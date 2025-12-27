"""Event emission service for workflow events."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.branded_ids import AnalysisID
from app.core.exceptions import WorkflowStageError
from app.core.logging import get_logger
from app.db.models.progress import AnalysisProgress
from app.db.session import AsyncSessionLocal
from app.shared.services.messaging.sse_helpers import emit_error_event, emit_streaming_event

logger = get_logger(__name__)


class WorkflowEventEmitter:
    """Service for emitting SSE events during workflow execution."""

    async def _check_recent_error_event(
        self, analysis_id: AnalysisID, lookback_seconds: int = 30
    ) -> bool:
        """Check if an error event was recently emitted for this analysis.

        This helps avoid duplicate error events when a node-level error
        has already been emitted and the orchestrator catches the exception.

        Args:
            analysis_id: UUID of the analysis
            lookback_seconds: How many seconds to look back for recent events (default: 30)

        Returns:
            True if a recent error event exists, False otherwise

        """
        try:
            cutoff_time = datetime.now(UTC) - timedelta(seconds=lookback_seconds)
            async with AsyncSessionLocal() as session:
                stmt = (
                    select(AnalysisProgress)
                    .where(AnalysisProgress.analysis_id == analysis_id)
                    .where(AnalysisProgress.progress_data["type"].astext == "error")
                    .where(AnalysisProgress.created_at >= cutoff_time)
                    .order_by(AnalysisProgress.created_at.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                event = result.scalar_one_or_none()
                return event is not None
        except Exception as e:  # noqa: BLE001 - Safety net: if check fails, emit event anyway
            # Log but don't fail - if check fails, we'll emit the event anyway (safe default)
            logger.warning(
                "recent_error_event_check_failed",
                analysis_id=str(analysis_id),
                error=str(e),
            )
            return False

    async def emit_error(
        self,
        analysis_id: AnalysisID,
        error: BaseException | Exception,
        stage: str | None = None,
    ) -> None:
        """Emit SSE error event for workflow failure.

        Extracts stage from WorkflowStageError exceptions if available, otherwise
        requires explicit stage parameter. No default "workflow" stage - all errors
        must be stage-specific.

        Checks for recent error events to avoid duplicates (if a node already emitted
        a stage-specific error, the orchestrator shouldn't emit a duplicate).

        Args:
            analysis_id: UUID of the analysis
            error: Exception that caused the failure
            stage: Stage name (required if error is not a WorkflowStageError)

        Raises:
            ValueError: If stage is not provided and error is not a WorkflowStageError

        """
        # Extract stage from WorkflowStageError if available
        if isinstance(error, WorkflowStageError):
            error_stage = error.stage
            # Use the original exception for error message
            error_message = str(error.original_exception)
        else:
            # Require explicit stage - no default fallback
            if stage is None:
                error_type_name = type(error).__name__
                error_msg = (
                    f"Stage must be provided when error is not WorkflowStageError. "
                    f"Got error type: {error_type_name}"
                )
                raise ValueError(error_msg)
            error_stage = stage
            error_message = str(error)

        # Check if a recent error event already exists (node may have already emitted)
        # Skip emission if node already emitted an error to avoid duplicates
        has_recent_error = await self._check_recent_error_event(analysis_id)
        if has_recent_error:
            logger.debug(
                "orchestrator_error_skipped_duplicate",
                analysis_id=str(analysis_id),
                stage=error_stage,
                message="Recent error event exists, skipping duplicate error emission",
            )
            return

        # Emit error event using standardized helper
        await emit_error_event(
            analysis_id=str(analysis_id),
            stage=error_stage,
            error=error_message,
            error_code=None,  # Let nodes set specific error codes
        )

    async def emit_completion(
        self,
        analysis_id: AnalysisID,
        artifact_id: str | None,
        trace_id: str | None,
    ) -> None:
        """Emit SSE completion event for successful workflow.

        Args:
            analysis_id: UUID of the analysis
            artifact_id: UUID of the generated artifact (if available)
            trace_id: Langfuse trace ID for feedback submission

        """
        from app.core.agent_config import get_stage_name

        if artifact_id:
            await emit_streaming_event(
                "complete",
                analysis_id=str(analysis_id),
                stage=get_stage_name("artifact_generation"),
                status="complete",
                artifact_id=artifact_id,
                trace_id=trace_id,
            )
            logger.info(
                "workflow_complete_event_emitted",
                analysis_id=str(analysis_id),
                artifact_id=artifact_id,
                trace_id=trace_id,
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
                trace_id=trace_id,
            )
