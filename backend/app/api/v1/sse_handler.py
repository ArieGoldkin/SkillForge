"""SSE endpoint handler for analysis progress streaming."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

from app.core.logging import get_logger
from app.services.event_broadcaster import broadcaster

logger = get_logger(__name__)


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

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        """Generate SSE events from broadcaster subscription.

        Leverages sse-starlette 3.0.3 features:
        - Better exception propagation for clearer error messages
        - Improved cancellation handling with asyncio.CancelledError
        - Library's enhanced disconnect detection (still check manually for logging)
        """
        try:
            async for event in broadcaster.subscribe(channel):
                # sse-starlette 3.0 has better disconnect detection, but we still
                # check manually for logging purposes and early exit
                if await request.is_disconnected():
                    logger.info(
                        "sse_client_disconnected",
                        analysis_id=str(analysis_id),
                    )
                    break

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
                    )
                    break

        except asyncio.CancelledError:
            # sse-starlette 3.0 has improved cancellation handling
            # This exception is properly propagated by the library
            logger.info(
                "sse_connection_cancelled",
                analysis_id=str(analysis_id),
            )
            raise
        except ConnectionError as e:
            # Granular error type for connection issues
            # sse-starlette 3.0 provides better error propagation
            logger.warning(
                "sse_connection_error",
                analysis_id=str(analysis_id),
                error_type="ConnectionError",
                error=str(e),
            )
            # Send structured error event with error type
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "error_type": "ConnectionError",
                        "analysis_id": str(analysis_id),
                        "error": "Connection error occurred",
                        "message": str(e),
                    }
                ),
            }
        except TimeoutError as e:
            # Granular error type for timeout issues
            logger.warning(
                "sse_timeout_error",
                analysis_id=str(analysis_id),
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
                    }
                ),
            }
        except Exception as e:
            # Catch-all for other exceptions with full error details
            # sse-starlette 3.0 has better exception propagation
            logger.error(
                "sse_connection_error",
                analysis_id=str(analysis_id),
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
                    }
                ),
            }

    return EventSourceResponse(event_generator())
