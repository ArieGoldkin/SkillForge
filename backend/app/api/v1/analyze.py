"""Analysis endpoints for content analysis pipeline."""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.sse_handler import stream_analysis_progress as stream_analysis_progress_handler
from app.api.v1.workflow_runner import run_workflow_task
from app.core.config import settings
from app.core.logging import get_logger
from app.core.utils import normalize_analysis_id_to_uuid
from app.db.session import get_db
from app.models.analysis import Analysis
from app.schemas.analyze import AnalyzeCreateResponse, AnalyzeRequest
from app.services.extraction.content_type import ContentTypeError, detect_content_type

router = APIRouter(tags=["analyze"])
logger = get_logger(__name__)


@router.get("/analyze/{analysis_id}/stream")
async def stream_analysis_progress_endpoint(
    analysis_id: uuid.UUID,
    request: Request,
):
    """Stream real-time analysis progress via Server-Sent Events (SSE).

    See app.api.v1.sse_handler.stream_analysis_progress for full documentation.
    """
    return await stream_analysis_progress_handler(analysis_id, request)


@router.post("/analyze", status_code=status.HTTP_201_CREATED)
async def create_analysis(
    request: AnalyzeRequest,
    db: AsyncSession = Depends(get_db),
) -> AnalyzeCreateResponse:
    """Create a new analysis and start the workflow.

    This endpoint accepts a URL, creates an Analysis record in the database,
    and starts the analysis workflow asynchronously. The endpoint returns
    immediately with the analysis_id, allowing clients to connect to the SSE
    endpoint for real-time progress updates.

    Args:
        request: AnalyzeRequest containing URL and optional analysis_id
        db: Database session dependency

    Returns:
        AnalyzeCreateResponse with analysis_id, URL, content_type, status, and SSE endpoint

    Raises:
        HTTPException: 422 if URL validation fails or content type detection fails
        HTTPException: 500 if database operation fails

    Example Request:
        ```json
        {
            "url": "https://example.com/article",
            "analysis_id": "optional-custom-id"
        }
        ```

    Example Response:
        ```json
        {
            "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
            "url": "https://example.com/article",
            "content_type": "article",
            "status": "pending",
            "sse_endpoint": "/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/stream"
        }
        ```

    """
    url_str = str(request.url)

    # Detect content type
    try:
        content_type = detect_content_type(url_str)
    except ContentTypeError as e:
        logger.warning(
            "content_type_detection_failed",
            url=url_str,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid URL format: {e!s}",
        ) from e

    # Generate or normalize analysis_id
    if request.analysis_id:
        try:
            analysis_uuid = normalize_analysis_id_to_uuid(request.analysis_id)
        except Exception as e:
            logger.warning(
                "analysis_id_normalization_failed",
                analysis_id=request.analysis_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid analysis_id format: {e!s}",
            ) from e
    else:
        analysis_uuid = uuid.uuid4()

    # Create Analysis record
    try:
        analysis = Analysis(
            id=analysis_uuid,
            url=url_str,
            content_type=content_type,
            status="pending",
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)

        logger.info(
            "analysis_created",
            analysis_id=str(analysis_uuid),
            url=url_str,
            content_type=content_type,
        )
    except Exception as e:
        logger.error(
            "analysis_creation_failed",
            analysis_id=str(analysis_uuid),
            url=url_str,
            error=str(e),
            exc_info=True,
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create analysis record",
        ) from e

    # Start workflow asynchronously
    # Store task reference to prevent garbage collection (RUF006)
    _ = asyncio.create_task(run_workflow_task(analysis_uuid, url_str))

    # Build SSE endpoint URL
    sse_endpoint = f"{settings.API_V1_PREFIX}/analyze/{analysis_uuid}/stream"

    return AnalyzeCreateResponse(
        analysis_id=str(analysis_uuid),
        url=url_str,
        content_type=content_type,
        status="pending",
        sse_endpoint=sse_endpoint,
    )


@router.get("/analyze/{analysis_id}")
async def get_analysis(
    analysis_id: uuid.UUID,
) -> JSONResponse:
    """Get analysis details by ID.

    Args:
        analysis_id: UUID of the analysis

    Returns:
        JSONResponse with analysis details

    Note:
        This is a placeholder endpoint. Full implementation will require
        repository pattern integration (Task 1.3.1).

    """
    # TODO(@yonatan): Implement with repository pattern (Issue #41)
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "error": {
                "code": "NOT_IMPLEMENTED",
                "message": "Analysis retrieval not yet implemented",
                "analysis_id": str(analysis_id),
            }
        },
    )
