"""Event emission service for workflow events."""

import uuid

from app.core.logging import get_logger
from app.shared.services.messaging.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


class WorkflowEventEmitter:
    """Service for emitting SSE events during workflow execution."""

    async def emit_error(
        self, analysis_id: uuid.UUID, error: BaseException | Exception
    ) -> None:
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

    async def emit_completion(
        self,
        analysis_id: uuid.UUID,
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

