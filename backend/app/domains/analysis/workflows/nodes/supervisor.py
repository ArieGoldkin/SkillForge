"""Supervisor node for routing content analysis to specialized agents.

This module implements the supervisor pattern using structured output for faster inference.
The supervisor analyzes extracted content and decides which of 8 specialized
sub-agents should analyze the content.

Architecture:
    - Supervisor uses model.with_structured_output() for direct JSON response
    - No tool calling overhead - faster inference
    - Returns structured decision: {"agents": [...], "reasoning": "...", "confidence": 0.0-1.0}
    - Redis exact-match caching for deterministic routing (same content = same agents)
"""

import hashlib
import json
import time

from langchain_core.runnables import Runnable

from app.core.agent_config import get_stage_name
from app.core.config import settings
from app.core.exceptions import WorkflowStageError
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable
from app.core.types import AnalysisID

# Issue #436: Tier-based agent filtering
# Issue #533: Import AgentTier to protect Universal agents from content signal skipping
# Issue #544: Import get_agents_by_tier for force-injecting Tier 1 agents
from app.domains.analysis.agents.registry import (
    AgentTier,
    get_agent_metadata,
    get_agents_by_tier,
    get_agents_for_mode,
)
from app.domains.analysis.workflows.agents.prompt_builders import build_supervisor_user_prompt
from app.domains.analysis.workflows.nodes.supervisor_config import (
    SUPERVISOR_PROMPT,
    build_agent_list_variable,
)
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection
from app.shared.services.cache import get_exact_cache
from app.shared.services.messaging.sse_helpers import (
    emit_error_event,
    emit_streaming_event,
)
from app.shared.services.prompts import get_prompt_manager
from app.shared.workflows.utils.content_signals import (
    ContentGenre,
    detect_content_signals,
    # NOTE: should_skip_agent removed in Issue #547 (GAP 1)
    # LLM is now the single source of truth for agent selection
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

# Genre-aware minimum agent counts
# Different content types require different analysis depth based on genre
MIN_AGENTS_BY_GENRE: dict[ContentGenre, int] = {
    ContentGenre.TUTORIAL: 4,  # Comprehensive multi-perspective analysis
    ContentGenre.RESEARCH: 2,  # Concepts + trends only
    ContentGenre.OPINION: 1,  # Trend validation sufficient
    ContentGenre.REFERENCE: 3,  # Standard documentation coverage
    ContentGenre.QUICKSTART: 3,  # Implementation focus
    ContentGenre.CHANGELOG: 2,  # Trends + tech comparison
    ContentGenre.NEWS: 2,  # Issue #490: trend_validator + tech_comparator only
    ContentGenre.UNKNOWN: 3,  # Safe default
}


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
    if content_len <= CONTENT_SIZE_MEDIUM:
        # Medium: use 8K-10K (balanced)
        target = min(10000, content_len)
        return content[:target]
    if content_len <= CONTENT_SIZE_LARGE:
        # Large: use 12K-15K (comprehensive)
        target = min(15000, content_len)
        # For articles: first 10K + middle section highlights
        if content_type == "article":
            first_part = content[:10000]
            middle_start = content_len // 3
            middle_part = content[middle_start : middle_start + 2000]
            return f"{first_part}\n\n[... middle section ...]\n\n{middle_part}"
        return content[:target]
    # Very large: smart truncation
    # First 12K chars (simplified for now)
    return content[:12000]


async def _invoke_supervisor_with_retry(
    model: Runnable,
    prompt: str,
    analysis_id: AnalysisID,
) -> AgentSelection:
    """Invoke supervisor model with LCEL fallback.

    Uses LCEL `.with_fallbacks()` to provide automatic fallback to secondary model.
    Retry is handled at the LangChain level via LLM_MAX_RETRIES in model_factory.py.

    Args:
        model: Chat model with structured output (already bound)
        prompt: User prompt with content
        analysis_id: Analysis ID for logging

    Returns:
        AgentSelection with selected agents

    Raises:
        Exception: If both primary and fallback fail

    """
    # Create RunnableConfig
    config = create_runnable_config(
        metadata={
            "analysis_id": str(analysis_id),
            "agent_type": "supervisor",
            "task_type": "agent_routing",
        },
        tags=["supervisor", "agent_routing", f"analysis:{analysis_id}"],
    )

    logger.debug(
        "supervisor_invoking_with_lcel_chain",
        analysis_id=analysis_id,
    )

    # Invoke model (LCEL chain already has retry + fallback)
    result = await model.ainvoke(prompt, config=config)

    # Extract usage metadata (LangChain-Core 1.2.4+)
    if hasattr(result, "usage_metadata") and result.usage_metadata:
        usage = result.usage_metadata
        logger.info(
            "supervisor_token_usage",
            analysis_id=str(analysis_id),
            input_tokens=getattr(usage, "input_tokens", 0),
            output_tokens=getattr(usage, "output_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
        )

    # Type assertion: structured output guarantees AgentSelection
    if not isinstance(result, AgentSelection):
        msg = f"Supervisor returned unexpected type: {type(result)}"
        raise TypeError(msg)
    return result


def _generate_supervisor_cache_key(content: str, content_type: str) -> str:
    """Generate cache key for supervisor routing decisions.

    Args:
        content: Content to analyze
        content_type: Type of content

    Returns:
        Cache key combining content hash and type

    """
    # Use first 3000 chars for cache key (enough to be unique)
    content_hash = hashlib.sha256(f"{content[:3000]}{content_type}".encode()).hexdigest()[:16]
    return f"supervisor:{content_type}:{content_hash}"


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
    analysis_mode: str = "standard",
) -> dict[str, object]:
    """Supervisor decides which agents should analyze the content.

    Uses structured output for faster inference (no tool calling overhead).
    Implements dynamic content sizing and progressive timeout retry logic.
    Uses Redis exact-match caching to return same agents for identical content.

    Args:
        content: The extracted text content to analyze
        content_type: Content type (article, video, repo)
        analysis_id: Unique identifier for this analysis
        model_id: Optional model identifier to use (e.g., "gpt-4o-mini", "gemini-2.5-flash").
            If not provided, uses the default from settings.
        analysis_mode: Analysis depth mode (quick, standard, deep_dive). Controls tier-based
            agent filtering. Quick=Tier 1 only, Standard=Tier 1+2, Deep=All tiers.

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

    # Runtime metadata updates for Langfuse
    try:
        from app.core.tracing import update_current_trace

        update_current_trace(
            metadata={"analysis_id": str(analysis_id), "content_type": content_type},
            session_id=f"analysis-{analysis_id}",
            user_id="anonymous",
        )
    except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
        # Langfuse may not be available or trace update may fail
        # Continue workflow execution without blocking on telemetry
        logger.debug("Langfuse trace update failed, continuing: %s", e)

    # Emit SSE event: supervisor started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage=get_stage_name("supervisor"),
        status="running",
        analysis_mode=analysis_mode,
    )

    logger.info(
        "workflow_supervisor_started",
        analysis_id=analysis_id,
        content_type=content_type,
        content_length=len(content),
    )

    # Check Redis exact-match cache for supervisor routing
    cache_key = _generate_supervisor_cache_key(content, content_type)
    exact_cache = None
    cached_decision = None

    try:
        exact_cache = get_exact_cache()
        # Try to get cached decision
        cached_value = await exact_cache.aget(cache_key)
        if cached_value:
            cached_decision = (
                json.loads(cached_value) if isinstance(cached_value, str) else cached_decision
            )
            logger.info(
                "supervisor_cache_hit",
                analysis_id=analysis_id,
                cache_key=cache_key[:32],
                cached_agents=cached_decision.get("agents") if cached_decision else None,
            )
    except Exception as cache_error:  # noqa: BLE001 - Non-critical cache lookup
        # Gracefully handle Redis connection failures
        logger.warning(
            "supervisor_cache_unavailable",
            analysis_id=analysis_id,
            error=str(cache_error),
        )
        exact_cache = None

    # If we have a valid cached decision, return it immediately
    if cached_decision and cached_decision.get("agents"):
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "supervisor_returning_cached_decision",
            analysis_id=analysis_id,
            agents=cached_decision.get("agents"),
            duration_ms=duration_ms,
            cache_hit=True,
        )

        # Emit SSE event: supervisor complete (from cache)
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage=get_stage_name("supervisor"),
            status="complete",
            agent_count=len(cached_decision.get("agents", [])),
            selected_agents=cached_decision.get("agents"),
            cache_hit=True,
            analysis_mode=analysis_mode,
        )

        return {"supervisor_decision": cached_decision}

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
            # Issue #299-304: Log comparison detection
            has_comparisons=content_signals.has_comparisons,
            coverage_summary=content_signals.get_coverage_summary(),
        )

        # Get dynamically sized content for supervisor
        sized_content = _get_content_for_supervisor(content, content_type)

        # Issue #379: Fetch prompt from Langfuse with fallback to hardcoded
        # Get PromptManager instance
        prompt_manager = get_prompt_manager()

        # Build agent list variable for prompt
        agent_list = build_agent_list_variable()

        # Fetch and compile prompt (uses L1/L2 cache, Langfuse API, or hardcoded fallback)
        try:
            supervisor_prompt = await prompt_manager.get_prompt(
                name="analysis-supervisor-routing",
                variables={"agent_list": agent_list},
                label="production",
            )

            # Get metadata for trace attribution
            prompt_metadata = await prompt_manager.get_prompt_metadata(
                name="analysis-supervisor-routing",
                label="production",
            )

            logger.debug(
                "supervisor_prompt_fetched",
                analysis_id=analysis_id,
                prompt_source=prompt_metadata.get("prompt_source"),
                prompt_version=prompt_metadata.get("prompt_version"),
            )

        except Exception as e:  # noqa: BLE001 - Graceful degradation for prompt fetching
            # Fallback to hardcoded SUPERVISOR_PROMPT constant
            logger.warning(
                "supervisor_prompt_fetch_failed",
                analysis_id=analysis_id,
                error=str(e),
                message="Falling back to hardcoded SUPERVISOR_PROMPT",
                exc_info=True,
            )
            supervisor_prompt = SUPERVISOR_PROMPT
            prompt_metadata = {
                "prompt_source": "hardcoded_constant",
                "prompt_version": "fallback",
            }

        # Build prompt using prompt builder (pass content signals for LLM routing guidance)
        user_prompt = build_supervisor_user_prompt(
            system_prompt=supervisor_prompt,
            content=sized_content,
            content_type=content_type,
            content_signals=content_signals,
        )

        # Get model with structured output (no tools, faster inference)
        # Use runtime model override if model_id is provided, otherwise use task routing
        # Task routing uses cheaper/faster models for supervisor classification
        model_config: dict[str, dict[str, object]] | None = (
            {"configurable": {"model": model_id}} if model_id else None
        )
        # Only apply task routing if no explicit model_id is provided
        task_type_to_use = None if model_id else "supervisor"
        primary_model = get_chat_model(config=model_config, task_type=task_type_to_use)

        # Create fallback model
        fallback_model = get_chat_model(
            config={"configurable": {"model": settings.LLM_FALLBACK_MODEL}}
        )

        # LangChain 1.2.x: Use strict mode for exact schema compliance
        # Supervisor routing is critical path - must always return valid agent selection
        # LCEL chain: primary → fallback on failure
        # NOTE: Removed .with_retry() - redundant with LLM_MAX_RETRIES in model_factory.py
        structured_model = primary_model.with_structured_output(
            AgentSelection, strict=True
        ).with_fallbacks(
            [fallback_model.with_structured_output(AgentSelection, strict=True)],
            exceptions_to_handle=(Exception, TimeoutError),
        )

        # Invoke with LCEL chain (fallback built-in, retry at LangChain level)
        selection = await _invoke_supervisor_with_retry(
            structured_model,
            user_prompt,
            analysis_id,
        )

        # ═══════════════════════════════════════════════════════════════════
        # ISSUE #544: Force-inject Tier 1 (UNIVERSAL) agents as safety net
        # LLM may forget to include them despite prompt instructions.
        # Tier 1 agents provide foundational value for ALL content types.
        # NOTE: We don't recreate AgentSelection because the schema has max_length=8
        #       for LLM output validation. After injection, we may have >8 agents
        #       (LLM selection + 4 Tier 1), so we use the list directly.
        # ═══════════════════════════════════════════════════════════════════
        tier1_agents = get_agents_by_tier(AgentTier.UNIVERSAL)
        selected_agents = list(selection.agents)  # Mutable copy
        tier1_injected = []

        for tier1_agent in tier1_agents:
            if tier1_agent not in selected_agents:
                selected_agents.append(tier1_agent)
                tier1_injected.append(tier1_agent)

        if tier1_injected:
            logger.info(
                "supervisor_tier1_force_injected",
                analysis_id=analysis_id,
                injected_agents=tier1_injected,
                original_agents=list(selection.agents),
                reason="tier1_universals_always_required",
            )

        # Filter agents based on content type capabilities
        # Use selected_agents (with Tier 1 injected) instead of selection.agents
        filtered_agents, skipped_agents = filter_agents_by_content_type(
            selected_agents, detected_content_type
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

        # ISSUE #547 (GAP 1): REMOVED should_skip_agent() override
        # ═══════════════════════════════════════════════════════════════════
        # REASON: The LLM supervisor already receives content_signals in its prompt
        # and makes INFORMED decisions about which agents to select. The regex-based
        # should_skip_agent() was OVERRIDING LLM decisions, causing mismatch between
        # what LLM selected and what actually ran - leading to stuck aggregation.
        #
        # The LLM is now the SINGLE SOURCE OF TRUTH for agent selection.
        # Content signals inform the LLM, they don't override it.
        # ═══════════════════════════════════════════════════════════════════
        agents_to_skip: list[str] = []
        skip_reasons: dict[str, str] = {}  # Track reasons for any content-type skips

        # Log Tier 1 agents that are protected (for observability, not filtering)
        for agent in filtered_agents:
            agent_meta = get_agent_metadata(agent)
            if agent_meta is not None and agent_meta.tier == AgentTier.UNIVERSAL:
                logger.debug(
                    "supervisor_tier1_protected",
                    analysis_id=analysis_id,
                    agent=agent,
                    tier="UNIVERSAL",
                    reason="tier1_agents_always_run",
                )

        # MINIMUM AGENT ENFORCEMENT (Issue #299-304)
        # Use genre-aware minimum agent counts instead of hardcoded value
        min_agents_required = MIN_AGENTS_BY_GENRE.get(
            content_signals.detected_genre,
            3,  # Fallback to safe default
        )
        logger.info(
            "supervisor_genre_aware_minimum",
            analysis_id=analysis_id,
            genre=content_signals.detected_genre.value,
            minimum_required=min_agents_required,
            current_count=len(filtered_agents),
        )

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

        # ISSUE #436: Tier-based agent filtering based on analysis_mode
        # INCLUSIVE filtering: Only restrict agents that ARE in the tier registry
        # Old content-specific agents (tech_comparator, security_auditor, etc.) are
        # NOT in the tier registry - they pass through (filtered by content signals)
        allowed_for_mode = set(get_agents_for_mode(analysis_mode))
        tier_excluded = []
        tier_filtered_agents = []

        for agent in filtered_agents:
            agent_meta = get_agent_metadata(agent)
            if agent_meta is None:
                # Agent not in tier registry - allow through (content-specific)
                tier_filtered_agents.append(agent)
            elif agent in allowed_for_mode:
                # Agent is tiered and allowed for this mode
                tier_filtered_agents.append(agent)
            else:
                # Agent is tiered but NOT allowed for this mode
                tier_excluded.append(agent)

        if tier_excluded:
            logger.info(
                "supervisor_tier_filtered",
                analysis_id=analysis_id,
                analysis_mode=analysis_mode,
                excluded_agents=tier_excluded,
                reason="agents_excluded_by_tier",
            )

        # Update filtered_agents with tier-filtered list
        filtered_agents = tier_filtered_agents

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
        # ISSUE #547 (GAP 4): Include expected_agent_count for fan-in tracking
        supervisor_decision = {
            "agents": filtered_agents,  # Use filtered list
            "priority": [selection.confidence] * len(filtered_agents),
            "reasoning": " ".join(reasoning_parts),
            "confidence": selection.confidence,
            # Issue #547 (GAP 4): Expected agent count for fan-in validation
            # This is set by supervisor and verified by router + aggregation
            "expected_agent_count": len(filtered_agents),
            # Content signals for downstream agents and synthesis
            "content_signals": {
                "richness_score": content_signals.content_richness_score,
                # Issue #442: Must match agent reads
                "detected_genre": content_signals.detected_genre.value,
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

        # Store decision in Redis exact-match cache for future identical content
        if exact_cache is not None:
            try:
                await exact_cache.aset(cache_key, json.dumps(supervisor_decision))
                logger.debug(
                    "supervisor_decision_cached",
                    analysis_id=analysis_id,
                    cache_key=cache_key[:32],
                    agents=filtered_agents,
                )
            except Exception as cache_error:  # noqa: BLE001 - Non-critical cache set
                # Non-critical - log and continue
                logger.warning(
                    "supervisor_cache_set_failed",
                    analysis_id=analysis_id,
                    error=str(cache_error),
                )

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
            analysis_mode=analysis_mode,
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

        # Emit error event using standardized helper
        stage_name = get_stage_name("supervisor")
        await emit_error_event(
            analysis_id=analysis_id,
            stage=stage_name,
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
        # Wrap exception with stage context for orchestrator-level error handling
        raise WorkflowStageError(
            stage=stage_name,
            original_exception=e,
            message=f"Supervisor routing failed: {e}",
        ) from e
    else:
        return {"supervisor_decision": supervisor_decision}
