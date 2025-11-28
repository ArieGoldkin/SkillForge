"""Helper functions for emitting SSE events from workflows."""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.core.types import AnalysisID, EventData
from app.services.event_broadcaster import broadcaster

logger = get_logger(__name__)


async def emit_streaming_event(
    event_type: str,
    analysis_id: AnalysisID,
    stage: str,
    status: str,
    **kwargs: object,
) -> None:
    """Emit SSE event during workflow execution.

    Publishes a structured event to the broadcaster channel for the given
    analysis. Events are consumed by SSE endpoint subscribers.

    Args:
        event_type: Event type ("progress", "complete", "error", "evaluation",
            "pattern_comparison", "metrics")
        analysis_id: UUID of the analysis (as string)
        stage: Workflow stage name (e.g., "extraction", "tech_comparison")
        status: Stage status ("pending", "running", "complete", "failed")
        **kwargs: Additional event data (e.g., word_count, agent, error, quality_score, metrics)

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

    await broadcaster.publish(channel, event_data)

    logger.debug(
        "sse_event_emitted",
        analysis_id=analysis_id,
        event_type=event_type,
        stage=stage,
        status=status,
    )


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
