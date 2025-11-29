"""Background task runner for analysis workflows."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.services.sse_helpers import emit_streaming_event
from app.workflows.analysis import analysis_workflow

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


async def run_workflow_task(analysis_id: uuid.UUID, url: str) -> None:
    """Run analysis workflow in background task.

    This function is executed asynchronously after the endpoint returns.
    It runs the workflow and handles errors, updating the Analysis status.

    Args:
        analysis_id: UUID of the analysis
        url: URL to analyze

    """
    try:
        logger.info(
            "workflow_task_started",
            analysis_id=str(analysis_id),
            url=url,
        )

        # Run workflow with checkpointing
        # StateGraph.ainvoke expects AnalysisState TypedDict
        config: dict[str, object] = {"configurable": {"thread_id": str(analysis_id)}}
        input_state: dict[str, str] = {
            "url": url,
            "analysis_id": str(analysis_id),
        }
        await analysis_workflow.ainvoke(input_state, config=config)  # type: ignore[arg-type]

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

    except BaseException as e:
        # Handle both Exception and BaseException (including GeneratorExit)
        logger.error(
            "workflow_task_failed",
            analysis_id=str(analysis_id),
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
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
