"""Progress persistence service for writing SSE events to database.

This module provides fire-and-forget persistence of SSE events to the
analysis_progress table, following the background task pattern from analyze.py.

Note: Persistence is skipped during benchmark mode to avoid FK constraint
violations from synthetic analysis_ids that don't exist in the analyses table.
"""

import asyncio
import uuid

from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.core.types import EventData
from app.db.models.progress import AnalysisProgress
from app.db.session import AsyncSessionLocal

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

    Note: task.exception() re-raises CancelledError if the task was cancelled,
    so we must handle that case explicitly to avoid noisy error logs during
    shutdown or test teardown.

    Args:
        task: Completed asyncio task

    """
    _progress_tasks.discard(task)

    # Handle CancelledError explicitly - task.exception() re-raises it
    # This is expected during shutdown/test teardown, not an error
    try:
        exception = task.exception()
    except asyncio.CancelledError:
        logger.debug(
            "progress_persistence_task_cancelled",
            context="task_cancelled_during_shutdown",
        )
        return

    if exception is not None:
        logger.warning(
            "progress_persistence_task_failed",
            error_type=type(exception).__name__,
            error_message=str(exception),
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
    # Validate UUID BEFORE opening database session (fail-fast pattern)
    # This prevents ValueError during session cleanup which causes confusing
    # CancelledError chains during test teardown or shutdown
    try:
        analysis_id = uuid.UUID(str(event_data["analysis_id"]))
    except (ValueError, KeyError) as e:
        logger.warning(
            "progress_persistence_invalid_analysis_id",
            analysis_id=event_data.get("analysis_id"),
            stage=event_data.get("stage"),
            error=str(e),
        )
        return  # Early exit - don't open session for invalid data

    try:
        # Serialize UUID objects to strings for JSONB storage
        serialized_data = _serialize_event_data(event_data)

        async with AsyncSessionLocal() as db_session:
            progress = AnalysisProgress(
                analysis_id=analysis_id,  # Already validated above
                stage=event_data["stage"],
                status=event_data["status"],
                progress_data=serialized_data,  # Store serialized event data as JSONB
            )
            db_session.add(progress)
            await db_session.commit()

            logger.debug(
                "progress_event_persisted",
                analysis_id=str(analysis_id),
                stage=event_data["stage"],
                status=event_data["status"],
            )
    except (SQLAlchemyError, KeyError) as e:
        # Log but don't raise - persistence failure shouldn't break SSE
        # SQLAlchemyError: Database errors (connection, constraint violations)
        # KeyError: Missing required event_data fields (stage, status)
        logger.warning(
            "progress_persistence_failed",
            analysis_id=str(analysis_id),
            stage=event_data.get("stage"),
            error=str(e),
            exc_info=True,
        )


def persist_progress_event_async(event_data: EventData) -> asyncio.Task[None] | None:
    """Schedule progress event persistence as background task.

    Follows pattern from analyze.py for background task management.
    Tasks are tracked to prevent garbage collection and have completion
    callbacks for error handling.

    **Best Practice (Issue #507)**: Returns the task for optional awaiting.
    In production code, callers can ignore the return value (fire-and-forget).
    In tests, callers can await the task to eliminate race conditions.

    Note: Skips persistence during benchmark mode to avoid FK constraint
    violations from synthetic analysis_ids.

    Args:
        event_data: SSE event data dictionary

    Returns:
        The asyncio.Task if created, None if skipped (benchmark mode)

    """
    # Skip persistence during benchmarks - synthetic UUIDs don't exist in analyses table
    if _is_benchmark_mode():
        logger.debug(
            "progress_persistence_skipped_benchmark_mode",
            analysis_id=event_data.get("analysis_id"),
            stage=event_data.get("stage"),
        )
        return None

    task: asyncio.Task[None] = asyncio.create_task(persist_progress_event(event_data))
    _progress_tasks.add(task)
    task.add_done_callback(_handle_progress_task_completion)
    return task
