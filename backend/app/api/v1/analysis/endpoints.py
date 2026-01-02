"""Analysis endpoints for content analysis pipeline."""

import asyncio
import os
import uuid
from typing import Annotated, Any, ClassVar, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Request, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.schemas.errors import ErrorResponse
from app.api.v1.analysis.sse_handler import (
    stream_analysis_progress as stream_analysis_progress_handler,
)
from app.core.branded_ids import AnalysisID
from app.core.config import settings
from app.core.logging import get_logger
from app.core.utils import normalize_analysis_id_to_uuid
from app.db.repositories.analysis_repository import IAnalysisRepository, get_analysis_repository
from app.db.repositories.artifact_repository import IArtifactRepository, get_artifact_repository
from app.domains.analysis.schemas.api import (
    AnalysisProgressResponse,
    AnalysisRerunResponse,
    AnalysisRetryResponse,
    AnalysisStatus,
    AnalyzeCreateResponse,
    AnalyzeRequest,
    AnalyzeStatusResponse,
    ProgressEventResponse,
)
from app.domains.analysis.services.workflow import WorkflowOrchestrator
from app.domains.analysis.workflows.analysis import create_analysis_workflow
from app.shared.services.extraction.content_type import ContentTypeError, detect_content_type

router = APIRouter(tags=["analyze"])
logger = get_logger(__name__)


class WorkflowCache:
    """Cache for workflow instances keyed by checkpointer type.

    Maintains separate cached workflows for different checkpointer types
    (e.g., AsyncPostgresSaver for production, MemorySaver for tests).
    Issue #602: Support checkpointer injection from FastAPI app.state.
    """

    _instances: ClassVar[dict[str, Any]] = {}

    @classmethod
    def get_or_create(cls, checkpointer: Any = None) -> Any:
        """Get cached workflow instance or create new one.

        Args:
            checkpointer: Optional checkpointer instance (AsyncPostgresSaver, etc.)
                         If None, falls back to default in graph_builder.

        Returns:
            Compiled workflow graph

        """
        # Key by checkpointer type to maintain separate caches
        key = type(checkpointer).__name__ if checkpointer else "default"
        if key not in cls._instances:
            cls._instances[key] = create_analysis_workflow(checkpointer=checkpointer)
        return cls._instances[key]


def get_orchestrator(request: Request) -> WorkflowOrchestrator:
    """Get WorkflowOrchestrator instance with workflow and checkpointer injected.

    For FastAPI dependency injection. Creates workflow on first call.
    Issue #602: Injects checkpointer from app.state for AsyncPostgresSaver.

    Args:
        request: FastAPI Request to access app.state.checkpointer

    Returns:
        WorkflowOrchestrator with checkpointer-enabled workflow

    """
    # Get checkpointer from app.state (initialized in main.py lifespan)
    checkpointer = getattr(request.app.state, "checkpointer", None)
    workflow = WorkflowCache.get_or_create(checkpointer=checkpointer)
    return WorkflowOrchestrator(workflow=workflow)


def _handle_task_completion(
    task: asyncio.Task,
    background_tasks: set[asyncio.Task],
    analysis_id: AnalysisID | None = None,
) -> None:
    """Handle background task completion and check for exceptions.

    This callback checks for exceptions (including GeneratorExit) that occur
    during task execution or cleanup, and logs them appropriately.

    GeneratorExit during cleanup after successful workflow completion is
    logged at DEBUG level (normal behavior). GeneratorExit during execution
    is logged at ERROR level (real error).

    Args:
        task: The completed background task
        background_tasks: Set of active background tasks to update
        analysis_id: Optional analysis ID to update status on failure

    """
    background_tasks.discard(task)

    # Check for exceptions that occurred during task execution or cleanup
    from app.core.exceptions import is_cleanup_generator_exit

    exception = task.exception()
    if exception is not None:
        # Use unified GeneratorExit detection
        # Note: We can't determine workflow_completed from here, so we assume cleanup
        # (GeneratorExit in task callback is typically cleanup after successful completion)
        if is_cleanup_generator_exit(exception, workflow_completed=True):
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
            # Update analysis status to failed if analysis_id provided
            if analysis_id:
                import asyncio

                from app.db.session import get_session_factory

                async def mark_failed_on_exception() -> None:
                    session_factory = get_session_factory()
                    async with session_factory() as session:
                        repo = get_analysis_repository(session)
                        # Only update if status is still pending (workflow never started properly)
                        analysis = await repo.get_by_id(analysis_id, validate=False)
                        if analysis and analysis.status == "pending":
                            await repo.mark_failed(
                                analysis_id=analysis_id,
                                error_code="WORKFLOW_EXECUTION_FAILED",
                                error_message=f"Workflow execution failed: {exception!s}",
                                failed_at_stage="workflow_execution",
                            )
                            await session.commit()

                # Schedule the status update as a background task
                _task = asyncio.create_task(mark_failed_on_exception())
                del _task  # Fire-and-forget, reference not needed


