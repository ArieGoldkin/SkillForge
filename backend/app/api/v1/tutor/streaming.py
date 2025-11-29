"""Streaming endpoints for tutor (SSE)."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from app.core.logging import get_logger
from app.services.event_broadcaster import broadcaster

router = APIRouter()
logger = get_logger(__name__)


@router.get("/tutor/sessions/{session_id}/stream")
async def stream_tutor_progress(
    session_id: uuid.UUID,
    request: Request,
) -> EventSourceResponse:
    """Stream real-time tutor progress via Server-Sent Events (SSE).

    Establishes an SSE connection for the specified session and streams
    progress events as they occur during workflow execution.

    Args:
        session_id: UUID of the session to stream progress for
        request: FastAPI request object

    Returns:
        EventSourceResponse streaming SSE events

    """
    channel = f"tutor:{session_id}"

    logger.info(
        "tutor_sse_connection_started",
        session_id=str(session_id),
        channel=channel,
    )

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        """Generate SSE events from broadcaster subscription."""
        try:
            async for event in broadcaster.subscribe(channel):
                # Format event for SSE
                event_type = str(event.get("type", "message"))
                yield {
                    "event": event_type,
                    "data": json.dumps(event),
                }

                # Close connection on done event
                if event.get("type") == "done":
                    logger.info(
                        "tutor_sse_done_event_sent",
                        session_id=str(session_id),
                        channel=channel,
                    )
                    break

        except asyncio.CancelledError:
            logger.info(
                "tutor_sse_connection_cancelled",
                session_id=str(session_id),
                channel=channel,
            )
            raise
        except Exception as e:
            logger.error(
                "tutor_sse_unexpected_error",
                session_id=str(session_id),
                channel=channel,
                error=str(e),
                exc_info=True,
            )
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "session_id": str(session_id),
                        "error": str(e),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                ),
            }

    return EventSourceResponse(
        event_generator(),
        send_timeout=30.0,
    )
