"""SSE endpoint handler for analysis progress streaming.

Issue #444: Updated to use broadcaster factory for multi-instance support.
Uses Redis Pub/Sub when available, falls back to in-memory broadcaster.
"""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, MutableMapping
from contextlib import aclosing
from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

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


async def stream_analysis_progress(
    analysis_id: uuid.UUID,
    request: Request,
) -> EventSourceResponse:
    """Stream real-time analysis progress via Server-Sent Events (SSE).

    Establishes an SSE connection for the specified analysis and streams
    progress events as they occur during workflow execution. Events include
    stage updates, status changes, and completion notifications.

    This endpoint maintains a persistent connection that streams events from
    the workflow execution. The connection is automatically closed when:
    - A "complete" event is received
    - The client disconnects
    - An error occurs

    Args:
        analysis_id: UUID of the analysis to stream progress for
        request: FastAPI request object (used for disconnect detection)

    Returns:
        EventSourceResponse streaming SSE events in the format:
        ```
        event: {event_type}
        data: {json_encoded_event_data}
        ```

    Raises:
        404: If analysis_id is invalid or not found (handled by FastAPI)

    Event Types:
        - progress: Stage status updates (running, complete)
        - error: Error notifications with error details
        - complete: Final workflow completion

    Example Client Usage:
        ```javascript
        const eventSource = new EventSource('/api/v1/analyze/{id}/stream');

        eventSource.addEventListener('progress', (e) => {
            const data = JSON.parse(e.data);
            console.log(`Stage: ${data.stage}, Status: ${data.status}`);
        });

        eventSource.addEventListener('complete', (e) => {
            eventSource.close();
        });
        ```

    Example Server Events:
        ```
        event: progress
        data: {"type": "progress", "stage": "extraction", "status": "running", "timestamp": "..."}

        event: progress
        data: {"type": "progress", "stage": "extraction", "status": "complete", "word_count": 5234}

        event: complete
        data: {"type": "complete", "stage": "artifact_generation", "timestamp": "..."}
        ```

    """
    channel = f"workflow:{analysis_id}"

    logger.info(
        "sse_connection_started",
        analysis_id=str(analysis_id),
        channel=channel,
    )

    async def client_close_handler(message: MutableMapping[str, Any]) -> None:
        """Handle client disconnect with cleanup logging.

        Called automatically by sse-starlette 3.0.3 when client disconnects.
        Performs cleanup logging for monitoring and debugging.

        Args:
            message: Disconnect message from sse-starlette library

        """
        logger.info(
            "sse_client_disconnected",
            analysis_id=str(analysis_id),
            channel=channel,
            message=str(message),
        )

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        """Generate SSE events from broadcaster subscription.

        Leverages sse-starlette 3.0.3 features:
        - Automatic disconnect detection (no manual checks needed)
        - Better exception propagation for clearer error messages
        - Improved cancellation handling with asyncio.CancelledError
        - Library handles disconnect detection automatically via _listen_for_disconnect

        Uses aclosing() to ensure proper cleanup of the broadcaster subscription
        even if streaming is interrupted.

        Issue #444: Uses broadcaster factory for multi-instance support.
        Redis broadcaster shares events across all backend instances.

        """
        try:
            # Issue #444: Get broadcaster from factory (Redis or in-memory based on config)
            broadcaster = await get_broadcaster(_get_broadcaster_backend())

            # Use aclosing() to ensure proper cleanup of async generator
            # Type ignore: broadcaster.subscribe returns AsyncIterator which supports aclose()
            async with aclosing(broadcaster.subscribe(channel)) as subscription:  # type: ignore[type-var]
                async for event in subscription:
                    # Format event for SSE
                    event_type = str(event.get("type", "message"))
                    yield {
                        "event": event_type,
                        "data": json.dumps(event),
                    }

                    # Close connection on complete event
                    if event.get("type") == "complete":
                        logger.info(
                            "sse_complete_event_sent",
                            analysis_id=str(analysis_id),
                            channel=channel,
                        )
                        break

        except asyncio.CancelledError:
            # sse-starlette 3.0.3 automatically cancels on client disconnect
            # This exception is properly propagated by the library
            # No manual cleanup needed - library handles it
            logger.info(
                "sse_connection_cancelled",
                analysis_id=str(analysis_id),
                channel=channel,
            )
            raise
        except ConnectionError as e:
            # Granular error type for connection issues
            # sse-starlette 3.0.3 provides better error propagation
            logger.warning(
                "sse_connection_error",
                analysis_id=str(analysis_id),
                channel=channel,
                error_type="ConnectionError",
                error=str(e),
            )
            # Send structured error event with error type for client debugging
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "error_type": "ConnectionError",
                        "analysis_id": str(analysis_id),
                        "error": "Connection error occurred",
                        "message": str(e),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                ),
            }
        except TimeoutError as e:
            # Granular error type for timeout issues
            logger.warning(
                "sse_timeout_error",
                analysis_id=str(analysis_id),
                channel=channel,
                error_type="TimeoutError",
                error=str(e),
            )
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "error_type": "TimeoutError",
                        "analysis_id": str(analysis_id),
                        "error": "Connection timeout occurred",
                        "message": str(e),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                ),
            }
        except Exception as e:
            # Catch-all for other exceptions with full error details
            # sse-starlette 3.0.3 has better exception propagation
            logger.error(
                "sse_unexpected_error",
                analysis_id=str(analysis_id),
                channel=channel,
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True,
            )
            # Send error event with error type for better client debugging
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "error_type": type(e).__name__,
                        "analysis_id": str(analysis_id),
                        "error": "Unexpected error occurred",
                        "message": str(e),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                ),
            }
        finally:
            # Resource cleanup: unsubscribe from broadcaster if needed
            # EventBroadcaster automatically cleans up on subscription end,
            # but we log for monitoring
            logger.debug(
                "sse_event_generator_exiting",
                analysis_id=str(analysis_id),
                channel=channel,
            )

    # Configure EventSourceResponse with sse-starlette 3.0.3 enhancements
    # - client_close_handler_callable: Automatic cleanup logging on disconnect
    # - send_timeout: Prevent hanging connections from unresponsive clients (30 seconds)
    return EventSourceResponse(
        event_generator(),
        client_close_handler_callable=client_close_handler,
        send_timeout=30.0,  # 30 seconds timeout for unresponsive clients
    )