@router.get(
    "/analyze/{analysis_id}/stream",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def stream_analysis_progress_endpoint(
    analysis_id: Annotated[AnalysisID, Path(description="Analysis UUID")],
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
async def create_analysis(  # noqa: PLR0915 - Complex workflow orchestration
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

    # Generate or normalize analysis_id (if provided by client)
    # With Annotated types, UUID flows through directly - no conversion needed
    provided_analysis_id: AnalysisID | None = None
    if request.analysis_id:
        try:
            provided_analysis_id = normalize_analysis_id_to_uuid(request.analysis_id)
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

    # Create Analysis record (DB generates UUID v7 via server_default if not provided)
    try:
        created_analysis = await analysis_repo.create_analysis(
            analysis_id=provided_analysis_id,
            url=url_str,
            content_type=content_type,
            status="pending",
        )
        # cast() is the standard pattern for SQLAlchemy 1.x Column -> value conversion
        # At runtime, created_analysis.id is a UUID, not a Column descriptor
        analysis_uuid = cast("AnalysisID", created_analysis.id)

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
            analysis_id=str(provided_analysis_id) if provided_analysis_id else "auto-generated",
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
        try:
            orchestrator = get_orchestrator(fastapi_request)

            # Wrap workflow execution with timeout to prevent stuck analyses
            async def run_with_timeout() -> None:
                from app.core.timeout_config import WORKFLOW_TIMEOUT

                try:
                    async with asyncio.timeout(WORKFLOW_TIMEOUT):
                        await orchestrator.run(
                            analysis_uuid, url_str, request.skill_level, request.analysis_mode
                        )
                except TimeoutError:
                    # Workflow exceeded timeout - mark as failed
                    logger.exception(
                        "workflow_timeout_exceeded",
                        analysis_id=str(analysis_uuid),
                        timeout_seconds=WORKFLOW_TIMEOUT,
                    )
                    from app.db.session import get_session_factory

                    session_factory = get_session_factory()
                    async with session_factory() as session:
                        repo = get_analysis_repository(session)
                        analysis = await repo.get_by_id(analysis_uuid, validate=False)
                        if analysis and analysis.status in ("pending", "analyzing", "running"):
                            await repo.mark_failed(
                                analysis_id=analysis_uuid,
                                error_code="WORKFLOW_TIMEOUT",
                                error_message=f"Workflow exceeded timeout of {WORKFLOW_TIMEOUT}s",
                                failed_at_stage="workflow_execution",
                            )
                            await session.commit()
                    raise  # Re-raise to trigger task completion handler

            task: asyncio.Task[None] = asyncio.create_task(run_with_timeout())
            background_tasks = fastapi_request.app.state.background_tasks
            background_tasks.add(task)
            # Use functools.partial to bind background_tasks to callback
            from functools import partial

            task.add_done_callback(
                partial(
                    _handle_task_completion,
                    background_tasks=background_tasks,
                    analysis_id=analysis_uuid,
                )
            )
        except Exception as startup_exception:
            # Handle immediate workflow startup failures (Fix for stuck "pending" status)
            logger.error(
                "workflow_startup_failed",
                analysis_id=str(analysis_uuid),
                error=str(startup_exception),
                exc_info=True,
            )
            # Update analysis status to failed
            from app.db.session import get_session_factory

            error_message = f"Failed to start workflow: {startup_exception!s}"

            async def mark_failed() -> None:
                session_factory = get_session_factory()
                async with session_factory() as session:
                    repo = get_analysis_repository(session)
                    await repo.mark_failed(
                        analysis_id=analysis_uuid,
                        error_code="WORKFLOW_STARTUP_FAILED",
                        error_message=error_message,
                        failed_at_stage="workflow_startup",
                    )
                    await session.commit()

            # Schedule the status update as a background task
            _task = asyncio.create_task(mark_failed())
            del _task  # Fire-and-forget, reference not needed

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
    analysis_id: Annotated[AnalysisID, Path(description="Analysis UUID")],
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
        # Error tracking fields (Issue #441)
        error_code=str(analysis.error_code) if analysis.error_code else None,
        error_message=str(analysis.error_message) if analysis.error_message else None,
        failed_at_stage=str(analysis.failed_at_stage) if analysis.failed_at_stage else None,
    )


@router.get(
    "/analyses/error-summary",
    responses={
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_error_summary(
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
) -> dict:
    """Get summary of analysis errors for debugging and monitoring.

    Returns aggregated error statistics showing:
    - Error codes with counts
    - Stages where failures occurred
    - Most common error patterns

    Useful for:
    - System health monitoring
    - Identifying systemic issues
    - Debugging recurring failures

    Returns:
        Dictionary with error_summary list containing error_code, failed_at_stage, count.

    """
    from sqlalchemy import func, select

    from app.db.models.analysis import Analysis

    # Get database session from repository
    # Type ignore: repository implementation has session attribute
    db = analysis_repo.session  # type: ignore[attr-defined]

    result = await db.execute(
        select(
            Analysis.error_code,
            Analysis.failed_at_stage,
            func.count(Analysis.id).label("count"),
        )
        .where(Analysis.error_code.isnot(None))
        .group_by(Analysis.error_code, Analysis.failed_at_stage)
        .order_by(func.count(Analysis.id).desc())
    )

    error_summary = [
        {
            "error_code": row.error_code,
            "failed_at_stage": row.failed_at_stage,
            "count": row.count,
        }
        for row in result.fetchall()
    ]

    return {"error_summary": error_summary}


@router.get(
    "/analyze/{analysis_id}/progress",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_analysis_progress(
    analysis_id: Annotated[AnalysisID, Path(description="Analysis UUID")],
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
            progress_data=(
                dict(record.progress_data) if isinstance(record.progress_data, dict) else None
            ),
            timestamp=record.created_at.isoformat() if record.created_at else "",
        )
        for record in progress_records
    ]

    return AnalysisProgressResponse(
        analysis_id=str(analysis_id),
        events=events,
    )


@router.post(
    "/analyze/{analysis_id}/rerun",
    responses={
        400: {"model": ErrorResponse, "description": "Analysis not rerunnable"},
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def rerun_analysis(
    analysis_id: Annotated[AnalysisID, Path(description="Analysis UUID")],
    fastapi_request: Request,
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
    artifact_repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
) -> AnalysisRerunResponse:
    """Rerun a completed analysis with updated agents.

    This endpoint allows re-analyzing a completed analysis using updated agents
    while preserving the original extraction (raw_content, embeddings). The workflow
    starts from the 'analyzing' stage, skipping extraction.

    The previous artifact is archived (previous_artifact_id) and a new artifact
    will be generated. This enables comparison between different agent versions.

    Args:
        analysis_id: UUID of the completed analysis to rerun
        fastapi_request: FastAPI Request object for accessing app.state
        analysis_repo: Analysis repository dependency
        artifact_repo: Artifact repository dependency

    Returns:
        AnalysisRerunResponse with rerun details and SSE endpoint

    Raises:
        HTTPException: 404 if analysis not found
        HTTPException: 400 if analysis status is not 'complete'
        HTTPException: 500 if database operation fails

    """
    # Verify analysis exists
    analysis = await analysis_repo.get_by_id(analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    # Check if analysis can be rerun (only 'complete' status is rerunnable)
    # Type guard: analysis.status is a str in the database model
    if not AnalysisStatus.is_rerunnable(str(analysis.status)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Analysis must be in 'complete' status to rerun. Current status: {analysis.status}"
            ),
        )

    # Get current artifact to archive
    current_artifact = await artifact_repo.get_latest_artifact_by_analysis(analysis_id)
    # Type guard: current_artifact.id is a UUID in the database model
    current_artifact_id: uuid.UUID | None = (
        uuid.UUID(str(current_artifact.id)) if current_artifact else None
    )

    # Prepare analysis for rerun
    try:
        new_rerun_count, archived_artifact_id = await analysis_repo.prepare_for_rerun(
            analysis_id, current_artifact_id
        )

        logger.info(
            "analysis_rerun_initiated",
            analysis_id=str(analysis_id),
            rerun_count=new_rerun_count,
            archived_artifact_id=str(archived_artifact_id) if archived_artifact_id else None,
        )
    except Exception as e:
        logger.error(
            "analysis_rerun_preparation_failed",
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare analysis for rerun",
        ) from e

    # Start workflow asynchronously from 'analyzing' stage
    # E2E cost control: allow CI/docker E2E to create reruns without triggering
    # expensive external workflows. E2E tests can still validate HTTP + SSE plumbing.
    if os.environ.get("SKILLFORGE_E2E_DISABLE_WORKFLOW") == "true":
        logger.info(
            "analysis_workflow_skipped_for_e2e",
            analysis_id=str(analysis_id),
            url=str(analysis.url),
            rerun=True,
        )
    else:
        # Type ignore: mypy strictness - create_task accepts coroutines from async functions
        orchestrator = get_orchestrator(fastapi_request)

        # Wrap workflow execution with timeout to prevent stuck analyses
        async def run_with_timeout() -> None:
            from app.core.timeout_config import WORKFLOW_TIMEOUT

            try:
                async with asyncio.timeout(WORKFLOW_TIMEOUT):
                    await orchestrator.run(
                        analysis_id,
                        str(analysis.url),
                        "intermediate",  # Default skill level for rerun
                        "standard",  # Default analysis mode for rerun
                        start_from_stage="analyzing",  # Skip extraction, reuse existing content
                    )
            except TimeoutError:
                logger.exception(
                    "workflow_timeout_exceeded",
                    analysis_id=str(analysis_id),
                    timeout_seconds=WORKFLOW_TIMEOUT,
                )
                from app.db.session import get_session_factory

                session_factory = get_session_factory()
                async with session_factory() as session:
                    repo = get_analysis_repository(session)
                    analysis_check = await repo.get_by_id(analysis_id, validate=False)
                    if analysis_check and analysis_check.status in (
                        "pending",
                        "analyzing",
                        "running",
                    ):
                        await repo.mark_failed(
                            analysis_id=analysis_id,
                            error_code="WORKFLOW_TIMEOUT",
                            error_message=f"Workflow exceeded timeout of {WORKFLOW_TIMEOUT}s",
                            failed_at_stage="workflow_execution",
                        )
                        await session.commit()
                raise

        task: asyncio.Task[None] = asyncio.create_task(run_with_timeout())
        background_tasks = fastapi_request.app.state.background_tasks
        background_tasks.add(task)
        # Use functools.partial to bind background_tasks to callback
        from functools import partial

        task.add_done_callback(
            partial(
                _handle_task_completion, background_tasks=background_tasks, analysis_id=analysis_id
            )
        )

    # Build SSE endpoint URL
    sse_endpoint = f"{settings.API_V1_PREFIX}/analyze/{analysis_id}/stream"

    return AnalysisRerunResponse(
        analysis_id=str(analysis_id),
        status="analyzing",
        rerun_count=new_rerun_count,
        previous_artifact_id=str(archived_artifact_id) if archived_artifact_id else None,
        sse_endpoint=sse_endpoint,
    )


@router.post(
    "/analyze/{analysis_id}/retry",
    responses={
        404: {"model": ErrorResponse, "description": "Analysis not found"},
        400: {
            "model": ErrorResponse,
            "description": "Analysis not retryable or retry limit reached",
        },
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def retry_analysis(  # noqa: PLR0915 - Complex retry orchestration
    analysis_id: Annotated[AnalysisID, Path(description="Analysis UUID")],
    fastapi_request: Request,
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
) -> AnalysisRetryResponse:
    """Retry a failed analysis.

    Retries a failed analysis by clearing error state, incrementing retry count,
    and restarting the workflow from an appropriate stage based on where it failed.

    Restart stage logic:
    - extraction_failed → restart from "pending" (full restart including extraction)
    - analysis_failed, quality_gate_failed → restart from "analyzing" (reuse extraction)
    - artifact_failed → restart from "generating_artifact" (reuse analysis)

    Args:
        analysis_id: UUID of the analysis to retry
        fastapi_request: FastAPI Request object for accessing app.state
        analysis_repo: Repository for analysis persistence operations

    Returns:
        AnalysisRetryResponse with analysis_id, status, retry_count, and sse_endpoint

    Raises:
        HTTPException: 404 if analysis not found
        HTTPException: 400 if analysis not retryable or retry limit exceeded
        HTTPException: 500 if retry preparation fails

    """
    from app.core.constants import MAX_RETRY_ATTEMPTS

    # Get analysis by ID
    analysis = await analysis_repo.get_by_id(analysis_id)

    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    # Check if status is retryable (must be a failed state)
    current_status = str(analysis.status)
    if not AnalysisStatus.is_retryable(current_status):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Analysis status '{current_status}' is not retryable. "
                f"Only failed analyses can be retried."
            ),
        )

    # Check retry limit (must be < MAX_RETRY_ATTEMPTS)
    if analysis.retry_count >= MAX_RETRY_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Retry limit exceeded ({analysis.retry_count}/{MAX_RETRY_ATTEMPTS} attempts)",
        )

    # Determine restart stage based on failed_at_stage
    # extraction_failed → restart from "pending" (full restart)
    # supervisor, analysis, any agent → restart from "analyzing" (reuse extraction)
    # artifact_generation, quality_gate → restart from "generating_artifact"
    failed_stage = analysis.failed_at_stage or ""

    if failed_stage == "extraction" or analysis.status == "extraction_failed":
        restart_stage = "pending"  # Full restart including extraction
    elif failed_stage in {"artifact_generation", "quality_gate"} or analysis.status in {
        "artifact_failed",
        "quality_gate_failed",
    }:
        restart_stage = "generating_artifact"  # Reuse extraction and analysis
    else:
        # Default: restart from analyzing (covers supervisor, analysis, agent failures)
        restart_stage = "analyzing"

    # Prepare for retry (clear error state, increment retry_count)
    try:
        await analysis_repo.prepare_for_retry(analysis_id, restart_stage)
    except Exception as e:
        logger.error(
            "retry_preparation_failed",
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to prepare analysis for retry",
        ) from e

    # Queue background workflow (skip if E2E test mode)
    if os.environ.get("SKILLFORGE_E2E_DISABLE_WORKFLOW") == "true":
        logger.info(
            "retry_workflow_skipped_for_e2e",
            analysis_id=str(analysis_id),
        )
    else:
        # Start workflow asynchronously
        orchestrator = get_orchestrator(fastapi_request)
        # Note: WorkflowOrchestrator.run() doesn't currently support start_from_stage parameter
        # For now, we'll restart from pending and let the workflow handle status transitions
        # TODO(#544): Add start_from_stage parameter to WorkflowOrchestrator.run() for efficiency

        # Wrap workflow execution with timeout to prevent stuck analyses
        async def run_with_timeout() -> None:
            from app.core.timeout_config import WORKFLOW_TIMEOUT

            try:
                async with asyncio.timeout(WORKFLOW_TIMEOUT):
                    await orchestrator.run(
                        analysis_id,
                        str(analysis.url),
                        "intermediate",  # Default skill level
                        "standard",  # Default analysis mode
                    )
            except TimeoutError:
                logger.exception(
                    "workflow_timeout_exceeded",
                    analysis_id=str(analysis_id),
                    timeout_seconds=WORKFLOW_TIMEOUT,
                )
                from app.db.session import get_session_factory

                session_factory = get_session_factory()
                async with session_factory() as session:
                    repo = get_analysis_repository(session)
                    analysis_check = await repo.get_by_id(analysis_id, validate=False)
                    if analysis_check and analysis_check.status in (
                        "pending",
                        "analyzing",
                        "running",
                    ):
                        await repo.mark_failed(
                            analysis_id=analysis_id,
                            error_code="WORKFLOW_TIMEOUT",
                            error_message=f"Workflow exceeded timeout of {WORKFLOW_TIMEOUT}s",
                            failed_at_stage="workflow_execution",
                        )
                        await session.commit()
                raise

        task: asyncio.Task[None] = asyncio.create_task(run_with_timeout())
        background_tasks = fastapi_request.app.state.background_tasks
        background_tasks.add(task)
        from functools import partial

        task.add_done_callback(
            partial(
                _handle_task_completion, background_tasks=background_tasks, analysis_id=analysis_id
            )
        )

    # Build SSE endpoint URL
    sse_endpoint = f"{settings.API_V1_PREFIX}/analyze/{analysis_id}/stream"

    # Re-fetch analysis to get updated retry_count
    updated_analysis = await analysis_repo.get_by_id(analysis_id)
    if not updated_analysis:
        # Should not happen, but handle gracefully
        logger.error("retry_analysis_disappeared", analysis_id=str(analysis_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis disappeared after retry preparation",
        )

    logger.info(
        "analysis_retry_queued",
        analysis_id=str(analysis_id),
        restart_stage=restart_stage,
        retry_count=updated_analysis.retry_count,
    )

    retry_count: int = updated_analysis.retry_count or 0  # type: ignore[assignment]
    return AnalysisRetryResponse(
        analysis_id=str(analysis_id),
        status=restart_stage,
        retry_count=retry_count,
        sse_endpoint=sse_endpoint,
    )
