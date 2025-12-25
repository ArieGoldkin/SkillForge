"""Annotation API endpoints for user feedback and review queue.

This module provides endpoints for:
- Submitting user feedback (thumbs up/down) on artifacts
- Flagging artifacts for manual review
- Retrieving the annotation review queue
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.schemas.errors import ErrorResponse
from app.core.annotation_service import AnnotationService, get_annotation_service
from app.core.logging import get_logger
from app.db.repositories.annotation_repository import (
    AnnotationRepository,
    get_annotation_repository,
)
from app.db.repositories.artifact_repository import (
    ArtifactRepository,
    get_artifact_repository,
)
from app.schemas.annotations import (
    AnnotationQueueItemResponse,
    AnnotationQueueListResponse,
    FlagForReviewRequest,
    FlagForReviewResponse,
    SubmitFeedbackRequest,
    SubmitFeedbackResponse,
)

router = APIRouter(prefix="/annotations", tags=["annotations"])
logger = get_logger(__name__)


@router.post(
    "/feedback",
    responses={
        500: {"model": ErrorResponse, "description": "Feedback submission failed"},
    },
)
async def submit_feedback(
    request: SubmitFeedbackRequest,
    service: Annotated[AnnotationService, Depends(get_annotation_service)],
    artifact_repository: Annotated[ArtifactRepository, Depends(get_artifact_repository)],
) -> SubmitFeedbackResponse:
    """Submit user feedback (thumbs up/down) on an artifact.

    This endpoint:
    - Submits feedback to Langfuse as a score (0 or 1)
    - Optionally queues negative feedback with comments for review
    - Returns submission status

    Args:
        request: Feedback submission data including artifact_id, feedback type, and optional comment
        service: Annotation service dependency
        artifact_repository: Repository for looking up artifact trace_id

    Returns:
        Submission status and confirmation

    Raises:
        HTTPException: 500 if submission fails

    """
    try:
        # Look up artifact's trace_id if not provided in request
        trace_id = request.trace_id
        if not trace_id:
            artifact = await artifact_repository.get_artifact_by_id(request.artifact_id)
            if artifact:
                # Cast to str | None to satisfy type checker (SQLAlchemy Column attribute)
                trace_id = str(artifact.trace_id) if artifact.trace_id else None

        result = await service.submit_feedback(
            artifact_id=request.artifact_id,
            trace_id=trace_id,
            feedback=request.feedback.value,
            comment=request.comment,
        )

        return SubmitFeedbackResponse(**result)

    except Exception as e:
        logger.exception(
            "feedback_submission_failed",
            artifact_id=str(request.artifact_id),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback",
        ) from e


@router.post(
    "/flag",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Artifact already queued"},
        500: {"model": ErrorResponse, "description": "Failed to queue artifact"},
    },
)
async def flag_for_review(
    request: FlagForReviewRequest,
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
) -> FlagForReviewResponse:
    """Flag an artifact for manual review.

    This endpoint allows users to explicitly flag artifacts that need
    human review, regardless of quality scores.

    Args:
        request: Flag request with artifact ID and reason
        repository: Annotation repository dependency

    Returns:
        Queue entry ID and confirmation message

    Raises:
        HTTPException: 409 if artifact already queued
        HTTPException: 500 if queuing fails

    """
    try:
        # Check if already queued
        already_queued = await repository.check_if_queued(artifact_id=request.artifact_id)

        if already_queued:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Artifact {request.artifact_id} is already queued for review",
            )

        queue_entry = await repository.queue_for_review(
            artifact_id=request.artifact_id,
            reason="flagged_by_user",
            metadata={"user_reason": request.reason},
        )

        logger.info(
            "artifact_flagged_for_review",
            artifact_id=str(request.artifact_id),
            queue_id=queue_entry.id,
        )

        return FlagForReviewResponse(
            queue_id=queue_entry.id,
            message="Artifact flagged for review",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "flag_for_review_failed",
            artifact_id=str(request.artifact_id),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flag artifact for review",
        ) from e


@router.get(
    "/queue",
    responses={
        500: {"model": ErrorResponse, "description": "Failed to retrieve queue"},
    },
)
async def get_annotation_queue(
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Max items to return", examples=[20]),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Items to skip", examples=[0]),
    ] = 0,
) -> AnnotationQueueListResponse:
    """Get pending annotation queue entries.

    Returns a paginated list of artifacts awaiting human review.

    Args:
        repository: Annotation repository dependency
        limit: Maximum number of entries to return (1-100, default 20)
        offset: Number of entries to skip (default 0)

    Returns:
        Paginated list of queue entries with metadata

    Raises:
        HTTPException: 500 if query fails

    """
    try:
        items = await repository.get_pending_annotations(
            limit=limit,
            offset=offset,
        )

        # Get total count for pagination
        total = await repository.get_queue_count()

        # Convert to response models
        response_items = [AnnotationQueueItemResponse.model_validate(item) for item in items]

        return AnnotationQueueListResponse(
            items=response_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.exception("get_annotation_queue_failed", error_type=type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve annotation queue",
        ) from e


@router.patch(
    "/queue/{queue_id}/reviewed",
    responses={
        404: {"model": ErrorResponse, "description": "Queue entry not found"},
        500: {"model": ErrorResponse, "description": "Failed to mark as reviewed"},
    },
)
async def mark_as_reviewed(
    queue_id: Annotated[int, Path(description="Queue entry ID", ge=1)],
    repository: Annotated[AnnotationRepository, Depends(get_annotation_repository)],
) -> AnnotationQueueItemResponse:
    """Mark an annotation queue entry as reviewed.

    Args:
        queue_id: ID of the queue entry to mark as reviewed
        repository: Annotation repository dependency

    Returns:
        Updated queue entry

    Raises:
        HTTPException: 404 if queue entry not found
        HTTPException: 500 if update fails

    """
    try:
        queue_entry = await repository.mark_as_reviewed(queue_id=queue_id)

        if not queue_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Queue entry {queue_id} not found",
            )

        logger.info(
            "annotation_marked_reviewed",
            queue_id=queue_id,
            artifact_id=str(queue_entry.artifact_id),
        )

        return AnnotationQueueItemResponse.model_validate(queue_entry)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "mark_as_reviewed_failed",
            queue_id=queue_id,
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark as reviewed",
        ) from e
