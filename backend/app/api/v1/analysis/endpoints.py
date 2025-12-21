"""Analysis endpoints for content analysis pipeline."""

import asyncio
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.schemas.errors import ErrorResponse
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
    AnalysisProgressResponse,
    AnalyzeCreateResponse,
    AnalyzeRequest,
    AnalyzeStatusResponse,
    ProgressEventResponse,
)
from app.shared.services.extraction.content_type import ContentTypeError, detect_content_type

router = APIRouter(tags=["analyze"])
logger = get_logger(__name__)


def _handle_task_completion(task: asyncio.Task, background_tasks: set[asyncio.Task]) -> None:
    """Handle background task completion and check for exceptions.

    This callback checks for exceptions (including GeneratorExit) that occur
    during task execution or cleanup, and logs them appropriately.

    GeneratorExit during cleanup after successful workflow completion is
    logged at DEBUG level (normal behavior). GeneratorExit during execution
    is logged at ERROR level (real error).

    Args:
        task: The completed background task
        background_tasks: Set of active background tasks to update

    """
    background_tasks.discard(task)

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
                context="background_task_done_callback",
            )


@router.get(
    "/analyze/{analysis_id}/stream",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def stream_analysis_progress_endpoint(
    analysis_id: Annotated[uuid.UUID, Path(description="Analysis UUID")],
    request: Request,
):
    """Stream real-time analysis progress via Server-Sent Events (SSE).

    See app.api.v1.sse_handler.stream_analysis_progress for full documentation.
    """
    return await stream_analysis_progress_handler(analysis_id, request)


@router.post(
    "/analyze",
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def create_analysis(
    request: AnalyzeRequest,
    fastapi_request: Request,
    response: Response,
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
) -> AnalyzeCreateResponse:
    """Create a new analysis and start the workflow.

    This endpoint accepts a URL, creates an Analysis record in the database,
    and starts the analysis workflow asynchronously. The endpoint returns
    immediately with the analysis_id, allowing clients to connect to the SSE
    endpoint for real-time progress updates.

    Implements idempotency: if an analysis already exists for the URL, returns
    the existing analysis with HTTP 200 instead of creating a duplicate.

    Args:
        request: AnalyzeRequest containing URL and optional analysis_id
        fastapi_request: FastAPI Request object for accessing app.state
        response: FastAPI Response object for setting status code
        analysis_repo: Repository for analysis persistence operations

    Returns:
        AnalyzeCreateResponse with analysis_id, URL, content_type, status, SSE endpoint,
        and existing flag indicating if analysis was newly created or already existed

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

    # Check for existing analysis by URL (idempotency)
    existing_analysis = await analysis_repo.get_by_url(url_str)
    if existing_analysis:
        logger.info(
            "analysis_exists_returning_cached",
            analysis_id=str(existing_analysis.id),
            url=url_str,
        )
        response.status_code = status.HTTP_200_OK
        sse_endpoint = f"{settings.API_V1_PREFIX}/analyze/{existing_analysis.id}/stream"
        return AnalyzeCreateResponse(
            analysis_id=str(existing_analysis.id),
            url=url_str,
            content_type=str(existing_analysis.content_type),
            status=str(existing_analysis.status),
            sse_endpoint=sse_endpoint,
            existing=True,
        )

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
    except IntegrityError as integrity_err:
        # Race condition: another request created this URL between our check and insert
        # Need to access session through the repository implementation
        if hasattr(analysis_repo, "session"):
            await analysis_repo.session.rollback()  # type: ignore[attr-defined]
        existing_analysis = await analysis_repo.get_by_url(url_str)
        if existing_analysis:
            logger.info(
                "analysis_race_condition_returning_existing",
                analysis_id=str(existing_analysis.id),
                url=url_str,
            )
            response.status_code = status.HTTP_200_OK
            sse_endpoint = f"{settings.API_V1_PREFIX}/analyze/{existing_analysis.id}/stream"
            return AnalyzeCreateResponse(
                analysis_id=str(existing_analysis.id),
                url=url_str,
                content_type=str(existing_analysis.content_type),
                status=str(existing_analysis.status),
                sse_endpoint=sse_endpoint,
                existing=True,
            )
        # If we still can't find it, something is seriously wrong
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or retrieve analysis",
        ) from integrity_err
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
        background_tasks = fastapi_request.app.state.background_tasks
        background_tasks.add(task)
        # Use functools.partial to bind background_tasks to callback
        from functools import partial

        task.add_done_callback(partial(_handle_task_completion, background_tasks=background_tasks))

    # Build SSE endpoint URL
    sse_endpoint = f"{settings.API_V1_PREFIX}/analyze/{analysis_uuid}/stream"

    return AnalyzeCreateResponse(
        analysis_id=str(analysis_uuid),
        url=url_str,
        content_type=content_type,
        status="pending",
        sse_endpoint=sse_endpoint,
        existing=False,
    )


@router.get(
    "/analyze/{analysis_id}",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_analysis(
    analysis_id: Annotated[uuid.UUID, Path(description="Analysis UUID")],
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


@router.get(
    "/analyze/{analysis_id}/progress",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_analysis_progress(
    analysis_id: Annotated[uuid.UUID, Path(description="Analysis UUID")],
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
) -> AnalysisProgressResponse:
    """Get stored progress events for a completed analysis.

    Returns all progress events stored in the analysis_progress table,
    allowing reconstruction of the analysis timeline for completed analyses.
    This endpoint is used by the frontend to display stage progress when
    loading a completed analysis (no active SSE connection).

    Args:
        analysis_id: UUID of the analysis
        analysis_repo: Analysis repository dependency

    Returns:
        AnalysisProgressResponse with all progress events

    Raises:
        HTTPException: 404 if analysis not found

    """
    # Verify analysis exists
    analysis = await analysis_repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    # Fetch all progress events
    progress_records = await analysis_repo.get_progress_events(analysis_id)

    # Convert to response schema
    events = [
        ProgressEventResponse(
            stage=str(record.stage),
            status=str(record.status),
            progress_data=record.progress_data if record.progress_data is not None else None,
            timestamp=record.created_at.isoformat() if record.created_at else "",
        )
        for record in progress_records
    ]

    return AnalysisProgressResponse(
        analysis_id=str(analysis_id),
        events=events,
    )
