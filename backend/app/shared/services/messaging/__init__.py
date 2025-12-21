"""Messaging services for SSE and event broadcasting.

Issue #444: Module now exports factory pattern instead of singleton.
Use get_broadcaster() for multi-instance support with Redis Pub/Sub.
"""

from app.shared.services.messaging.broadcaster import EventBroadcaster
from app.shared.services.messaging.broadcaster_factory import (
    BroadcasterBackend,
    BroadcasterProtocol,
    get_broadcaster,
    get_current_backend,
    health_check,
    reset_broadcaster,
)
from app.shared.services.messaging.sse_helpers import emit_streaming_event

__all__ = [
    "BroadcasterBackend",
    "BroadcasterProtocol",
    "EventBroadcaster",
    "emit_streaming_event",
    "get_broadcaster",
    "get_current_backend",
    "health_check",
    "reset_broadcaster",
]
