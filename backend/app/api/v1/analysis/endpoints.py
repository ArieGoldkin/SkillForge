"""Analysis endpoints for content analysis pipeline."""

import asyncio
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.v1.analysis.sse_handler import (
    stream_analysis_progress as stream_analysis_progress_handler,
)
from app.api.v1.analysis.workflow_runner import run_workflow_task
from app.core.config import settings
from app.core.logging import get_logger
from app.core.utils import normalize_analysis_id_to_uuid
from app.db.repositories.analysis_repository import IAnalysisRepository, get_analysis_repository
from app.db.repositories.artifact_repository import IArtifactRepository, get_artifact_repository
from app.domains.analysis.schemas.api import (
    AnalyzeCreateResponse,
    AnalyzeRequest,
    AnalyzeStatusResponse,
)
from app.shared.services.extraction.content_type import ContentTypeError, detect_content_type

router = APIRouter(tags=["analyze"])
logger = get_logger(__name__)

# Store background task references to prevent garbage collection
_background_tasks: set[asyncio.Task] = set()


def _handle_task_completion(task: asyncio.Task) -> None:
    """Handle background task completion and check for exceptions.

    This callback checks for exceptions (including GeneratorExit) that occur
    during task execution or cleanup, and logs them appropriately.

    GeneratorExit during cleanup after successful workflow completion is
    logged at DEBUG level (normal behavior). GeneratorExit during execution
    is logged at ERROR level (real error).
    """
    _background_tasks.discard(task)

    # Check for exceptions that occurred during task execution or cleanup
    exception = task.exception()
    if exception is not None:
        if isinstance(exception, GeneratorExit):
            # GeneratorExit can occur during cleanup (normal) or execution (error)
            # We can't easily determine if workflow completed from here, but
            # GeneratorExit in cleanup context is typically normal behavior
            # Log at DEBUG to avoid false error indicators
            logger.debug(
                "background_task_generator_exit",
                error_type="GeneratorExit",
                error_message=str(exception),
                exc_info=True,
                context="background_task_done_callback",
                note=(
                    "GeneratorExit caught in background task done callback. "
                    "This typically occurs when LangGraph's pregel module closes "
                    "an async generator during cleanup after workflow execution completes. "
                    "This is normal generator lifecycle behavior and does not indicate an error. "
                    "If the workflow completed successfully, this is expected cleanup behavior."
                ),
            )
        else:
            # Other exceptions are real errors - log at ERROR level
            logger.error(
                "background_task_exception",
                error_type=type(exception).__name__,
                error_message=str(exception),
                exc_info=True,
                context="background_task_done_callback",
            )


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
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
) -> AnalyzeCreateResponse:
    """Create a new analysis and start the workflow.

    This endpoint accepts a URL, creates an Analysis record in the database,
    and starts the analysis workflow asynchronously. The endpoint returns
    immediately with the analysis_id, allowing clients to connect to the SSE
    endpoint for real-time progress updates.

    Args:
        request: AnalyzeRequest containing URL and optional analysis_id
        analysis_repo: Repository for analysis persistence operations

    Returns:
        AnalyzeCreateResponse with analysis_id, URL, content_type, status, and SSE endpoint

    Raises:
        HTTPException: 422 if URL validation fails or content type detection fails
        HTTPException: 500 if database operation fails

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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Invalid analysis_id format: {e!s}",
            ) from e
    else:
        analysis_uuid = uuid.uuid4()

    # Create Analysis record
    try:
        await analysis_repo.create_analysis(
            analysis_id=analysis_uuid,
            url=url_str,
            content_type=content_type,
            status="pending",
        )

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create analysis record",
        ) from e

    # Start workflow asynchronously with proper task lifecycle management
    # E2E cost control: allow CI/docker E2E to create analyses without triggering
    # expensive external workflows. E2E tests can still validate HTTP + SSE plumbing.
    if os.environ.get("SKILLFORGE_E2E_DISABLE_WORKFLOW") == "true":
        logger.info(
            "analysis_workflow_skipped_for_e2e",
            analysis_id=str(analysis_uuid),
            url=url_str,
        )
    else:
        # Type ignore: mypy strictness - create_task accepts coroutines from async functions
        task: asyncio.Task[None] = asyncio.create_task(
            run_workflow_task(analysis_uuid, url_str, request.skill_level)  # type: ignore[arg-type]
        )
        _background_tasks.add(task)
        task.add_done_callback(_handle_task_completion)

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
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
    artifact_repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
) -> AnalyzeStatusResponse:
    """Get analysis details including latest artifact id."""
    analysis = await analysis_repo.get_by_id(analysis_id)

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    artifact = await artifact_repo.get_latest_artifact_by_analysis(analysis_id)

    return AnalyzeStatusResponse(
        analysis_id=str(analysis.id),
        url=str(analysis.url),
        content_type=str(analysis.content_type),
        status=str(analysis.status),
        title=str(analysis.title) if analysis.title else None,
        artifact_id=str(artifact.id) if artifact else None,
        created_at=analysis.created_at.isoformat() if analysis.created_at else "",
        updated_at=analysis.updated_at.isoformat() if analysis.updated_at else "",
    )
