"""State management service for tutor workflow.

Extracts state building logic from API endpoints.
"""

import uuid

from app.core.logging import get_logger
from app.db.repositories.tutor_repository import ITutorRepository
from app.models.tutoring import TutoringSession
from app.workflows.tutor.graph_builder import tutor_workflow
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)


async def load_state_from_session(
    session: TutoringSession,
    repo: ITutorRepository,
) -> TutorState:
    """Load tutor state from session and checkpoint.

    Args:
        session: Tutoring session from database
        repo: Tutor repository

    Returns:
        Complete TutorState dictionary

    """
    # Get current state from checkpoint
    config = {"configurable": {"thread_id": str(session.id)}}
    try:
        state_snapshot = await tutor_workflow.aget_state(config)
        current_state = state_snapshot.values if state_snapshot else {}
    except Exception:
        current_state = {}

    # Load conversation history from database
    _, messages = await repo.get_session_with_messages(session.id)
    conversation_history = [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
            "metadata": msg.message_metadata,
        }
        for msg in messages
    ]

    # Build complete state
    return {
        "session_id": str(session.id),
        "analysis_id": str(session.analysis_id) if session.analysis_id else None,
        "syllabus": session.syllabus or current_state.get("syllabus"),
        "current_section": session.current_section,
        "current_lesson": session.current_lesson,
        "current_phase": session.current_phase,
        "user_level": session.user_level,
        "understanding_scores": session.understanding_scores or {},
        "conversation_history": conversation_history,
        "conversation_summary": session.conversation_summary,
        "last_user_message": None,
        "last_assistant_response": current_state.get("last_assistant_response"),
        "user_ready": current_state.get("user_ready", False),
        "attempts_current_lesson": current_state.get("attempts_current_lesson", 0),
        "session_metadata": session.session_metadata,
    }


def build_tutor_state(
    session_id: uuid.UUID,
    analysis_id: uuid.UUID | None,
    user_level: str,
) -> TutorState:
    """Build initial tutor state for new session.

    Args:
        session_id: Session UUID
        analysis_id: Optional analysis UUID
        user_level: User skill level

    Returns:
        Initial TutorState dictionary

    """
    return {
        "session_id": str(session_id),
        "analysis_id": str(analysis_id) if analysis_id else None,
        "syllabus": None,
        "current_section": 0,
        "current_lesson": 0,
        "current_phase": "syllabus_generation",
        "user_level": user_level,
        "understanding_scores": {},
        "conversation_history": [],
        "conversation_summary": None,
        "last_user_message": None,
        "last_assistant_response": None,
        "user_ready": False,
        "attempts_current_lesson": 0,
        "session_metadata": None,
    }
