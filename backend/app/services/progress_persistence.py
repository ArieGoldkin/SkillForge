"""Progress persistence service for writing SSE events to database.

This module provides fire-and-forget persistence of SSE events to the
analysis_progress table, following the background task pattern from analyze.py.
"""

import asyncio
import uuid
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.core.types import EventData
from app.db.session import AsyncSessionLocal
from app.models.progress import AnalysisProgress

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# Track background tasks to prevent garbage collection
_progress_tasks: set[asyncio.Task[None]] = set()


def _handle_progress_task_completion(task: asyncio.Task[None]) -> None:
    """Handle progress persistence task completion.

    This callback checks for exceptions that occur during task execution
    and logs them appropriately. Errors in persistence should not break
    the SSE stream, so they are logged at WARNING level.

    Args:
        task: Completed asyncio task

    """
    _progress_tasks.discard(task)
    exception = task.exception()
    if exception is not None:
        logger.warning(
            "progress_persistence_task_failed",
            error_type=type(exception).__name__,
            error_message=str(exception),
            exc_info=True,
            context="progress_persistence_task_done_callback",
        )


async def persist_progress_event(event_data: EventData) -> None:
    """Persist progress event to database.

    Writes SSE events to the analysis_progress table for historical tracking
    and audit trails. Uses direct model access (acceptable for service layer).

    Non-blocking: errors are logged but don't affect SSE stream.

    Args:
        event_data: SSE event data dictionary

    """
    try:
        async with AsyncSessionLocal() as db_session:
            progress = AnalysisProgress(
                analysis_id=uuid.UUID(str(event_data["analysis_id"])),
                stage=event_data["stage"],
                status=event_data["status"],
                progress_data=event_data,  # Store full event data as JSONB
            )
            db_session.add(progress)
            await db_session.commit()

            logger.debug(
                "progress_event_persisted",
                analysis_id=event_data["analysis_id"],
                stage=event_data["stage"],
                status=event_data["status"],
            )
    except Exception as e:
        # Log but don't raise - persistence failure shouldn't break SSE
        logger.warning(
            "progress_persistence_failed",
            analysis_id=event_data.get("analysis_id"),
            stage=event_data.get("stage"),
            error=str(e),
            exc_info=True,
        )


def persist_progress_event_async(event_data: EventData) -> None:
    """Schedule progress event persistence as fire-and-forget task.

    Follows pattern from analyze.py for background task management.
    Tasks are tracked to prevent garbage collection and have completion
    callbacks for error handling.

    Args:
        event_data: SSE event data dictionary

    """
    task: asyncio.Task[None] = asyncio.create_task(persist_progress_event(event_data))
    _progress_tasks.add(task)
    task.add_done_callback(_handle_progress_task_completion)
