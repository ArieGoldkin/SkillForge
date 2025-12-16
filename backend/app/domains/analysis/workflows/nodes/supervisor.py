"""Supervisor node for routing content analysis to specialized agents.

This module implements the supervisor pattern using structured output for faster inference.
The supervisor analyzes extracted content and decides which of 8 specialized
sub-agents should analyze the content.

Architecture:
    - Supervisor uses model.with_structured_output() for direct JSON response
    - No tool calling overhead - faster inference
    - Returns structured decision: {"agents": [...], "reasoning": "...", "confidence": 0.0-1.0}
"""

import time

from langchain_core.runnables import Runnable

from app.core.agent_config import get_stage_name
from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable
from app.core.types import AnalysisID
from app.shared.services.messaging.sse_helpers import emit_streaming_event
from app.domains.analysis.workflows.agents.prompt_builders import build_supervisor_user_prompt
from app.domains.analysis.workflows.nodes.supervisor_config import SUPERVISOR_PROMPT
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection
from app.shared.workflows.utils.content_signals import (
    detect_content_signals,
    should_skip_agent,
)
from app.shared.workflows.utils.content_type_detection import (
    detect_content_type,
    filter_agents_by_content_type,
)
from app.shared.workflows.utils.import_detection import detect_code_patterns

logger = get_logger(__name__)

# Content size thresholds for supervisor analysis
CONTENT_SIZE_SMALL = 5000  # Use all content
CONTENT_SIZE_MEDIUM = 15000  # Use 8K-10K chars
CONTENT_SIZE_LARGE = 50000  # Use 12K-15K chars


def _get_content_for_supervisor(
    content: str,
    content_type: str,
) -> str:
    """Get content for supervisor with dynamic sizing based on content length.

    Strategy:
    - Small (<5K): Use all content
    - Medium (5K-15K): Use 8K-10K chars
    - Large (15K+): Use 12K-15K chars
    - Very large (>50K): Smart truncation (beginning + key sections)

    Args:
        content: Full extracted content
        content_type: Type of content (article, video, repo)

    Returns:
        Content sized appropriately for supervisor analysis

    """
    content_len = len(content)

    if content_len <= CONTENT_SIZE_SMALL:
        # Small content: use all
        return content
    elif content_len <= CONTENT_SIZE_MEDIUM:
        # Medium: use 8K-10K (balanced)
        target = min(10000, content_len)
        return content[:target]
    elif content_len <= CONTENT_SIZE_LARGE:
        # Large: use 12K-15K (comprehensive)
        target = min(15000, content_len)
        # For articles: first 10K + middle section highlights
        if content_type == "article":
            first_part = content[:10000]
            middle_start = content_len // 3
            middle_part = content[middle_start : middle_start + 2000]
            return f"{first_part}\n\n[... middle section ...]\n\n{middle_part}"
        return content[:target]
    else:
        # Very large: smart truncation
        # First 12K chars (simplified for now)
        return content[:12000]


async def _invoke_supervisor_with_retry(
    model: Runnable,
    prompt: str,
    analysis_id: AnalysisID,
    max_attempts: int = 3,
) -> AgentSelection:
    """Invoke supervisor model with retry logic - timeout handled by step_timeout.

    Timeout handling is managed by LangGraph's `step_timeout` on the compiled graph.
    This avoids nested timeout conflicts and PEP 789 violations.

    Retry strategy:
    - Attempt 1: First attempt
    - Attempt 2: Retry if first fails
    - Attempt 3: Final attempt

    Args:
        model: Chat model with structured output
        prompt: User prompt with content
        analysis_id: Analysis ID for logging
        max_attempts: Maximum retry attempts

    Returns:
        AgentSelection with selected agents

    Raises:
        Exception: If all attempts fail (timeout handled by step_timeout)

    """
    for attempt in range(max_attempts):
        # Create RunnableConfig (timeout handled by step_timeout on graph)
        config = create_runnable_config()

        try:
            logger.debug(
                "supervisor_attempt",
                analysis_id=analysis_id,
                attempt=attempt + 1,
                max_attempts=max_attempts,
            )

            # Invoke model - no timeout wrapper (step_timeout handles it)
            result = await model.ainvoke(prompt, config=config)

            # Type assertion: structured output guarantees AgentSelection
            if not isinstance(result, AgentSelection):
                msg = f"Supervisor returned unexpected type: {type(result)}"
                raise TypeError(msg)
            return result
        except Exception as e:
            # Retry on any error (timeout will be handled by step_timeout)
            if attempt == max_attempts - 1:
                logger.warning(
                    "supervisor_failed_all_attempts",
                    analysis_id=analysis_id,
                    max_attempts=max_attempts,
                    error=str(e),
                )
                raise

            logger.warning(
                "supervisor_error_retry",
                analysis_id=analysis_id,
                attempt=attempt + 1,
                max_attempts=max_attempts,
                error=str(e),
            )
            # Continue to next attempt

    # Should never reach here
    msg = "Retry loop exhausted without success"
    raise RuntimeError(msg)


