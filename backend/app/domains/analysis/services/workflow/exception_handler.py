"""Exception handling service for workflow execution."""

import uuid

from app.core.logging import get_logger
from app.domains.analysis.schemas.api import AnalysisStatus
from app.domains.analysis.services.events import WorkflowEventEmitter
from app.domains.analysis.services.persistence import StatusUpdater

logger = get_logger(__name__)


async def handle_workflow_exception(
    exc: BaseException | Exception,
    analysis_id: uuid.UUID,
    workflow_completed: bool,
) -> None:
    """Handle workflow exceptions with status updates and SSE events.

    This unified handler processes GeneratorExit and RuntimeError (converted from GeneratorExit)
    exceptions, distinguishing between cleanup (normal) and execution (error) scenarios.

    Python's async runtime converts GeneratorExit to RuntimeError in async functions.
    This handler normalizes both cases and handles them consistently.

    Args:
        exc: The exception to handle (GeneratorExit, RuntimeError, or other)
        analysis_id: UUID of the analysis
        workflow_completed: Whether the workflow completed successfully before the exception

    Raises:
        The exception is re-raised if it's an execution error (not cleanup).
        Returns None if the exception should be suppressed (cleanup GeneratorExit).

    Note:
        GeneratorExit during cleanup after successful completion is normal behavior
        when LangGraph's pregel module closes async generators. These are suppressed.
        GeneratorExit during execution indicates workflow interruption/cancellation.

    """
    # Check if this is a GeneratorExit or converted RuntimeError
    is_generator_exit = isinstance(exc, GeneratorExit)
    is_converted_generator_exit = isinstance(
        exc, RuntimeError
    ) and "coroutine ignored GeneratorExit" in str(exc)

    if is_generator_exit or is_converted_generator_exit:
        if workflow_completed:
            # Cleanup GeneratorExit - normal behavior, suppress it
            logger.debug(
                "workflow_task_cleanup_generator_exit",
                analysis_id=str(analysis_id),
                error_type=type(exc).__name__,
                error_message=str(exc),
                context="workflow_task_runner_cleanup",
                note=(
                    "GeneratorExit caught at workflow task level during cleanup. "
                    "This is normal generator lifecycle behavior when LangGraph's pregel module "
                    "closes async generators during cleanup after successful workflow completion. "
                    "Suppressing to prevent false errors."
                ),
            )
            # Don't re-raise - this is expected cleanup behavior
            return
        # Execution GeneratorExit - real error, handle it
        logger.error(
            "workflow_task_execution_generator_exit",
            analysis_id=str(analysis_id),
            error_type=type(exc).__name__,
            error_message=str(exc),
            context="workflow_task_runner_execution",
            note=(
                "GeneratorExit caught at workflow task level during execution. "
                "This typically occurs when LangGraph's pregel module closes "
                "an async generator during timeout or cancellation. "
                "Check LangGraph streaming and timeout configuration."
            ),
        )
        # Update status and emit error event before re-raising
        status_updater = StatusUpdater()
        event_emitter = WorkflowEventEmitter()
        await status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
        await event_emitter.emit_error(analysis_id, exc)
        # Re-raise to propagate (explicit re-raise for ruff PLE0704)
        raise exc
    # Other exception - handle as error
    logger.error(
        "workflow_task_failed",
        analysis_id=str(analysis_id),
        error=str(exc),
        error_type=type(exc).__name__,
        context="workflow_task_runner",
    )
    # Update status and emit error event before re-raising
    status_updater = StatusUpdater()
    event_emitter = WorkflowEventEmitter()
    await status_updater.update(analysis_id, AnalysisStatus.FAILED.value)
    await event_emitter.emit_error(analysis_id, exc)
    # Re-raise to propagate (explicit re-raise for ruff PLE0704)
    raise exc

