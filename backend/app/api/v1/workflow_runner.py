"""Background task runner for analysis workflows."""

from __future__ import annotations

import asyncio
import uuid
from typing import TYPE_CHECKING

from langsmith import traceable

from app.core.logging import get_logger
from app.core.timeout_config import create_runnable_config
from app.services.sse_helpers import emit_streaming_event
from app.workflows.analysis import analysis_workflow

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


@traceable(
    name="analysis_workflow",
    run_type="chain",
    tags=["workflow", "analysis"],
)
async def run_workflow_task(analysis_id: uuid.UUID, url: str) -> None:
    """Run analysis workflow in background task.

    This function is executed asynchronously after the endpoint returns.
    It runs the workflow and handles errors, updating the Analysis status.

    The @traceable decorator ensures LangGraph's internal node/LLM traces
    nest properly under this outer trace in LangSmith.

    Args:
        analysis_id: UUID of the analysis
        url: URL to analyze

    """
    workflow_completed = False  # Track completion status for GeneratorExit handling
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
        }

        # Execute workflow with detailed error logging for debugging
        logger.debug(
            "workflow_execution_starting",
            analysis_id=str(analysis_id),
            url=url,
            thread_id=str(analysis_id),
        )
        try:
            result = await analysis_workflow.ainvoke(input_state, config=config)  # type: ignore[arg-type]
            workflow_completed = True  # Mark as completed successfully
            logger.debug(
                "workflow_execution_completed",
                analysis_id=str(analysis_id),
                result_keys=list(result.keys()) if isinstance(result, dict) else "non-dict",
            )
        except GeneratorExit as gen_exit:
            if workflow_completed:
                # GeneratorExit during cleanup after successful completion
                # This is normal - log at DEBUG and suppress
                logger.debug(
                    "workflow_cleanup_generator_exit",
                    analysis_id=str(analysis_id),
                    error_type="GeneratorExit",
                    error_message=str(gen_exit),
                    exc_info=True,
                    context="workflow_ainvoke_cleanup",
                    note=(
                        "GeneratorExit caught during cleanup after successful workflow completion. "
                        "This is normal generator lifecycle behavior when LangGraph's pregel "
                        "module closes async generators during cleanup. "
                        "Suppressing to prevent false errors."
                    ),
                )
                # Don't re-raise - this is expected cleanup behavior
            else:
                # GeneratorExit during execution - this is a real error
                logger.error(
                    "workflow_execution_generator_exit",
                    analysis_id=str(analysis_id),
                    error_type="GeneratorExit",
                    error_message=str(gen_exit),
                    exc_info=True,
                    context="workflow_ainvoke_execution",
                    note=(
                        "GeneratorExit caught during workflow execution (before completion). "
                        "This indicates the workflow was interrupted or cancelled. "
                        "Check LangGraph streaming and timeout configuration."
                    ),
                )
                # Re-raise to be caught by outer BaseException handler
                raise
        except BaseException as workflow_error:
            # Catch all other exceptions for detailed logging
            logger.error(
                "workflow_execution_error",
                analysis_id=str(analysis_id),
                error_type=type(workflow_error).__name__,
                error_message=str(workflow_error),
                exc_info=True,  # Include full stack trace
                context="workflow_ainvoke",
            )
            # Re-raise to be caught by outer handler
            raise
        finally:
            # Check for cleanup exceptions that occur after ainvoke returns
            # LangGraph's pregel module may close generators during cleanup,
            # raising GeneratorExit in a different execution context
            try:
                # Give a small window for cleanup to complete
                # This allows us to catch GeneratorExit that occurs during cleanup
                await asyncio.sleep(0.1)
                # Check current task for any pending exceptions
                current_task = asyncio.current_task()
                if current_task and current_task.done():
                    exc = current_task.exception()
                    if exc is not None and isinstance(exc, GeneratorExit):
                        # Cleanup GeneratorExit - log at DEBUG level
                        logger.debug(
                            "workflow_cleanup_generator_exit",
                            analysis_id=str(analysis_id),
                            error_type="GeneratorExit",
                            error_message=str(exc),
                            exc_info=True,
                            context="workflow_cleanup_phase",
                            note=(
                                "GeneratorExit caught during cleanup phase after workflow "
                                "execution. This is normal generator lifecycle behavior when "
                                "LangGraph's pregel module closes async generators during cleanup. "
                                "The workflow completed successfully."
                            ),
                        )
            except GeneratorExit as cleanup_exit:
                # Catch GeneratorExit that occurs during cleanup check itself
                # This is normal cleanup behavior - log at DEBUG
                logger.debug(
                    "workflow_cleanup_generator_exit",
                    analysis_id=str(analysis_id),
                    error_type="GeneratorExit",
                    error_message=str(cleanup_exit),
                    exc_info=True,
                    context="workflow_cleanup_check",
                    note=(
                        "GeneratorExit caught during cleanup exception check. "
                        "This is normal generator lifecycle behavior when LangGraph's pregel "
                        "module closes async generators during cleanup after workflow execution "
                        "completes."
                    ),
                )
                # Don't re-raise - cleanup exceptions shouldn't break the workflow
            except Exception as cleanup_check_error:
                # Log but don't raise - cleanup check errors shouldn't break workflow
                logger.warning(
                    "workflow_cleanup_check_error",
                    analysis_id=str(analysis_id),
                    error_type=type(cleanup_check_error).__name__,
                    error_message=str(cleanup_check_error),
                    context="workflow_cleanup_check",
                )

        logger.info(
            "workflow_task_complete",
            analysis_id=str(analysis_id),
        )

        # Update Analysis status to complete
        # Import DB modules lazily to avoid DATABASE_URL validation at import time
        try:
            from sqlalchemy import select

            from app.db.session import AsyncSessionLocal
            from app.models.analysis import Analysis

            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                analysis = result.scalar_one_or_none()
                if analysis:
                    analysis.status = "complete"  # type: ignore[assignment]
                    await db_session.commit()
                    logger.info(
                        "workflow_task_status_updated",
                        analysis_id=str(analysis_id),
                        status="complete",
                    )
        except Exception as db_error:
            logger.error(
                "workflow_task_status_update_failed",
                analysis_id=str(analysis_id),
                error=str(db_error),
                exc_info=True,
            )
            # Don't raise - workflow completed successfully, status update is secondary

        # Emit completion event with artifact_id per SSE_SCHEMA.md
        # Query artifact by analysis_id to get artifact_id for complete event
        try:
            from app.core.agent_config import get_stage_name
            from app.db.repositories.artifact_repository import ArtifactRepository
            from app.db.session import AsyncSessionLocal

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

    except GeneratorExit as gen_exit:
        # GeneratorExit is a BaseException that occurs when async generators are closed
        # If workflow completed successfully, this is normal cleanup behavior
        # If workflow didn't complete, this is an error
        if workflow_completed:
            # Cleanup GeneratorExit after successful completion - log at DEBUG
            logger.debug(
                "workflow_task_cleanup_generator_exit",
                analysis_id=str(analysis_id),
                error_type="GeneratorExit",
                error_message=str(gen_exit),
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
        else:
            # GeneratorExit during execution - this is a real error
            logger.error(
                "workflow_task_execution_generator_exit",
                analysis_id=str(analysis_id),
                error_type="GeneratorExit",
                error_message=str(gen_exit),
                exc_info=True,
                context="workflow_task_runner_execution",
                note=(
                    "GeneratorExit caught at workflow task level during execution. "
                    "This typically occurs when LangGraph's pregel module closes "
                    "an async generator during timeout or cancellation. "
                    "Check LangGraph streaming and timeout configuration."
                ),
            )
            # Re-raise to propagate (GeneratorExit is a BaseException)
            raise
    except BaseException as e:
        # Handle other BaseExceptions (SystemExit, KeyboardInterrupt) and regular Exceptions
        logger.error(
            "workflow_task_failed",
            analysis_id=str(analysis_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
            context="workflow_task_runner",
        )

        # Update Analysis status to failed
        # Import DB modules lazily to avoid DATABASE_URL validation at import time
        try:
            from sqlalchemy import select

            from app.db.session import AsyncSessionLocal
            from app.models.analysis import Analysis

            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                analysis = result.scalar_one_or_none()
                if analysis:
                    analysis.status = "failed"  # type: ignore[assignment]
                    await db_session.commit()
        except Exception as db_error:
            logger.error(
                "workflow_task_status_update_failed",
                analysis_id=str(analysis_id),
                error=str(db_error),
                exc_info=True,
            )

        # Emit error event
        await emit_streaming_event(
            "error",
            analysis_id=str(analysis_id),
            stage="workflow",
            status="failed",
            error=str(e),
        )
