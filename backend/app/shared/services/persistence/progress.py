"""Progress persistence service for writing SSE events to database.

This module provides fire-and-forget persistence of SSE events to the
analysis_progress table, following the background task pattern from analyze.py.

Note: Persistence is skipped during benchmark mode to avoid FK constraint
violations from synthetic analysis_ids that don't exist in the analyses table.
"""

import asyncio
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.types import EventData
from app.db.models.progress import AnalysisProgress
from app.db.session import AsyncSessionLocal

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def _serialize_event_data(event_data: dict) -> dict:
    """Convert UUID objects to strings for JSON serialization.

    Recursively processes dictionaries and lists to ensure all UUID
    objects are converted to strings before storing in JSONB fields.

    Args:
        event_data: Event data dictionary that may contain UUID objects

    Returns:
        Dictionary with all UUID objects converted to strings

    """
    serialized: dict = {}
    for key, value in event_data.items():
        if isinstance(value, uuid.UUID):
            serialized[key] = str(value)
        elif isinstance(value, dict):
            serialized[key] = _serialize_event_data(value)
        elif isinstance(value, list):
            serialized[key] = [
                str(item)
                if isinstance(item, uuid.UUID)
                else (_serialize_event_data(item) if isinstance(item, dict) else item)
                for item in value
            ]
        else:
            serialized[key] = value
    return serialized


def _is_benchmark_mode() -> bool:
    """Check if currently running in benchmark mode.

    Imports lazily to avoid circular imports. Returns False if the
    benchmark module is not loaded or benchmark mode is not active.
    """
    try:
        from app.evaluation.llm_benchmark import is_benchmark_mode

        return is_benchmark_mode()
    except ImportError:
        # Benchmark module not available (e.g., in minimal deployments)
        return False


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
        # Serialize UUID objects to strings for JSONB storage
        serialized_data = _serialize_event_data(event_data)

        async with AsyncSessionLocal() as db_session:
            progress = AnalysisProgress(
                analysis_id=uuid.UUID(str(event_data["analysis_id"])),
                stage=event_data["stage"],
                status=event_data["status"],
                progress_data=serialized_data,  # Store serialized event data as JSONB
            )
            db_session.add(progress)
            await db_session.commit()

            logger.debug(
                "progress_event_persisted",
                analysis_id=event_data["analysis_id"],
                stage=event_data["stage"],
                status=event_data["status"],
            )
    except (SQLAlchemyError, ValueError, KeyError) as e:
        # Log but don't raise - persistence failure shouldn't break SSE
        # SQLAlchemyError: Database errors (connection, constraint violations)
        # ValueError: UUID conversion errors
        # KeyError: Missing required event_data fields
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

    Note: Skips persistence during benchmark mode to avoid FK constraint
    violations from synthetic analysis_ids.

    Args:
        event_data: SSE event data dictionary

    """
    # Skip persistence during benchmarks - synthetic UUIDs don't exist in analyses table
    if _is_benchmark_mode():
        logger.debug(
            "progress_persistence_skipped_benchmark_mode",
            analysis_id=event_data.get("analysis_id"),
            stage=event_data.get("stage"),
        )
        return

    task: asyncio.Task[None] = asyncio.create_task(persist_progress_event(event_data))
    _progress_tasks.add(task)
    task.add_done_callback(_handle_progress_task_completion)
