"""Annotation service for managing user feedback and quality-based queuing.

This service handles:
1. User feedback submission (thumbs up/down) with Langfuse score tracking
2. Automatic queuing of low-quality artifacts for human review
3. Integration with Langfuse Annotation Queue for UI-based review
4. Graceful degradation when Langfuse is unavailable

Architecture:
- Uses dependency injection for repository
- Langfuse integration for observability (optional)
- Dual queuing: Local database + Langfuse Annotation Queue
- Structured logging for debugging
"""

import uuid
from datetime import UTC, datetime
from typing import Annotated, Literal, TypedDict

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.langfuse_service import get_langfuse_service
from app.core.logging import get_logger
from app.db.models.annotation_queue import AnnotationQueue
from app.db.session import get_db

logger = get_logger(__name__)

FeedbackType = Literal["thumbs_up", "thumbs_down"]
QueueReason = Literal["low_quality", "negative_feedback", "flagged_by_user"]
QueueStatus = Literal["pending", "reviewed", "skipped"]


class SubmitFeedbackResult(TypedDict):
    """Return type for submit_feedback method."""

    status: str
    message: str
    langfuse_submitted: bool


class AnnotationService:
    """Service for managing artifact feedback and annotation queues.

    This service integrates with Langfuse for observability and manages
    the annotation queue for artifacts that need human review.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize annotation service with database session.

        Args:
            session: Async database session for persistence

        """
        self.session = session

    async def submit_feedback(
        self,
        artifact_id: uuid.UUID,
        trace_id: str | None,
        feedback: FeedbackType,
        comment: str | None = None,
    ) -> SubmitFeedbackResult:
        """Submit user feedback for an artifact.

        Converts feedback to Langfuse score (thumbs_up=1.0, thumbs_down=0.0)
        and optionally queues artifact for review if negative.

        Args:
            artifact_id: ID of the artifact being rated
            trace_id: Optional Langfuse trace ID for linking feedback
            feedback: User feedback type ("thumbs_up" or "thumbs_down")
            comment: Optional user comment explaining the feedback

        Returns:
            Status dict with keys:
                - status: str - "success" or "error"
                - message: str - Human-readable message
                - langfuse_submitted: bool - Whether Langfuse score was submitted

        Example:
            >>> service = AnnotationService(session)
            >>> result = await service.submit_feedback(
            ...     artifact_id=uuid.uuid4(),
            ...     trace_id="trace-123",
            ...     feedback="thumbs_down",
            ...     comment="Missing implementation details",
            ... )
            >>> assert result["status"] == "success"

        """
        logger.info(
            "feedback_submission_started",
            artifact_id=str(artifact_id),
            trace_id=trace_id,
            feedback=feedback,
            has_comment=bool(comment),
        )

        # Convert feedback to Langfuse score
        score_value = 1.0 if feedback == "thumbs_up" else 0.0

        # Submit to Langfuse (graceful degradation if unavailable)
        langfuse_submitted = await self._submit_langfuse_score(
            trace_id=trace_id,
            score_name="user_feedback",
            score_value=score_value,
            comment=comment,
        )

        # Queue for review if thumbs_down with comment
        queued_for_review = False
        if feedback == "thumbs_down" and comment:
            try:
                await self._queue_artifact(
                    artifact_id=artifact_id,
                    trace_id=trace_id,
                    reason="negative_feedback",
                    metadata={
                        "feedback": feedback,
                        "comment": comment,
                        "score": score_value,
                        "submitted_at": datetime.now(UTC).isoformat(),
                    },
                )
                queued_for_review = True

                logger.info(
                    "artifact_queued_from_feedback",
                    artifact_id=str(artifact_id),
                    reason="negative_feedback",
                )

            except Exception as e:
                logger.error(
                    "failed_to_queue_artifact",
                    artifact_id=str(artifact_id),
                    error=str(e),
                    exc_info=True,
                )
                # Return error response
                return {
                    "status": "error",
                    "message": f"Feedback recorded but failed to queue for review: {e}",
                    "langfuse_submitted": langfuse_submitted,
                }

        # Build success message
        message_parts = ["Feedback submitted successfully"]
        if queued_for_review:
            message_parts.append("queued for review")
        if langfuse_submitted:
            message_parts.append("tracked in Langfuse")

        message = (
            " - " + ", ".join(message_parts[1:]) if len(message_parts) > 1 else message_parts[0]
        )

        return {
            "status": "success",
            "message": message,
            "langfuse_submitted": langfuse_submitted,
        }

    async def queue_low_quality_artifact(
        self,
        artifact_id: uuid.UUID,
        trace_id: str | None,
        quality_scores: dict[str, float],
        threshold: float = 0.6,
    ) -> dict[str, object]:
        """Queue an artifact for review if quality scores are below threshold.

        Calculates average quality score from provided metrics and queues
        if below threshold.

        Args:
            artifact_id: ID of the artifact to check
            trace_id: Optional Langfuse trace ID
            quality_scores: Dict of quality metrics (e.g., {"relevance": 0.5, "depth": 0.4})
            threshold: Minimum average score required (default: 0.6)

        Returns:
            Status dict with keys:
                - success: bool - Whether operation completed
                - queued: bool - Whether artifact was queued
                - average_score: float - Calculated average score
                - below_threshold: bool - Whether score was below threshold
                - error: str | None - Error message if failed

        Example:
            >>> service = AnnotationService(session)
            >>> result = await service.queue_low_quality_artifact(
            ...     artifact_id=uuid.uuid4(),
            ...     trace_id="trace-456",
            ...     quality_scores={"relevance": 0.5, "depth": 0.4, "coherence": 0.6},
            ... )
            >>> assert result["below_threshold"]
            >>> assert result["queued"]

        """
        logger.info(
            "quality_check_started",
            artifact_id=str(artifact_id),
            quality_scores=quality_scores,
            threshold=threshold,
        )

        result: dict[str, object] = {
            "success": False,
            "queued": False,
            "average_score": 0.0,
            "below_threshold": False,
            "error": None,
        }

        # Calculate average quality score
        if not quality_scores:
            logger.warning(
                "no_quality_scores_provided",
                artifact_id=str(artifact_id),
            )
            result["error"] = "No quality scores provided"
            return result

        average_score = sum(quality_scores.values()) / len(quality_scores)
        result["average_score"] = average_score
        result["below_threshold"] = average_score < threshold

        logger.info(
            "quality_score_calculated",
            artifact_id=str(artifact_id),
            average_score=average_score,
            below_threshold=average_score < threshold,
        )

        # Queue if below threshold
        if average_score < threshold:
            try:
                await self._queue_artifact(
                    artifact_id=artifact_id,
                    trace_id=trace_id,
                    reason="low_quality",
                    metadata={
                        "quality_scores": quality_scores,
                        "average_score": average_score,
                        "threshold": threshold,
                        "queued_at": datetime.now(UTC).isoformat(),
                    },
                )
                result["queued"] = True

                logger.info(
                    "artifact_queued_for_low_quality",
                    artifact_id=str(artifact_id),
                    average_score=average_score,
                    threshold=threshold,
                )

            except Exception as e:
                logger.error(
                    "failed_to_queue_low_quality_artifact",
                    artifact_id=str(artifact_id),
                    error=str(e),
                    exc_info=True,
                )
                result["error"] = f"Failed to queue artifact: {e}"
                return result

        result["success"] = True
        return result

    async def _submit_langfuse_score(
        self,
        trace_id: str | None,
        score_name: str,
        score_value: float,
        comment: str | None = None,
    ) -> bool:
        """Submit a score to Langfuse for observability.

        Handles Langfuse submission with graceful degradation if unavailable.

        Args:
            trace_id: Langfuse trace ID (required for score submission)
            score_name: Name of the score metric
            score_value: Numeric score value
            comment: Optional comment explaining the score

        Returns:
            True if score was submitted successfully, False otherwise

        """
        if not trace_id:
            logger.debug(
                "langfuse_score_skipped_no_trace",
                score_name=score_name,
                message="No trace_id provided, skipping Langfuse submission",
            )
            return False

        service = get_langfuse_service()
        if not service:
            logger.debug(
                "langfuse_service_unavailable",
                score_name=score_name,
                message="Langfuse service not configured",
            )
            return False

        try:
            # LangfuseService.submit_score handles SDK calls and flushing
            service.submit_score(
                trace_id=trace_id,
                name=score_name,
                value=score_value,
                comment=comment,
            )

            logger.info(
                "langfuse_score_submitted",
                trace_id=trace_id,
                score_name=score_name,
                score_value=score_value,
            )

            return True

        except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
            logger.warning(
                "langfuse_score_submission_failed",
                trace_id=trace_id,
                score_name=score_name,
                error=str(e),
                exc_info=True,
            )
            return False

    async def _queue_artifact(
        self,
        artifact_id: uuid.UUID,
        trace_id: str | None,
        reason: QueueReason,
        metadata: dict[str, object] | None = None,
    ) -> None:
        """Add an artifact to the annotation queue.

        Queues artifact in both:
        1. Local database (annotation_queue table) - for API access
        2. Langfuse Annotation Queue (if configured) - for UI-based review

        Args:
            artifact_id: ID of the artifact to queue
            trace_id: Optional Langfuse trace ID
            reason: Reason for queuing (low_quality, negative_feedback, etc.)
            metadata: Additional context for reviewers

        Raises:
            Exception: If database operation fails

        """
        # Check if already queued with pending status
        existing = await self.session.execute(
            select(AnnotationQueue).where(
                AnnotationQueue.artifact_id == artifact_id,
                AnnotationQueue.status == "pending",
            )
        )
        existing_queue = existing.scalar_one_or_none()

        if existing_queue:
            logger.info(
                "artifact_already_queued",
                artifact_id=str(artifact_id),
                existing_queue_id=existing_queue.id,
            )
            return

        # Create new queue entry in local database
        queue_entry = AnnotationQueue(
            artifact_id=artifact_id,
            trace_id=trace_id,
            reason=reason,
            status="pending",
            metadata=metadata,
        )

        self.session.add(queue_entry)
        await self.session.commit()
        await self.session.refresh(queue_entry)

        logger.info(
            "artifact_queued_locally",
            queue_id=queue_entry.id,
            artifact_id=str(artifact_id),
            reason=reason,
        )

        # Also add to Langfuse Annotation Queue (optional, graceful degradation)
        await self._add_to_langfuse_queue(
            artifact_id=artifact_id,
            trace_id=trace_id,
            reason=reason,
            metadata=metadata,
        )

    async def _add_to_langfuse_queue(
        self,
        artifact_id: uuid.UUID,
        trace_id: str | None,
        reason: QueueReason,
        metadata: dict[str, object] | None = None,
    ) -> bool:
        """Add item to Langfuse Annotation Queue for UI-based review.

        This enables reviewers to use the Langfuse UI for annotation workflows.

        Note: The Langfuse Python SDK does not currently expose annotation queue
        methods. This would need to be implemented using the REST API directly
        via httpx if needed.

        Args:
            artifact_id: ID of the artifact to queue
            trace_id: Optional Langfuse trace ID
            reason: Reason for queuing
            metadata: Additional context for reviewers

        Returns:
            True if successfully added to Langfuse queue, False otherwise

        """
        # Validate all preconditions before attempting submission
        if not self._validate_langfuse_queue_config(artifact_id, trace_id):
            return False

        # Get validated configuration
        queue_id = settings.LANGFUSE_ANNOTATION_QUEUE_ID
        if not queue_id:
            logger.debug(
                "langfuse_queue_id_not_set",
                artifact_id=str(artifact_id),
                message="LANGFUSE_ANNOTATION_QUEUE_ID not set, skipping Langfuse queue",
            )
            return False

        # Get Langfuse service to check if enabled
        service = get_langfuse_service()
        if not service:
            logger.debug(
                "langfuse_service_unavailable",
                artifact_id=str(artifact_id),
                message="Langfuse service not configured",
            )
            return False

        # Type guard: Validation ensures trace_id is not None
        assert trace_id is not None, "trace_id validated in _validate_langfuse_queue_config"

        try:
            # Use LangfuseService which handles annotation queue REST API
            success = await service.add_to_annotation_queue(
                queue_id=queue_id,
                trace_id=trace_id,
                object_type="TRACE",
            )

            if success:
                logger.info(
                    "artifact_added_to_langfuse_queue",
                    artifact_id=str(artifact_id),
                    queue_id=queue_id,
                    trace_id=trace_id,
                    reason=reason,
                )

            return success

        except Exception as e:  # noqa: BLE001 - Graceful degradation
            # Graceful degradation - log warning but don't fail the operation
            logger.warning(
                "langfuse_queue_submission_failed",
                artifact_id=str(artifact_id),
                queue_id=queue_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return False

    def _validate_langfuse_queue_config(
        self,
        artifact_id: uuid.UUID,
        trace_id: str | None,
    ) -> bool:
        """Validate Langfuse queue configuration preconditions.

        Args:
            artifact_id: ID of the artifact (for logging)
            trace_id: Langfuse trace ID to validate

        Returns:
            True if validation passes (proceed with submission),
            False if validation fails (skip queue submission)

        """
        # Check if Langfuse queue is configured
        queue_id = settings.LANGFUSE_ANNOTATION_QUEUE_ID
        if not queue_id:
            logger.debug(
                "langfuse_queue_not_configured",
                message="LANGFUSE_ANNOTATION_QUEUE_ID not set, skipping Langfuse queue",
                artifact_id=str(artifact_id),
            )
            return False

        # Langfuse requires trace_id to link to TRACE objectType
        if not trace_id:
            logger.debug(
                "langfuse_queue_skipped_no_trace",
                message="No trace_id available, cannot add to Langfuse queue",
                artifact_id=str(artifact_id),
            )
            return False

        # All validations passed
        # (Client handles LANGFUSE_ENABLED and credential validation)
        return True


def get_annotation_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnnotationService:
    """Dependency injection function for AnnotationService."""
    return AnnotationService(session=db)
