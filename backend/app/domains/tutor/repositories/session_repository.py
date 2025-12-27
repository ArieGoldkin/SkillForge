"""Session repository for tutor database operations.

Handles session CRUD operations, following repository pattern.
"""

from typing import Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branded_ids import AnalysisID, SessionID
from app.core.logging import get_logger
from app.db.models.tutoring import TutoringSession
from app.db.session import get_db

logger = get_logger(__name__)


class ITutorSessionRepository(Protocol):
    """Protocol interface for session repository operations."""

    async def create_session(
        self,
        analysis_id: AnalysisID | None = None,
        user_level: str = "intermediate",
        session_metadata: dict[str, object] | None = None,
    ) -> TutoringSession:
        """Create a new tutoring session."""
        ...

    async def get_session(self, session_id: SessionID) -> TutoringSession | None:
        """Get a tutoring session by ID."""
        ...

    async def update_session_state(  # noqa: PLR0913 - Repository method needs many optional parameters
        self,
        session_id: SessionID,
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


class TutorSessionRepository:
    """Repository implementation for session operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session

        """
        self.session = session

    async def create_session(
        self,
        analysis_id: AnalysisID | None = None,
        user_level: str = "intermediate",
        session_metadata: dict[str, object] | None = None,
    ) -> TutoringSession:
        """Create a new tutoring session."""
        session = TutoringSession(
            analysis_id=analysis_id,
            user_level=user_level,
            session_metadata=session_metadata,
            status="active",
        )
        self.session.add(session)
        await self.session.commit()
        await self.session.refresh(session)

        logger.info(
            "tutor_session_created",
            session_id=str(session.id),
            analysis_id=str(analysis_id) if analysis_id else None,
            user_level=user_level,
        )

        return session

    async def get_session(self, session_id: SessionID) -> TutoringSession | None:
        """Get a tutoring session by ID."""
        result = await self.session.execute(
            select(TutoringSession).where(TutoringSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def update_session_state(  # noqa: PLR0913 - Repository method needs many optional parameters
        self,
        session_id: SessionID,
        syllabus: dict[str, object] | None = None,
        current_section: int | None = None,
        current_lesson: int | None = None,
        current_phase: str | None = None,
        understanding_scores: dict[str, float] | None = None,
        conversation_summary: str | None = None,
        status: str | None = None,
    ) -> TutoringSession:
        """Update session state fields."""
        from app.domains.tutor.repositories.helpers import update_session_fields

        session = await self.get_session(session_id)
        if not session:
            msg = f"Session {session_id} not found"
            raise ValueError(msg)

        update_session_fields(
            session,
            syllabus=syllabus,
            current_section=current_section,
            current_lesson=current_lesson,
            current_phase=current_phase,
            understanding_scores=understanding_scores,
            conversation_summary=conversation_summary,
            status=status,
        )

        await self.session.commit()
        await self.session.refresh(session)

        logger.debug(
            "tutor_session_state_updated",
            session_id=str(session_id),
            current_phase=current_phase,
            current_section=current_section,
            current_lesson=current_lesson,
        )

        return session


def get_tutor_session_repository(
    session: AsyncSession = Depends(get_db),  # noqa: B008 - FastAPI dependency injection pattern
) -> ITutorSessionRepository:
    """Dependency injection for session repository."""
    return TutorSessionRepository(session)
