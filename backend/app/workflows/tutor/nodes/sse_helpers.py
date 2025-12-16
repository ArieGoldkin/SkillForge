"""SSE event helpers for tutor workflow nodes."""

from datetime import UTC, datetime

from app.core.logging import get_logger
from app.services.messaging.broadcaster import broadcaster

logger = get_logger(__name__)


async def emit_tutor_event(
    session_id: str,
    event_type: str,
    stage: str,
    status: str,
    **kwargs: object,
) -> None:
    """Emit SSE event for tutor workflow.

    Args:
        session_id: Session UUID as string
        event_type: Event type ("progress", "chunk", "done", "error")
        stage: Workflow stage name
        status: Stage status
        **kwargs: Additional event data

    """
    channel = f"tutor:{session_id}"

    event_data = {
        "type": event_type,
        "session_id": session_id,
        "stage": stage,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat(),
        **kwargs,
    }

    await broadcaster.publish(channel, event_data)

    logger.debug(
        "tutor_sse_event_emitted",
        session_id=session_id,
        event_type=event_type,
        stage=stage,
        status=status,
    )
