"""Helper functions for emitting SSE events from workflows.

Issue #444: Updated to use broadcaster factory for multi-instance support.
Uses Redis Pub/Sub when available, falls back to in-memory broadcaster.

Issue #507: Functions now return asyncio.Task for optional awaiting.
In production code, the return value can be ignored (fire-and-forget).
In tests, callers can await the task to eliminate race conditions.
"""

import asyncio
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.types import AnalysisID, EventData
from app.shared.services.messaging.broadcaster_factory import BroadcasterBackend, get_broadcaster
from app.shared.services.persistence.progress import persist_progress_event_async

logger = get_logger(__name__)


def _get_broadcaster_backend() -> BroadcasterBackend:
    """Get broadcaster backend from settings."""
    settings = get_settings()
    backend_str = settings.BROADCASTER_BACKEND.lower()
    return BroadcasterBackend(backend_str)


async def emit_streaming_event(
    event_type: str,
    analysis_id: AnalysisID,
    stage: str,
    status: str,
    **kwargs: object,
) -> "asyncio.Task[None] | None":
    """Emit SSE event during workflow execution.

    Publishes a structured event to the broadcaster channel for the given
    analysis. Events are consumed by SSE endpoint subscribers.

    **Best Practice (Issue #507)**: Returns the persistence task for optional awaiting.
    In production code, callers can ignore the return value (fire-and-forget).
    In tests, callers can await the task to eliminate race conditions.

    Args:
        event_type: Event type ("progress", "complete", "error", "evaluation",
            "pattern_comparison", "metrics")
        analysis_id: UUID of the analysis (as string)
        stage: Workflow stage name (e.g., "extraction", "tech_comparison")
        status: Stage status ("pending", "running", "complete", "failed")
        **kwargs: Additional event data (e.g., word_count, agent, error, quality_score, metrics)

    Returns:
        The asyncio.Task if created, None if skipped (benchmark mode)

    Example:
        ```python
        await emit_streaming_event(
            "progress",
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            stage="extraction",
            status="running",
            word_count=5234,
        )
        ```

    """
    channel = f"workflow:{analysis_id}"

    event_data: EventData = {
        "type": event_type,
        "analysis_id": analysis_id,
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        **kwargs,
    }

    # Issue #444: Use factory for multi-instance broadcaster support
    broadcaster = await get_broadcaster(_get_broadcaster_backend())
    await broadcaster.publish(channel, event_data)

    # Persist to database - returns task for optional awaiting (Issue #507)
    # In production: fire-and-forget (ignore return value)
    # In tests: await task to eliminate race conditions
    persistence_task = persist_progress_event_async(event_data)

    logger.debug(
        "sse_event_emitted",
        analysis_id=analysis_id,
        event_type=event_type,
        stage=stage,
        status=status,
    )

    return persistence_task


async def emit_error_event(
    analysis_id: AnalysisID,
    stage: str,
    error: str | Exception,
    error_code: str | None = None,
    **kwargs: object,
) -> asyncio.Task[None] | None:
    """Emit standardized error event for workflow failures.

    This is the ONLY way to emit error events. All workflow nodes
    must use this function for consistency.

    Always emits `type="error"` with `status="failed"` to ensure
    frontend can reliably detect failures.

    **Best Practice (Issue #507)**: Returns the persistence task for optional awaiting.
    In production code, callers can ignore the return value (fire-and-forget).
    In tests, callers can await the task to eliminate race conditions.

    Args:
        analysis_id: UUID of the analysis (as string)
        stage: Stage name where error occurred (e.g., "extraction", "quality_validation")
        error: Error message or Exception object (will be converted to string)
        error_code: Optional error code (e.g., "EXTRACTION_FAILED", "QUALITY_GATE_FAILED")
        **kwargs: Additional event data (e.g., agent_type, quality_scores, retry_count)

    Returns:
        The asyncio.Task if created, None if skipped (benchmark mode)

    Example:
        ```python
        await emit_error_event(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            stage="extraction",
            error="Failed to extract content: timeout",
            error_code="EXTRACTION_FAILED",
            url=url,
            retry_count=1,
        )
        ```

    """
    # Convert Exception to string if needed
    error_message = str(error) if isinstance(error, Exception) else error

    # Build error event data
    event_data: EventData = {
        "type": "error",
        "analysis_id": analysis_id,
        "stage": stage,
        "status": "failed",
        "timestamp": datetime.now(UTC).isoformat(),
        "error": error_message,
    }

    # Add error_code if provided
    if error_code:
        event_data["error_code"] = error_code

    # Add any additional context
    event_data.update(kwargs)

    # Publish to broadcaster
    channel = f"workflow:{analysis_id}"
    broadcaster = await get_broadcaster(_get_broadcaster_backend())
    await broadcaster.publish(channel, event_data)

    # Persist to database - returns task for optional awaiting (Issue #507)
    # In production: fire-and-forget (ignore return value)
    # In tests: await task to eliminate race conditions
    persistence_task = persist_progress_event_async(event_data)

    logger.info(
        "sse_error_event_emitted",
        analysis_id=analysis_id,
        stage=stage,
        error_code=error_code,
        error_message=error_message[:100],  # Truncate for logging
    )

    return persistence_task


async def emit_evaluation_event(
    analysis_id: AnalysisID,
    agent_type: str,
    quality_score: float,
    metrics: dict[str, object] | None = None,
) -> None:
    """Emit evaluation event for agent quality assessment.

    Publishes an evaluation event with agent quality scores and metrics.

    Args:
        analysis_id: UUID of the analysis
        agent_type: Type of agent that was evaluated
        quality_score: Quality score (0.0-1.0)
        metrics: Optional additional metrics (latency, tokens, etc.)

    """
    await emit_streaming_event(
        "evaluation",
        analysis_id=analysis_id,
        stage=agent_type,
        status="complete",
        quality_score=quality_score,
        metrics=metrics or {},
    )


async def emit_pattern_comparison_event(
    analysis_id: AnalysisID,
    pattern_a: str,
    pattern_b: str,
    comparison_results: dict[str, object],
) -> None:
    """Emit A/B testing pattern comparison results.

    Publishes comparison results between two agent patterns or strategies.

    Args:
        analysis_id: UUID of the analysis
        pattern_a: Name of first pattern being compared
        pattern_b: Name of second pattern being compared
        comparison_results: Comparison metrics and results

    """
    await emit_streaming_event(
        "pattern_comparison",
        analysis_id=analysis_id,
        stage="pattern_comparison",
        status="complete",
        pattern_a=pattern_a,
        pattern_b=pattern_b,
        results=comparison_results,
    )


async def emit_metrics_event(
    analysis_id: AnalysisID,
    metrics: dict[str, object],
) -> None:
    """Emit performance and quality metrics event.

    Publishes aggregated metrics for the analysis workflow.

    Args:
        analysis_id: UUID of the analysis
        metrics: Dictionary of metrics (latency, tokens, success_rate, etc.)

    """
    await emit_streaming_event(
        "metrics",
        analysis_id=analysis_id,
        stage="metrics",
        status="complete",
        metrics=metrics,
    )
