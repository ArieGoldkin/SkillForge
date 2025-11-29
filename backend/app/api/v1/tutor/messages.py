"""Message endpoints for tutor."""

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logging import get_logger
from app.db.repositories.tutor_repository import ITutorRepository, get_tutor_repository
from app.services.tutor.state_service import load_state_from_session
from app.services.tutor.workflow_service import continue_workflow_after_message
from app.workflows.tutor.schemas.api import SendMessageRequest

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
    updated_state = {
        **complete_state,
        "last_user_message": request.content,
        "conversation_history": complete_state["conversation_history"]
        + [
            {
                "role": "user",
                "content": request.content,
                "created_at": message.created_at.isoformat(),
                "metadata": message.message_metadata,
            }
        ],
    }

    # Continue workflow: invoke assess_readiness node directly
    asyncio.create_task(continue_workflow_after_message(session_id, updated_state, repo))

    logger.info(
        "tutor_message_sent",
        session_id=str(session_id),
        message_id=str(message.id),
    )

    return {
        "message_id": str(message.id),
        "status": "sent",
    }
