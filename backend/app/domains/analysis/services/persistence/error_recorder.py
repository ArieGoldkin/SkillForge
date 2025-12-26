"""Error recording service for analysis records.

Records error details to the Analysis table's error tracking fields
(error_code, error_message, failed_at_stage) for debugging and monitoring.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)

# Maximum length for error_message field (Analysis.error_message is Text, but we truncate for safety)
MAX_ERROR_MESSAGE_LENGTH = 2000


class ErrorRecorder:
    """Service for recording error details in Analysis table."""

    async def record(
        self,
        analysis_id: AnalysisID,
        error_code: str,
        error_message: str,
        stage: str,
    ) -> None:
        """Record error details to Analysis table.

        Updates the error tracking fields in the Analysis table to record when
        and where an error occurred during the analysis workflow.

        Args:
            analysis_id: UUID string of the analysis that encountered an error
            error_code: Error code identifier (e.g., "SECURITY_AUDITOR_FAILED")
            error_message: Human-readable error message (will be truncated to 2000 chars)
            stage: Stage/node name where the error occurred (e.g., "security_auditor")

        """
        try:
            # Convert string UUID to UUID object for database query (or use directly if already UUID)
            analysis_uuid = (
                analysis_id if isinstance(analysis_id, uuid.UUID) else uuid.UUID(str(analysis_id))
            )

            async with AsyncSessionLocal() as db_session:
                # Fetch the analysis record
                result = await db_session.execute(
                    select(Analysis).where(Analysis.id == analysis_uuid)
                )
                analysis = result.scalar_one_or_none()

                if not analysis:
                    logger.warning(
                        "error_recorder_analysis_not_found",
                        analysis_id=str(analysis_id),
                        error_code=error_code,
                        stage=stage,
                    )
                    return

                # Truncate error message to fit column constraints
                truncated_message = error_message[:MAX_ERROR_MESSAGE_LENGTH]
                if len(error_message) > MAX_ERROR_MESSAGE_LENGTH:
                    logger.info(
                        "error_recorder_message_truncated",
                        analysis_id=str(analysis_id),
                        original_length=len(error_message),
                        truncated_length=MAX_ERROR_MESSAGE_LENGTH,
                    )

                # Update error tracking fields
                analysis.error_code = error_code
                analysis.error_message = truncated_message
                analysis.failed_at_stage = stage
                analysis.updated_at = datetime.now(UTC)

                await db_session.commit()

                logger.info(
                    "error_recorder_recorded",
                    analysis_id=str(analysis_id),
                    error_code=error_code,
                    stage=stage,
                    error_preview=truncated_message[:100],  # Log first 100 chars
                )
        except Exception as db_error:
            logger.error(
                "error_recorder_failed",
                analysis_id=str(analysis_id),
                error_code=error_code,
                stage=stage,
                error=str(db_error),
                exc_info=True,
            )
            # Don't raise - error recording should not break the workflow

    async def record_warning(
        self,
        analysis_id: AnalysisID,
        warning_code: str,
        warning_message: str,
        stage: str,
    ) -> None:
        """Record a non-fatal warning (doesn't set status to failed).

        Use this for "soft" failures that don't prevent the analysis from
        completing, such as G-Eval scoring failures or annotation queue errors.

        Args:
            analysis_id: UUID string of the analysis
            warning_code: Warning code (e.g., "ARTIFACT_G_EVAL_SCORING_FAILED")
            warning_message: Human-readable warning description
            stage: Workflow stage where warning occurred

        Note:
            Currently this only logs the warning. In the future, this could
            write to a separate warnings table or append to a warnings field.

        """
        logger.warning(
            "workflow_warning_recorded",
            analysis_id=analysis_id,
            warning_code=warning_code,
            warning_message=warning_message,
            stage=stage,
            message="Non-fatal warning recorded (analysis continues)",
        )


# Singleton instance for import convenience
error_recorder = ErrorRecorder()
