"""Tutoring models for Socratic tutoring system."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TutoringSession(Base):
    """Tutoring session model for Socratic tutoring interactions.

    Sessions represent a tutoring conversation, optionally linked to an
    analysis. Sessions can exist independently (for general tutoring).

    Uses SQLAlchemy 2.0 style Mapped[] annotations for proper type inference.
    """

    __tablename__ = "tutoring_sessions"

    # Primary key and foreign keys
    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Workflow state
    syllabus: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # Generated curriculum structure
    current_section: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )  # Current section index (0-based)
    current_lesson: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )  # Current lesson index (0-based)
    current_phase: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="syllabus_generation", index=True
    )  # Current workflow phase
    user_level: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="intermediate"
    )  # User skill level
    understanding_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )  # Per-concept understanding scores
    conversation_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # Summarized conversation history
    session_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # Session configuration, preferences

    # Status and timestamps
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship
    analysis = relationship("Analysis", backref="tutoring_sessions")


class TutoringMessage(Base):
    """Tutoring message model storing conversation messages.

    Messages are part of a tutoring session and can be from the user
    or assistant. Stores the conversation history for context.

    Uses SQLAlchemy 2.0 style Mapped[] annotations for proper type inference.
    """

    __tablename__ = "tutoring_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("tutoring_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # Additional metadata (tokens, model, etc.)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationship
    session = relationship("TutoringSession", backref="messages")
