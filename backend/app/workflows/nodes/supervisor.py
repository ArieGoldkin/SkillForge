"""Supervisor node for routing content analysis to specialized agents.

This module implements the supervisor pattern using structured output for faster inference.
The supervisor analyzes extracted content and decides which of 8 specialized
sub-agents should analyze the content.

Architecture:
    - Supervisor uses model.with_structured_output() for direct JSON response
    - No tool calling overhead - faster inference
    - Returns structured decision: {"agents": [...], "reasoning": "...", "confidence": 0.0-1.0}
"""

import asyncio
import time

from langchain_core.runnables import Runnable
from langsmith import traceable

from app.core.agent_config import get_stage_name
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.types import AnalysisID
from app.services.sse_helpers import emit_streaming_event
from app.workflows.agents.prompt_builders import build_supervisor_user_prompt
from app.workflows.nodes.supervisor_config import SUPERVISOR_PROMPT
from app.workflows.nodes.supervisor_schema import AgentSelection

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
    """Invoke supervisor model with progressive timeout and retry logic.

    Progressive timeout strategy:
    - Attempt 1: 60s (fast path)
    - Attempt 2: 120s (fallback)
    - Attempt 3: 180s (last resort)

    Args:
        model: Chat model with structured output
        prompt: User prompt with content
        analysis_id: Analysis ID for logging
        max_attempts: Maximum retry attempts

    Returns:
        AgentSelection with selected agents

    Raises:
        TimeoutError: If all attempts exceed their timeouts

    """
    timeouts = [60.0, 120.0, 180.0]

    for attempt in range(max_attempts):
        timeout = timeouts[attempt]
        try:
            logger.debug(
                "supervisor_attempt",
                analysis_id=analysis_id,
                attempt=attempt + 1,
                timeout=timeout,
            )
            result = await asyncio.wait_for(
                model.ainvoke(prompt),
                timeout=timeout,
            )
            # Type assertion: structured output guarantees AgentSelection
            if not isinstance(result, AgentSelection):
                msg = f"Supervisor returned unexpected type: {type(result)}"
                raise TypeError(msg)
            return result
        except TimeoutError:
            if attempt == max_attempts - 1:
                # Last attempt failed
                logger.warning(
                    "supervisor_timeout_all_attempts",
                    analysis_id=analysis_id,
                    max_attempts=max_attempts,
                    final_timeout=timeout,
                )
                msg = f"Supervisor exceeded all timeouts (final: {timeout}s)"
                raise TimeoutError(msg) from None

            logger.warning(
                "supervisor_timeout_retry",
                analysis_id=analysis_id,
                attempt=attempt + 1,
                timeout=timeout,
                next_timeout=timeouts[attempt + 1],
            )
            # Continue to next attempt with longer timeout
        except Exception as e:
            # Non-timeout errors: log and re-raise
            logger.error(
                "supervisor_invocation_error",
                analysis_id=analysis_id,
                attempt=attempt + 1,
                error=str(e),
                exc_info=True,
            )
            raise

    # Should never reach here
    msg = "Retry loop exhausted without success"
    raise RuntimeError(msg)


@traceable(
    name="supervisor_route",
    run_type="chain",
    tags=["workflow", "supervisor"],
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

        # Calculate duration for performance monitoring
        duration_ms = int((time.time() - start_time) * 1000)

        # Create supervisor decision (convert to legacy format for compatibility)
        supervisor_decision = {
            "agents": selection.agents,
            "priority": [selection.confidence] * len(selection.agents),
            "reasoning": selection.reasoning,
            "confidence": selection.confidence,
        }

        # Emit SSE event: supervisor complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage=get_stage_name("supervisor"),
            status="complete",
            agent_count=len(selection.agents),
            selected_agents=selection.agents,
            confidence=selection.confidence,
        )

        logger.info(
            "workflow_supervisor_complete",
            analysis_id=analysis_id,
            selected_agents=selection.agents,
            agent_count=len(selection.agents),
            confidence=selection.confidence,
            duration_ms=duration_ms,
            content_sent_chars=len(sized_content),
            content_original_chars=len(content),
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
