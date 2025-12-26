"""Type-safe accessor functions for TutorState.

This module provides getter functions that encapsulate type: ignore comments
in one place, allowing all consuming code to be fully type-safe.

Usage:
    from app.domains.tutor.workflows.state_accessors import (
        get_syllabus,
        get_conversation_history,
    )

    syllabus = get_syllabus(state)  # Returns Syllabus | None
"""

from app.domains.tutor.workflows.state import TutorState
from app.domains.tutor.workflows.state_types import SessionMetadata, Syllabus
from app.shared.types import TutorMessage


def get_syllabus(state: TutorState) -> Syllabus | None:
    """Get syllabus from state with proper typing."""
    return state.get("syllabus")


def get_conversation_history(state: TutorState) -> list[TutorMessage]:
    """Get conversation history from state with proper typing."""
    return state.get("conversation_history", [])


def get_session_metadata(state: TutorState) -> SessionMetadata | None:
    """Get session metadata from state with proper typing."""
    return state.get("session_metadata")


def get_understanding_scores(state: TutorState) -> dict[str, float]:
    """Get understanding scores from state with proper typing."""
    return state.get("understanding_scores", {})
