"""Unified tutor repository interface.

Maintains backwards compatibility by composing session and message repositories.
"""

from typing import Protocol
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.tutoring import TutoringMessage, TutoringSession
from app.db.session import get_db
from app.domains.tutor.repositories.message_repository import (
    ITutorMessageRepository,
    get_tutor_message_repository,
)
from app.domains.tutor.repositories.session_repository import (
    ITutorSessionRepository,
    get_tutor_session_repository,
)

logger = get_logger(__name__)


class ITutorRepository(Protocol):
    """Protocol interface for tutor repository operations (backwards compatible)."""

    async def create_session(
        self,
        analysis_id: UUID | None = None,
        user_level: str = "intermediate",
        session_metadata: dict[str, object] | None = None,
    ) -> TutoringSession:
        """Create a new tutoring session."""
        ...

    async def get_session(self, session_id: UUID) -> TutoringSession | None:
        """Get a tutoring session by ID."""
        ...

    async def get_session_with_messages(
        self, session_id: UUID
    ) -> tuple[TutoringSession, list[TutoringMessage]]:
        """Get session with all messages (for resume)."""
        ...

    async def save_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        message_metadata: dict[str, object] | None = None,
    ) -> TutoringMessage:
        """Save a message to the conversation history."""
        ...

    async def get_analysis_summary(self, analysis_id: UUID) -> dict[str, object] | None:
        """Get analysis summary for context (from aggregated_insights)."""
        ...

    async def update_session_state(  # noqa: PLR0913 - Repository method needs many optional parameters
        self,
        session_id: UUID,
        syllabus: dict[str, object] | None = None,
        current_section: int | None = None,
        current_lesson: int | None = None,
        current_phase: str | None = None,
        understanding_scores: dict[str, float] | None = None,
        conversation_summary: str | None = None,
        status: str | None = None,
    ) -> TutoringSession:
        """Update session state fields."""
        ...


class TutorRepository:
    """Unified repository implementation (backwards compatible).

    Composes session and message repositories to maintain API compatibility.
    """

    def __init__(
        self,
        session: AsyncSession,
        session_repo: ITutorSessionRepository | None = None,
        message_repo: ITutorMessageRepository | None = None,
    ) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session
            session_repo: Optional session repository (for dependency injection)
            message_repo: Optional message repository (for dependency injection)

        """
        self.session = session
        self._session_repo = session_repo or get_tutor_session_repository(session)
        self._message_repo = message_repo or get_tutor_message_repository(session)

    async def create_session(
        self,
        analysis_id: UUID | None = None,
        user_level: str = "intermediate",
        session_metadata: dict[str, object] | None = None,
    ) -> TutoringSession:
        """Create a new tutoring session."""
        return await self._session_repo.create_session(
            analysis_id=analysis_id,
            user_level=user_level,
            session_metadata=session_metadata,
        )

    async def get_session(self, session_id: UUID) -> TutoringSession | None:
        """Get a tutoring session by ID."""
        return await self._session_repo.get_session(session_id)

    async def get_session_with_messages(
        self, session_id: UUID
    ) -> tuple[TutoringSession, list[TutoringMessage]]:
        """Get session with all messages (for resume)."""
        return await self._message_repo.get_session_with_messages(session_id)

    async def save_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        message_metadata: dict[str, object] | None = None,
    ) -> TutoringMessage:
        """Save a message to the conversation history."""
        return await self._message_repo.save_message(
            session_id=session_id,
            role=role,
            content=content,
            message_metadata=message_metadata,
        )

    async def get_analysis_summary(self, analysis_id: UUID) -> dict[str, object] | None:
        """Get analysis summary for context (from aggregated_insights)."""
        from app.domains.tutor.services.analysis_service import get_analysis_summary

        return await get_analysis_summary(self.session, analysis_id)

    async def update_session_state(  # noqa: PLR0913 - Repository method needs many optional parameters
        self,
        session_id: UUID,
        syllabus: dict[str, object] | None = None,
        current_section: int | None = None,
        current_lesson: int | None = None,
        current_phase: str | None = None,
        understanding_scores: dict[str, float] | None = None,
        conversation_summary: str | None = None,
        status: str | None = None,
    ) -> TutoringSession:
        """Update session state fields."""
        return await self._session_repo.update_session_state(
            session_id=session_id,
            syllabus=syllabus,
            current_section=current_section,
            current_lesson=current_lesson,
            current_phase=current_phase,
            understanding_scores=understanding_scores,
            conversation_summary=conversation_summary,
            status=status,
        )


def get_tutor_repository(
    session: AsyncSession = Depends(get_db),  # noqa: B008 - FastAPI dependency injection pattern
) -> ITutorRepository:
    """Dependency injection for tutor repository (backwards compatible).

    Args:
        session: Database session from dependency injection

    Returns:
        ITutorRepository implementation

    """
    return TutorRepository(session)
