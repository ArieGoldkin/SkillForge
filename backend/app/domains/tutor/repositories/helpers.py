"""Helper functions for tutor repository operations.

Extracted to reduce file size and improve maintainability.
"""

from datetime import UTC, datetime

from app.db.models.tutoring import TutoringSession


def update_session_fields(  # noqa: PLR0913 - Repository method needs many optional parameters
    session: TutoringSession,
    syllabus: dict[str, object] | None = None,
    current_section: int | None = None,
    current_lesson: int | None = None,
    current_phase: str | None = None,
    understanding_scores: dict[str, float] | None = None,
    conversation_summary: str | None = None,
    status: str | None = None,
) -> None:
    """Update session model fields.

    Args:
        session: TutoringSession model instance
        syllabus: Optional syllabus to update
        current_section: Optional section index to update
        current_lesson: Optional lesson index to update
        current_phase: Optional phase to update
        understanding_scores: Optional understanding scores to update
        conversation_summary: Optional conversation summary to update
        status: Optional status to update

    """
    if syllabus is not None:
        session.syllabus = syllabus  # type: ignore[assignment]
    if current_section is not None:
        session.current_section = current_section  # type: ignore[assignment]
    if current_lesson is not None:
        session.current_lesson = current_lesson  # type: ignore[assignment]
    if current_phase is not None:
        session.current_phase = current_phase  # type: ignore[assignment]
    if understanding_scores is not None:
        session.understanding_scores = understanding_scores  # type: ignore[assignment]
    if conversation_summary is not None:
        session.conversation_summary = conversation_summary  # type: ignore[assignment]
    if status is not None:
        session.status = status  # type: ignore[assignment]
        if status in ("completed", "abandoned"):
            session.completed_at = datetime.now(UTC)  # type: ignore[assignment]
