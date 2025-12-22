"""Status update service for analysis records."""

import uuid

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


class StatusUpdater:
    """Service for updating analysis status in database."""

    async def update(self, analysis_id: uuid.UUID, status: str) -> None:
        """Update analysis status in database.

        Args:
            analysis_id: UUID of the analysis to update
            status: New status value (e.g., "complete", "failed", "artifact_failed")

        """
        try:
            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
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
                status=status,
                error=str(db_error),
                exc_info=True,
            )
