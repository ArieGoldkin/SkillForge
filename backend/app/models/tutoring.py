"""Tutoring models for Socratic tutoring system."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import relationship

from app.db.base import Base


class TutoringSession(Base):
    """Tutoring session model for Socratic tutoring interactions.

    Sessions represent a tutoring conversation, optionally linked to an
    analysis. Sessions can exist independently (for general tutoring).
    """

    __tablename__ = "tutoring_sessions"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_metadata = Column(JSONB)  # Session configuration, preferences
    status = Column(String(50), nullable=False, default="active", index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    analysis = relationship("Analysis", backref="tutoring_sessions")


class TutoringMessage(Base):
    """Tutoring message model storing conversation messages.

    Messages are part of a tutoring session and can be from the user
    or assistant. Stores the conversation history for context.
    """

    __tablename__ = "tutoring_messages"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tutoring_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSONB)  # Additional metadata (tokens, model, etc.)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Relationship
    session = relationship("TutoringSession", backref="messages")
