"""State management service for tutor workflow.

Extracts state building logic from API endpoints.
"""

import uuid
from typing import TYPE_CHECKING, Any, cast

from app.core.logging import get_logger
from app.db.models.tutoring import TutoringSession
from app.domains.tutor.repositories import ITutorRepository
from app.domains.tutor.workflows.graph_builder import tutor_workflow
from app.domains.tutor.workflows.state import TutorState
from app.domains.tutor.workflows.state_types import SessionMetadata, Syllabus

if TYPE_CHECKING:
    from app.shared.types import TutorMessage

logger = get_logger(__name__)


def _parse_syllabus(data: dict[str, Any] | None) -> Syllabus | None:
    """Parse JSONB dict to Syllabus TypedDict.

    TypedDict is structurally typed, so a dict matching the shape is compatible.
    We use cast() since JSONB data was originally serialized from a Syllabus.

    Args:
        data: Raw dict from JSONB column or None

    Returns:
        Syllabus TypedDict or None

    """
    if data is None:
        return None
    return cast("Syllabus", data)


def _parse_session_metadata(data: dict[str, Any] | None) -> SessionMetadata | None:
    """Parse JSONB dict to SessionMetadata TypedDict.

    TypedDict is structurally typed, so a dict matching the shape is compatible.
    We use cast() since JSONB data was originally serialized from a SessionMetadata.

    Args:
        data: Raw dict from JSONB column or None

    Returns:
        SessionMetadata TypedDict or None

    """
    if data is None:
        return None
    return cast("SessionMetadata", data)


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
    except Exception:  # noqa: BLE001 - Langfuse may not be available, catch all to continue
        current_state = {}

    # Load conversation history from database
    # session.id returns uuid.UUID with SQLAlchemy 2.0 Mapped[] annotations
    _, messages = await repo.get_session_with_messages(session.id)
    conversation_history: list[TutorMessage] = [
        cast(
            "TutorMessage",
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat(),
                "metadata": msg.message_metadata,
            },
        )
        for msg in messages
    ]

    # Parse JSONB fields to proper TypedDict types
    syllabus_from_db = _parse_syllabus(session.syllabus)
    syllabus_from_checkpoint = current_state.get("syllabus")
    syllabus = syllabus_from_db if syllabus_from_db is not None else syllabus_from_checkpoint

    # Build complete state with proper types
    state: TutorState = {
        "session_id": str(session.id),
        "analysis_id": str(session.analysis_id) if session.analysis_id else None,
        "syllabus": syllabus,
        "current_section": session.current_section,
        "current_lesson": session.current_lesson,
        "current_phase": session.current_phase,
        "user_level": session.user_level,
        "understanding_scores": cast("dict[str, float]", session.understanding_scores or {}),
        "conversation_history": conversation_history,
        "conversation_summary": session.conversation_summary,
        "last_user_message": None,
        "last_assistant_response": current_state.get("last_assistant_response"),
        "user_ready": current_state.get("user_ready", False),
        "attempts_current_lesson": current_state.get("attempts_current_lesson", 0),
        "session_metadata": _parse_session_metadata(session.session_metadata),
    }
    return state


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
