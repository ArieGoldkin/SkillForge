"""Background task runner for analysis workflows."""

import uuid
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis
from app.services.sse_helpers import emit_streaming_event
from app.workflows.analysis import analysis_workflow

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

        # Emit initial progress event
        await emit_streaming_event(
            "progress",
            analysis_id=str(analysis_id),
            stage="workflow",
            status="running",
        )

        # Run workflow with checkpointing
        # LangGraph's Pregel.ainvoke has complex state/config types that mypy can't resolve
        config: dict[str, Any] = {"configurable": {"thread_id": str(analysis_id)}}
        input_state = {"url": url, "analysis_id": str(analysis_id)}
        await analysis_workflow.ainvoke(input_state, config=config)  # type: ignore[arg-type]

        logger.info(
            "workflow_task_complete",
            analysis_id=str(analysis_id),
        )

    except Exception as e:
        logger.error(
            "workflow_task_failed",
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True,
        )

        # Update Analysis status to failed
        try:
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

