"""State definitions for tutor workflow.

This module defines the TutorState TypedDict for the tutor agent workflow.
State is managed by LangGraph's StateGraph and automatically checkpointed.
"""

from typing import TypedDict

from app.core.types import AnalysisID


class TutorState(TypedDict, total=False):
    """State structure for the tutor workflow.

    All fields are optional (total=False) to allow incremental population
    as the workflow progresses through stages.

    Attributes:
        session_id: Unique identifier for this tutoring session
        analysis_id: Optional analysis ID this session is based on
        syllabus: Generated curriculum structure (Syllabus model)
        current_section: Current section index (0-based)
        current_lesson: Current lesson index (0-based)
        current_phase: Current workflow phase (TutorPhase enum)
        user_level: User's skill level (beginner, intermediate, advanced)
        understanding_scores: Per-concept understanding scores (dict)
        conversation_history: List of messages (Message models)
        conversation_summary: Summarized conversation history
        last_user_message: Last message from user
        last_assistant_response: Last response from assistant
        user_ready: Boolean indicating if user is ready to proceed
        attempts_current_lesson: Number of attempts at current lesson
        session_metadata: Additional session metadata

    """

    session_id: str
    analysis_id: AnalysisID | None
    syllabus: dict[str, object] | None
    current_section: int
    current_lesson: int
    current_phase: str
    user_level: str
    understanding_scores: dict[str, float]
    conversation_history: list[dict[str, object]]
    conversation_summary: str | None
    last_user_message: str | None
    last_assistant_response: str | None
    user_ready: bool
    attempts_current_lesson: int
    session_metadata: dict[str, object] | None
