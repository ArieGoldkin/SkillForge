"""Session management endpoints for tutor."""

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logging import get_logger
from app.db.repositories.tutor_repository import ITutorRepository, get_tutor_repository
from app.domains.tutor.schemas.api import (
    CreateSessionRequest,
    CreateSessionResponse,
    GetSessionResponse,
    UpdateSessionRequest,
)
from app.domains.tutor.services.state_service import build_tutor_state
from app.domains.tutor.workflows.graph_builder import tutor_workflow

router = APIRouter()
logger = get_logger(__name__)


def _format_messages(messages: list) -> list[dict[str, object]]:
    """Format messages for API response."""
    return [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "metadata": msg.message_metadata,
        }
        for msg in messages
    ]


@router.post("/tutor/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    request: CreateSessionRequest,
    repo: Annotated[ITutorRepository, Depends(get_tutor_repository)],
) -> CreateSessionResponse:
    """Create a new tutoring session.

    Creates a tutoring session, optionally linked to an analysis, and
    initializes the tutor workflow. Returns session ID and SSE endpoint.

    Args:
        request: CreateSessionRequest with optional analysis_id and user_level
        repo: Tutor repository dependency

    Returns:
        CreateSessionResponse with session_id, status, and SSE endpoint

    Raises:
        HTTPException: 404 if analysis_id provided but not found
        HTTPException: 500 if database operation fails

    """
    try:
        # Create session in database
        session = await repo.create_session(
            analysis_id=request.analysis_id,
            user_level=request.user_level,
        )

        # Initialize tutor workflow state
        # session.id is a UUID when accessed from instance, not Column[UUID]
        session_id: uuid.UUID = session.id  # type: ignore[assignment]
        initial_state = build_tutor_state(
            session_id,
            request.analysis_id,
            request.user_level,
        )

        # Start workflow asynchronously (syllabus generation)
        config = {"configurable": {"thread_id": str(session.id)}}
        task = asyncio.create_task(tutor_workflow.ainvoke(initial_state, config=config))
        # Store task reference to prevent garbage collection (RUF006)
        _ = task  # Task will complete naturally

        logger.info(
            "tutor_session_created",
            session_id=str(session.id),
            analysis_id=str(request.analysis_id) if request.analysis_id else None,
            user_level=request.user_level,
        )

        # SQLAlchemy Column types return actual values when accessed from instances
        return CreateSessionResponse(
            session_id=session.id,  # type: ignore[arg-type]
            status=str(session.status),  # type: ignore[arg-type]
            sse_endpoint=f"/api/v1/tutor/sessions/{session.id}/stream",  # type: ignore[arg-type]
        )

    except ValueError as e:
        logger.warning(
            "tutor_session_creation_failed",
            analysis_id=str(request.analysis_id) if request.analysis_id else None,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis not found: {e!s}",
        ) from e
    except Exception as e:
        logger.error(
            "tutor_session_creation_error",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tutoring session",
        ) from e


@router.get("/tutor/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    repo: Annotated[ITutorRepository, Depends(get_tutor_repository)],
) -> GetSessionResponse:
    """Get tutoring session with conversation history (for resume).

    Returns full session details including all messages for resuming
    a session.

    Args:
        session_id: Session UUID
        repo: Tutor repository dependency

    Returns:
        GetSessionResponse with session details and messages

    Raises:
        HTTPException: 404 if session not found

    """
    try:
        session, messages = await repo.get_session_with_messages(session_id)
        formatted_messages = _format_messages(messages)

        # SQLAlchemy Column types return actual values when accessed from instances
        return GetSessionResponse(
            session_id=session.id,  # type: ignore[arg-type]
            analysis_id=session.analysis_id,  # type: ignore[arg-type]
            status=str(session.status),  # type: ignore[arg-type]
            syllabus=session.syllabus,  # type: ignore[arg-type]
            current_section=int(session.current_section),  # type: ignore[arg-type]
            current_lesson=int(session.current_lesson),  # type: ignore[arg-type]
            current_phase=str(session.current_phase),  # type: ignore[arg-type]
            user_level=str(session.user_level),  # type: ignore[arg-type]
            messages=formatted_messages,
            started_at=session.started_at.isoformat(),
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch("/tutor/sessions/{session_id}")
async def update_session(
    session_id: uuid.UUID,
    request: UpdateSessionRequest,
    repo: Annotated[ITutorRepository, Depends(get_tutor_repository)],
) -> dict[str, object]:
    """Update tutoring session status (for exit).

    Marks session as completed or abandoned and sets completed_at timestamp.

    Args:
        session_id: Session UUID
        request: UpdateSessionRequest with new status
        repo: Tutor repository dependency

    Returns:
        Dictionary with updated session details

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 400 if status is invalid

    """
    if request.status not in ("active", "completed", "abandoned"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status: {request.status}. Must be 'active', 'completed', or 'abandoned'"
            ),
        )

    try:
        session = await repo.update_session_state(
            session_id,
            status=request.status,
        )

        logger.info(
            "tutor_session_updated",
            session_id=str(session_id),
            status=request.status,
        )

        return {
            "session_id": str(session.id),
            "status": session.status,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
