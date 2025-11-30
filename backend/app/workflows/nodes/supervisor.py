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
from app.services.sse_helpers import emit_streaming_event
from app.workflows.agents.prompt_builders import build_supervisor_user_prompt
from app.workflows.nodes.supervisor_config import SUPERVISOR_PROMPT
from app.workflows.nodes.supervisor_schema import AgentSelection
from app.workflows.utils.content_type_detection import (
    detect_content_type,
    filter_agents_by_content_type,
)

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
async def supervisor_route(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
) -> dict[str, object]:
    """Supervisor decides which agents should analyze the content.

    Uses structured output for faster inference (no tool calling overhead).
    Implements dynamic content sizing and progressive timeout retry logic.

    Args:
        content: The extracted text content to analyze
        content_type: Content type (article, video, repo)
        analysis_id: Unique identifier for this analysis

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

        # Get dynamically sized content for supervisor
        sized_content = _get_content_for_supervisor(content, content_type)

        # Build prompt using prompt builder
        user_prompt = build_supervisor_user_prompt(
            system_prompt=SUPERVISOR_PROMPT,
            content=sized_content,
            content_type=content_type,
        )

        # Get model with structured output (no tools, faster inference)
        model = get_chat_model()
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

        # Create supervisor decision with filtered agents
        supervisor_decision = {
            "agents": filtered_agents,  # Use filtered list
            "priority": [selection.confidence] * len(filtered_agents),
            "reasoning": (
                f"{selection.reasoning} "
                f"(Filtered: {len(skipped_agents)} agents skipped due to content type mismatch)"
                if skipped_agents
                else selection.reasoning
            ),
            "confidence": selection.confidence,
        }

        # Emit SSE event: supervisor complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage=get_stage_name("supervisor"),
            status="complete",
            agent_count=len(filtered_agents),
            selected_agents=filtered_agents,
            skipped_agents=skipped_agents if skipped_agents else None,
            confidence=selection.confidence,
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
