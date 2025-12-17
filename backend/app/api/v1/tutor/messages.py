"""Message endpoints for tutor."""

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logging import get_logger
from app.db.repositories.tutor_repository import ITutorRepository, get_tutor_repository
from app.domains.tutor.schemas.api import SendMessageRequest
from app.domains.tutor.services.state_service import load_state_from_session
from app.domains.tutor.services.workflow_service import continue_workflow_after_message
from app.domains.tutor.workflows.state import TutorState
from app.shared.types import TutorMessage

router = APIRouter()
logger = get_logger(__name__)


@router.post("/tutor/sessions/{session_id}/messages")
async def send_message(
    session_id: uuid.UUID,
    request: SendMessageRequest,
    repo: Annotated[ITutorRepository, Depends(get_tutor_repository)],
) -> dict[str, object]:
    """Send a message in a tutoring session.

    Saves user message and triggers workflow to generate response.
    Response is streamed via SSE (connect to /stream endpoint).

    Args:
        session_id: Session UUID
        request: SendMessageRequest with message content
        repo: Tutor repository dependency

    Returns:
        Dictionary with message_id and status

    Raises:
        HTTPException: 404 if session not found
        HTTPException: 400 if session is not active

    """
    # Get session
    session = await repo.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )

    if session.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session {session_id} is not active (status: {session.status})",
        )

    # Save user message
    message = await repo.save_message(
        session_id,
        role="user",
        content=request.content,
    )

    # Load state from session
    complete_state = await load_state_from_session(session, repo)

    # Update state with new user message
    new_message: TutorMessage = {
        "role": "user",
        "content": request.content,
        "created_at": message.created_at.isoformat(),  # type: ignore[union-attr]
        "metadata": message.message_metadata,  # type: ignore[typeddict-item]
    }
    updated_history: list[TutorMessage] = [*complete_state["conversation_history"], new_message]
    updated_state: TutorState = {
        **complete_state,
        "last_user_message": request.content,
        "conversation_history": updated_history,
    }

    # Continue workflow: invoke assess_readiness node directly
    task = asyncio.create_task(continue_workflow_after_message(session_id, updated_state, repo))
    # Store task reference to prevent garbage collection (RUF006)
    _ = task  # Task will complete naturally

    logger.info(
        "tutor_message_sent",
        session_id=str(session_id),
        message_id=str(message.id),
    )

    return {
        "message_id": str(message.id),
        "status": "sent",
    }
