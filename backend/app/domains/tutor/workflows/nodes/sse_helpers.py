"""SSE event helpers for tutor workflow nodes.

Issue #444: Updated to use broadcaster factory for multi-instance support.
Uses Redis Pub/Sub when available, falls back to in-memory broadcaster.
"""

from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.logging import get_logger
from app.shared.services.messaging.broadcaster_factory import (
    BroadcasterBackend,
    get_broadcaster,
)

logger = get_logger(__name__)


def _get_broadcaster_backend() -> BroadcasterBackend:
    """Get broadcaster backend from settings."""
    settings = get_settings()
    backend_str = settings.BROADCASTER_BACKEND.lower()
    return BroadcasterBackend(backend_str)


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

    # Issue #444: Get broadcaster from factory (Redis or in-memory based on config)
    broadcaster = await get_broadcaster(_get_broadcaster_backend())
    await broadcaster.publish(channel, event_data)

    logger.debug(
        "tutor_sse_event_emitted",
        session_id=session_id,
        event_type=event_type,
        stage=stage,
        status=status,
    )
