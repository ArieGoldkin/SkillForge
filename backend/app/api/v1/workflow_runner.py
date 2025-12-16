"""Background task runner for analysis workflows."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.constants import DEFAULT_TITLE
from app.core.logging import get_logger
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable
from app.services.messaging.sse_helpers import emit_streaming_event
from app.workflows.analysis import analysis_workflow

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


def _validate_workflow_result(workflow_result: dict) -> list[str]:
    """Validate required workflow result fields and return missing ones."""
    required_fields = ["raw_content", "extraction_metadata", "content_embedding"]
    missing_fields: list[str] = []

    for field in required_fields:
        value = workflow_result.get(field)
        if not value:
            missing_fields.append(field)

    return missing_fields


async def _update_analysis_status(analysis_id: uuid.UUID, status: str) -> None:
    """Update analysis status in database.

    Args:
        analysis_id: UUID of the analysis to update
        status: New status value ("complete", "failed", etc.)

    """
    try:
        from sqlalchemy import select

        from app.db.session import AsyncSessionLocal
        from app.models.analysis import Analysis

        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one_or_none()
            if analysis:
                analysis.status = status  # type: ignore[assignment]
                await db_session.commit()
                logger.info(
                    "workflow_task_status_updated",
                    analysis_id=str(analysis_id),
                    status=status,
                )
    except Exception as db_error:
        logger.error(
            "workflow_task_status_update_failed",
            analysis_id=str(analysis_id),
            error=str(db_error),
            exc_info=True,
        )


async def _persist_analysis_data(analysis_id: uuid.UUID, workflow_result: dict) -> bool:
    """Persist workflow results to the analysis record.

    Updates the analysis with extracted content, title, and embedding data.
    This enables full-text search (via search_vector trigger) and semantic search.

    Args:
        analysis_id: UUID of the analysis to update
        workflow_result: Dictionary containing workflow state with:
            - raw_content: Extracted text content
            - extraction_metadata: Metadata dict with title, word_count, etc.
            - content_embedding: Vector embedding (1536 dimensions)

    Returns:
        bool: True if data was persisted successfully, False otherwise

    """
    try:
        from sqlalchemy import select

        from app.db.session import AsyncSessionLocal
        from app.models.analysis import Analysis

        async with AsyncSessionLocal() as db_session:
            result = await db_session.execute(select(Analysis).where(Analysis.id == analysis_id))
            analysis = result.scalar_one_or_none()

            if not analysis:
                logger.warning(
                    "persist_analysis_data_not_found",
                    analysis_id=str(analysis_id),
                )
                return False

            # Persist raw content
            raw_content = workflow_result.get("raw_content")
            if raw_content:
                analysis.raw_content = raw_content  # type: ignore[assignment]
            else:
                logger.warning(
                    "persist_missing_raw_content",
                    analysis_id=str(analysis_id),
                    message="Workflow result missing raw_content",
                )

            # Extract and persist title from extraction_metadata
            extraction_metadata = workflow_result.get("extraction_metadata")
            if extraction_metadata and isinstance(extraction_metadata, dict):
                analysis.extraction_metadata = extraction_metadata  # type: ignore[assignment]
                title = extraction_metadata.get("title")
                if title:
                    analysis.title = title  # type: ignore[assignment]
                else:
                    # Always persist a title - use default if extraction failed
                    analysis.title = DEFAULT_TITLE  # type: ignore[assignment]
                    logger.warning(
                        "persist_default_title",
                        analysis_id=str(analysis_id),
                        message=f"Title missing, using default: {DEFAULT_TITLE}",
                    )
            else:
                logger.warning(
                    "persist_missing_extraction_metadata",
                    analysis_id=str(analysis_id),
                    message="Workflow result missing extraction_metadata",
                )

            # Persist content embedding
            content_embedding = workflow_result.get("content_embedding")
            if content_embedding:
                analysis.content_embedding = content_embedding  # type: ignore[assignment]
            else:
                logger.warning(
                    "persist_missing_content_embedding",
                    analysis_id=str(analysis_id),
                    message="Workflow result missing content_embedding",
                )

            await db_session.commit()

            logger.info(
                "persist_analysis_data_success",
                analysis_id=str(analysis_id),
                has_raw_content=raw_content is not None,
                has_title=analysis.title is not None,
                has_embedding=content_embedding is not None,
                raw_content_length=len(raw_content) if raw_content else 0,
            )
            return True

    except Exception as db_error:
        logger.error(
            "persist_analysis_data_failed",
            analysis_id=str(analysis_id),
            error=str(db_error),
            exc_info=True,
        )
        error_message = f"Failed to persist analysis data: {db_error}"
        raise RuntimeError(error_message) from db_error


async def _emit_workflow_error(analysis_id: uuid.UUID, error: BaseException | Exception) -> None:
    """Emit SSE error event for workflow failure.

    Args:
        analysis_id: UUID of the analysis
        error: Exception that caused the failure

    """
    await emit_streaming_event(
        "error",
        analysis_id=str(analysis_id),
        stage="workflow",
        status="failed",
        error=str(error),
    )


async def _handle_workflow_exception(
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
                exc_info=True,
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
        else:
            # Execution GeneratorExit - real error, handle it
            logger.error(
                "workflow_task_execution_generator_exit",
                analysis_id=str(analysis_id),
                error_type=type(exc).__name__,
                error_message=str(exc),
                exc_info=True,
                context="workflow_task_runner_execution",
                note=(
                    "GeneratorExit caught at workflow task level during execution. "
                    "This typically occurs when LangGraph's pregel module closes "
                    "an async generator during timeout or cancellation. "
                    "Check LangGraph streaming and timeout configuration."
                ),
            )
            # Update status and emit error event before re-raising
            await _update_analysis_status(analysis_id, "failed")
            await _emit_workflow_error(analysis_id, exc)
            # Re-raise to propagate (explicit re-raise for ruff PLE0704)
            raise exc
    else:
        # Other exception - handle as error
        logger.error(
            "workflow_task_failed",
            analysis_id=str(analysis_id),
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
            context="workflow_task_runner",
        )
        # Update status and emit error event before re-raising
        await _update_analysis_status(analysis_id, "failed")
        await _emit_workflow_error(analysis_id, exc)
        # Re-raise to propagate (explicit re-raise for ruff PLE0704)
        raise exc


@robust_traceable(
    name="analysis_workflow",
    run_type="chain",
    tags=["workflow", "analysis"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "analysis",
    },
)
async def run_workflow_task(  # noqa: PLR0915
    analysis_id: uuid.UUID, url: str, skill_level: str = "intermediate"
) -> None:
    """Run analysis workflow in background task.

    This function is executed asynchronously after the endpoint returns.
    It runs the workflow and handles errors, updating the Analysis status.

    The robust_traceable decorator ensures LangGraph's internal node/LLM traces
    nest properly under this outer trace in LangSmith.

    Exception handling is done at the application boundary (this function) where
    we have context (analysis_id, status updates). GeneratorExit exceptions are
    handled by the unified _handle_workflow_exception() helper.

    Args:
        analysis_id: UUID of the analysis
        url: URL to analyze
        skill_level: User's experience level (beginner, intermediate, expert)

    """
    workflow_completed = False  # Track completion status for GeneratorExit handling

    # Runtime metadata updates
    try:
        from langsmith import get_current_run_tree

        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.metadata["analysis_id"] = str(analysis_id)
            run_tree.metadata["url"] = url
            run_tree.metadata["workflow_version"] = "1.0"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

    try:
        logger.info(
            "workflow_task_started",
            analysis_id=str(analysis_id),
            url=url,
        )

        # Create config with thread_id for checkpointing
        # Note: Workflow-level timeout is handled by step_timeout on graph
        config = create_runnable_config(thread_id=str(analysis_id))

        input_state: dict[str, str] = {
            "url": url,
            "analysis_id": str(analysis_id),
            "skill_level": skill_level,
        }

        # Execute workflow
        logger.debug(
            "workflow_execution_starting",
            analysis_id=str(analysis_id),
            url=url,
            thread_id=str(analysis_id),
        )
        result = await analysis_workflow.ainvoke(input_state, config=config)  # type: ignore[arg-type]
        workflow_completed = True  # Mark as completed successfully
        logger.debug(
            "workflow_execution_completed",
            analysis_id=str(analysis_id),
            result_keys=list(result.keys()) if isinstance(result, dict) else "non-dict",
        )

        logger.info(
            "workflow_task_complete",
            analysis_id=str(analysis_id),
        )

        # Persist workflow data to analysis record (Issue #168)
        # This enables full-text search (search_vector trigger) and semantic search
        if isinstance(result, dict):
            missing_fields = _validate_workflow_result(result)
            if missing_fields:
                logger.error(
                    "workflow_result_incomplete",
                    analysis_id=str(analysis_id),
                    missing_fields=missing_fields,
                    message="Workflow result missing required fields",
                )
                await _update_analysis_status(analysis_id, "failed")
                await _emit_workflow_error(
                    analysis_id,
                    ValueError(f"Workflow result incomplete: missing {missing_fields}"),
                )
                return

            persist_success = await _persist_analysis_data(analysis_id, result)
            if not persist_success:
                logger.error(
                    "workflow_persistence_failed",
                    analysis_id=str(analysis_id),
                    message="Failed to persist workflow data, marking as failed",
                )
                await _update_analysis_status(analysis_id, "failed")
                await _emit_workflow_error(
                    analysis_id,
                    RuntimeError("Workflow data persistence failed"),
                )
                return

        # Validate artifact exists before marking analysis complete
        # This ensures data integrity - analyses should not be marked complete without artifacts
        from app.core.agent_config import get_stage_name
        from app.db.repositories.artifact_repository import ArtifactRepository
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as db_session:
            repository = ArtifactRepository(session=db_session)
            artifact = await repository.get_artifact_by_analysis_id(analysis_id)

            if not artifact:
                logger.error(
                    "workflow_complete_without_artifact",
                    analysis_id=str(analysis_id),
                    error="Artifact generation failed or was skipped",
                )
                # Mark as failed - incomplete workflow
                await _update_analysis_status(analysis_id, "failed")
                await _emit_workflow_error(
                    analysis_id,
                    ValueError("Workflow completed but no artifact was generated"),
                )
                return

        # Update Analysis status to complete (only if artifact exists)
        await _update_analysis_status(analysis_id, "complete")

        # Emit completion event with artifact_id per SSE_SCHEMA.md
        # Reuse artifact from validation check above (already queried)
        # Also attach artifact info to LangSmith trace for visibility
        try:
            # Re-query artifact for SSE event (artifact variable from validation is out of scope)
            async with AsyncSessionLocal() as db_session:
                repository = ArtifactRepository(session=db_session)
                artifact = await repository.get_artifact_by_analysis_id(analysis_id)

                if artifact:
                    await emit_streaming_event(
                        "complete",
                        analysis_id=str(analysis_id),
                        stage=get_stage_name("artifact_generation"),
                        status="complete",
                        artifact_id=str(artifact.id),
                    )
                    logger.info(
                        "workflow_complete_event_emitted",
                        analysis_id=str(analysis_id),
                        artifact_id=str(artifact.id),
                    )
                else:
                    # Artifact not found - log warning but still emit complete event
                    logger.warning(
                        "workflow_complete_event_no_artifact",
                        analysis_id=str(analysis_id),
                        message="Artifact not found, emitting complete event without artifact_id",
                    )
                    await emit_streaming_event(
                        "complete",
                        analysis_id=str(analysis_id),
                        stage=get_stage_name("artifact_generation"),
                        status="complete",
                    )
        except Exception as event_error:
            logger.error(
                "workflow_complete_event_failed",
                analysis_id=str(analysis_id),
                error=str(event_error),
                exc_info=True,
            )
            # Don't raise - workflow completed successfully, event emission is secondary

    except (GeneratorExit, RuntimeError, BaseException) as exc:  # noqa: BLE001
        # Unified exception handling for all workflow exceptions
        # Python's async runtime converts GeneratorExit to RuntimeError in async functions
        # The handler normalizes both cases and handles them consistently
        # BaseException needed to catch GeneratorExit which doesn't inherit from Exception
        await _handle_workflow_exception(exc, analysis_id, workflow_completed)
