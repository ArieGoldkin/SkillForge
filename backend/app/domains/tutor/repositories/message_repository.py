"""Message repository for tutor database operations.

Handles message CRUD operations, following repository pattern.
"""

from typing import Protocol, cast
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.tutoring import TutoringMessage, TutoringSession
from app.db.session import get_db

logger = get_logger(__name__)


class ITutorMessageRepository(Protocol):
    """Protocol interface for message repository operations."""

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


class TutorMessageRepository:
    """Repository implementation for message operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session

        """
        self.session = session

    async def get_session_with_messages(
        self, session_id: UUID
    ) -> tuple[TutoringSession, list[TutoringMessage]]:
        """Get session with all messages (for resume).

        Args:
            session_id: Session UUID

        Returns:
            Tuple of (TutoringSession, list of TutoringMessage)

        Raises:
            ValueError: If session not found

        """
        # Get session
        result = await self.session.execute(
            select(TutoringSession).where(TutoringSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            msg = f"Session {session_id} not found"
            raise ValueError(msg)

        # Get messages ordered by created_at
        result = await self.session.execute(
            select(TutoringMessage)
            .where(TutoringMessage.session_id == session_id)
            .order_by(TutoringMessage.created_at)
        )
        # Type cast: SQLAlchemy returns correct type but mypy can't infer it
        messages = cast("list[TutoringMessage]", list(result.scalars().all()))

        return session, messages

    async def save_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        message_metadata: dict[str, object] | None = None,
    ) -> TutoringMessage:
        """Save a message to the conversation history.

        Args:
            session_id: Session UUID
            role: Message role ('user' or 'assistant')
            content: Message content
            message_metadata: Optional message metadata

        Returns:
            Created TutoringMessage

        """
        message = TutoringMessage(
            session_id=session_id,
            role=role,
            content=content,
            message_metadata=message_metadata,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)

        logger.debug(
            "tutor_message_saved",
            session_id=str(session_id),
            role=role,
            content_length=len(content),
        )

        return message


def get_tutor_message_repository(
    session: AsyncSession = Depends(get_db),  # noqa: B008 - FastAPI dependency injection pattern
) -> ITutorMessageRepository:
    """Dependency injection for message repository.

    Args:
        session: Database session from dependency injection

    Returns:
        ITutorMessageRepository implementation

    """
    return TutorMessageRepository(session)