@robust_traceable(
    name="supervisor_route",
    run_type="chain",
    tags=["workflow", "supervisor"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "analysis",
        "component": "supervisor",
    },
)
async def supervisor_route(  # noqa: PLR0912, PLR0915
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    model_id: str | None = None,
) -> dict[str, object]:
    """Supervisor decides which agents should analyze the content.

    Uses structured output for faster inference (no tool calling overhead).
    Implements dynamic content sizing and progressive timeout retry logic.

    Args:
        content: The extracted text content to analyze
        content_type: Content type (article, video, repo)
        analysis_id: Unique identifier for this analysis
        model_id: Optional model identifier to use (e.g., "gpt-4o-mini", "gemini-2.5-flash").
            If not provided, uses the default from settings.

    Returns:
        Dictionary with supervisor_decision containing:
            - agents: List of selected agent names
            - priority: List of priority scores (derived from confidence)
            - reasoning: Brief explanation from model

    Raises:
        TimeoutError: If supervisor exceeds all timeout attempts
        Exception: If supervisor invocation fails

    """
    start_time = time.time()

    # Emit SSE event: supervisor started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage=get_stage_name("supervisor"),
        status="running",
    )

    logger.info(
        "workflow_supervisor_started",
        analysis_id=analysis_id,
        content_type=content_type,
        content_length=len(content),
    )

    try:
        # Detect actual content type from content (may differ from extraction metadata)
        detected_content_type = detect_content_type(content, content_type_hint=content_type)
        logger.debug(
            "content_type_detected",
            analysis_id=analysis_id,
            detected_type=detected_content_type,
            hint_type=content_type,
        )

        # Detect code patterns that indicate dependency analysis needed
        code_patterns = detect_code_patterns(content)
        logger.debug(
            "code_patterns_detected",
            analysis_id=analysis_id,
            has_imports=code_patterns["has_imports"],
            has_package_files=code_patterns["has_package_files"],
            has_install_commands=code_patterns["has_install_commands"],
            has_frameworks=code_patterns["has_frameworks"],
        )

        # ISSUE #299-304: Detect content signals for intelligent routing
        # This tells us WHAT'S IN the content, not just how long it is
        content_signals = detect_content_signals(content)
        logger.info(
            "content_signals_detected",
            analysis_id=analysis_id,
            richness_score=content_signals.content_richness_score,
            genre=content_signals.detected_genre.value,
            word_count=content_signals.word_count,
            has_code=content_signals.has_code_patterns,
            has_benchmarks=content_signals.has_benchmarks,
            has_security=content_signals.has_security_patterns,
            has_architecture=content_signals.has_architecture,
            coverage_summary=content_signals.get_coverage_summary(),
        )

        # Get dynamically sized content for supervisor
        sized_content = _get_content_for_supervisor(content, content_type)

        # Build prompt using prompt builder
        user_prompt = build_supervisor_user_prompt(
            system_prompt=SUPERVISOR_PROMPT,
            content=sized_content,
            content_type=content_type,
        )

        # Get model with structured output (no tools, faster inference)
        # Use runtime model override if model_id is provided
        model_config: dict[str, dict[str, object]] | None = (
            {"configurable": {"model": model_id}} if model_id else None
        )
        model = get_chat_model(model_config)
        structured_model = model.with_structured_output(AgentSelection)

        # Invoke with progressive timeout retry
        selection = await _invoke_supervisor_with_retry(
            structured_model,
            user_prompt,
            analysis_id,
        )

        # Filter agents based on content type capabilities
        filtered_agents, skipped_agents = filter_agents_by_content_type(
            selection.agents, detected_content_type
        )

        # Auto-activate dependency_mapper if code patterns detected and not already selected
        if (
            code_patterns["has_imports"]
            or code_patterns["has_package_files"]
            or code_patterns["has_install_commands"]
        ) and "dependency_mapper" not in filtered_agents:
            logger.info(
                "supervisor_auto_activate_dependency_mapper",
                analysis_id=analysis_id,
                reason="code_patterns_detected",
                patterns=code_patterns,
            )
            filtered_agents.append("dependency_mapper")

        # ISSUE #178: Auto-activate performance_analyst
        if (
            code_patterns.get("has_performance_indicators")
            and "performance_analyst" not in filtered_agents
        ):
            logger.info(
                "supervisor_auto_activate_performance_analyst",
                analysis_id=analysis_id,
                reason="performance_indicators_detected",
            )
            filtered_agents.append("performance_analyst")

        # ISSUE #174: Auto-activate security_auditor
        if (
            code_patterns.get("has_security_indicators")
            and "security_auditor" not in filtered_agents
        ):
            logger.info(
                "supervisor_auto_activate_security_auditor",
                analysis_id=analysis_id,
                reason="security_indicators_detected",
            )
            filtered_agents.append("security_auditor")

        # ISSUE #177: Auto-activate tech_comparator
        if (
            code_patterns.get("has_comparison_indicators")
            and "tech_comparator" not in filtered_agents
        ):
            logger.info(
                "supervisor_auto_activate_tech_comparator",
                analysis_id=analysis_id,
                reason="comparison_indicators_detected",
                detected_frameworks=code_patterns.get("frameworks_detected", []),
            )
            filtered_agents.append("tech_comparator")

        # ISSUE #299-304: Filter agents that should be skipped based on content signals
        # Skip agents when there's NO relevant data (different from OPPORTUNISTIC)
        agents_to_skip: list[str] = []
        skip_reasons: dict[str, str] = {}  # Track reasons for skipped agents
        for agent in filtered_agents.copy():
            skip, reason = should_skip_agent(agent, content_signals)
            if skip:
                agents_to_skip.append(agent)
                skip_reasons[agent] = reason
                filtered_agents.remove(agent)
                logger.info(
                    "supervisor_agent_skipped_by_signals",
                    analysis_id=analysis_id,
                    agent=agent,
                    reason=reason,
                    content_richness=content_signals.content_richness_score,
                )

        # MINIMUM AGENT ENFORCEMENT (Issue #299-304)
        # Use content signals to pick appropriate default agents
        min_agents_required = 3
        # Combine signal-appropriate with static defaults to ensure enough agents
        signal_appropriate_agents = content_signals.get_appropriate_agents()
        static_defaults = ["implementation_planner", "dependency_mapper", "trend_validator"]
        # Use signal-appropriate first, then fill with static defaults
        default_agents_for_minimum = signal_appropriate_agents + [
            a for a in static_defaults if a not in signal_appropriate_agents
        ]

        if len(filtered_agents) < min_agents_required:
            logger.info(
                "supervisor_enforcing_minimum_agents",
                analysis_id=analysis_id,
                current_count=len(filtered_agents),
                minimum_required=min_agents_required,
                original_agents=filtered_agents.copy(),
                signal_recommended=signal_appropriate_agents,
            )
            # Add signal-appropriate agents to meet minimum
            for default_agent in default_agents_for_minimum:
                if default_agent not in filtered_agents:
                    filtered_agents.append(default_agent)
                    logger.debug(
                        "supervisor_added_default_agent",
                        analysis_id=analysis_id,
                        agent=default_agent,
                        current_count=len(filtered_agents),
                        source="content_signals",
                    )
                    if len(filtered_agents) >= min_agents_required:
                        break

        if skipped_agents:
            logger.info(
                "supervisor_agents_filtered",
                analysis_id=analysis_id,
                skipped_agents=skipped_agents,
                filtered_agents=filtered_agents,
                content_type=detected_content_type,
                reason="agents_cannot_process_content_type",
            )

        # Calculate duration for performance monitoring
        duration_ms = int((time.time() - start_time) * 1000)

        # Build reasoning with code pattern detection info
        reasoning_parts = [selection.reasoning]
        if skipped_agents:
            reasoning_parts.append(
                f"(Filtered: {len(skipped_agents)} agents skipped due to content type mismatch)"
            )

        # Add auto-activation reasoning
        activation_reasons = []
        if (
            code_patterns["has_imports"]
            or code_patterns["has_package_files"]
            or code_patterns["has_install_commands"]
        ) and "dependency_mapper" in filtered_agents:
            activation_reasons.append("dependency_mapper (code patterns)")

        if (
            code_patterns.get("has_performance_indicators")
            and "performance_analyst" in filtered_agents
        ):
            activation_reasons.append("performance_analyst (perf keywords)")

        if code_patterns.get("has_security_indicators") and "security_auditor" in filtered_agents:
            activation_reasons.append("security_auditor (security keywords)")

        if code_patterns.get("has_comparison_indicators") and "tech_comparator" in filtered_agents:
            frameworks = code_patterns.get("frameworks_detected", [])
            if isinstance(frameworks, list):
                activation_reasons.append(
                    f"tech_comparator (comparison detected: {', '.join(frameworks)})"
                )

        if activation_reasons:
            reasoning_parts.append(f"(Auto-activated: {'; '.join(activation_reasons)})")

        # Create supervisor decision with filtered agents and content signals
        # ISSUE #299-304: Include agent expectations so agents know what depth is expected
        supervisor_decision = {
            "agents": filtered_agents,  # Use filtered list
            "priority": [selection.confidence] * len(filtered_agents),
            "reasoning": " ".join(reasoning_parts),
            "confidence": selection.confidence,
            # Content signals for downstream agents and synthesis
            "content_signals": {
                "richness_score": content_signals.content_richness_score,
                "genre": content_signals.detected_genre.value,
                "word_count": content_signals.word_count,
                "coverage_summary": content_signals.get_coverage_summary(),
                "has_code": content_signals.has_code_patterns,
                "has_benchmarks": content_signals.has_benchmarks,
                "has_security": content_signals.has_security_patterns,
                "has_architecture": content_signals.has_architecture,
                "has_dependencies": content_signals.has_dependencies,
                "has_comparisons": content_signals.has_comparisons,
                "has_tutorials": content_signals.has_tutorials,
                "has_conceptual_only": content_signals.has_conceptual_only,
            },
            # Agent expectations map (FULL_ANALYSIS, PARTIAL, OPPORTUNISTIC)
            "agent_expectations": {
                agent: exp.value for agent, exp in content_signals.agent_expectations.items()
            },
            # Agents skipped due to no relevant data
            "agents_skipped_by_signals": agents_to_skip,
        }

        # Calculate expected total stages: 5 fixed stages + selected agents
        # Fixed stages: extraction, embedding, supervisor, aggregation, artifact_generation
        expected_total_stages = 5 + len(filtered_agents)

        # Build skip_reasons dict for all skipped agents (content type + signal-based)
        all_skip_reasons: dict[str, str] = {}
        # Add content type based skip reasons
        if skipped_agents:
            for agent in skipped_agents:
                all_skip_reasons[agent] = f"Not applicable for {detected_content_type} content type"
        # Add signal-based skip reasons
        all_skip_reasons.update(skip_reasons)

        # Emit SSE event: supervisor complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage=get_stage_name("supervisor"),
            status="complete",
            agent_count=len(filtered_agents),
            selected_agents=filtered_agents,
            skipped_agents=skipped_agents if skipped_agents else None,
            skip_reasons=all_skip_reasons if all_skip_reasons else None,
            confidence=selection.confidence,
            expected_total_stages=expected_total_stages,
        )

        logger.info(
            "workflow_supervisor_complete",
            analysis_id=analysis_id,
            selected_agents=filtered_agents,
            agent_count=len(filtered_agents),
            skipped_agent_count=len(skipped_agents),
            confidence=selection.confidence,
            duration_ms=duration_ms,
            content_sent_chars=len(sized_content),
            content_original_chars=len(content),
            detected_content_type=detected_content_type,
            code_patterns_detected=code_patterns,
        )
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)

        # Emit SSE event: supervisor failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage=get_stage_name("supervisor"),
            status="failed",
            error=str(e),
            error_code="SUPERVISOR_FAILED",
        )

        logger.error(
            "workflow_supervisor_failed",
            analysis_id=analysis_id,
            error=str(e),
            duration_ms=duration_ms,
            exc_info=True,
        )
        raise
    else:
        return {"supervisor_decision": supervisor_decision}
