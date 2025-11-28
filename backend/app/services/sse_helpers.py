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
        event_type: Event type ("progress", "complete", "error")
        analysis_id: UUID of the analysis (as string)
        stage: Workflow stage name (e.g., "extraction", "tech_comparison")
        status: Stage status ("pending", "running", "complete", "failed")
        **kwargs: Additional event data (e.g., word_count, agent, error)

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
