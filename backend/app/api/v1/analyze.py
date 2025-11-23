"""Analysis endpoints for content analysis pipeline."""

import asyncio
import json
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from app.core.logging import get_logger
from app.services.event_broadcaster import broadcaster

router = APIRouter(tags=["analyze"])
logger = get_logger(__name__)


@router.get("/analyze/{analysis_id}/stream")
async def stream_analysis_progress(
    analysis_id: uuid.UUID,
    request: Request,
) -> EventSourceResponse:
    """Stream real-time analysis progress via Server-Sent Events (SSE).

    Establishes an SSE connection for the specified analysis and streams
    progress events as they occur during workflow execution. Events include
    stage updates, status changes, and completion notifications.

    Args:
        analysis_id: UUID of the analysis to stream progress for
        request: FastAPI request object (used for disconnect detection)

    Returns:
        EventSourceResponse streaming SSE events

    Raises:
        404: If analysis_id is invalid or not found (handled by FastAPI)

    Example:
        Client connects to `/api/v1/analyze/{id}/stream` and receives:
        ```
        event: progress
        data: {"type": "progress", "stage": "extraction", "status": "running", ...}

        event: progress
        data: {"type": "progress", "stage": "extraction", "status": "complete", ...}

        event: complete
        data: {"type": "complete", "stage": "artifact_generation", ...}
        ```

    """
    channel = f"workflow:{analysis_id}"

    logger.info(
        "sse_connection_started",
        analysis_id=str(analysis_id),
        channel=channel,
    )

    async def event_generator() -> AsyncIterator[dict[str, str]]:
        """Generate SSE events from broadcaster subscription."""
        try:
            async for event in broadcaster.subscribe(channel):
                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(
                        "sse_client_disconnected",
                        analysis_id=str(analysis_id),
                    )
                    break

                # Format event for SSE
                yield {
                    "event": event.get("type", "message"),
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
            logger.info(
                "sse_connection_cancelled",
                analysis_id=str(analysis_id),
            )
            raise
        except Exception as e:
            logger.error(
                "sse_connection_error",
                analysis_id=str(analysis_id),
                error=str(e),
                exc_info=True,
            )
            # Send error event before closing
            yield {
                "event": "error",
                "data": json.dumps(
                    {
                        "type": "error",
                        "analysis_id": str(analysis_id),
                        "error": "Connection error occurred",
                    }
                ),
            }

    return EventSourceResponse(event_generator())


@router.get("/analyze/{analysis_id}")
async def get_analysis(
    analysis_id: uuid.UUID,
) -> JSONResponse:
    """Get analysis details by ID.

    Args:
        analysis_id: UUID of the analysis

    Returns:
        JSONResponse with analysis details

    Note:
        This is a placeholder endpoint. Full implementation will require
        repository pattern integration (Task 1.3.1).

    """
    # TODO(@yonatan): Implement with repository pattern (Issue #41)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "Analysis retrieval not yet implemented",
                "analysis_id": str(analysis_id),
            }
        },
    )
