"""Analysis model for content analysis pipeline."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.artifact import Artifact


class Analysis(Base):
    """Analysis model representing a content analysis task.

    Stores information about URLs being analyzed, their content, embeddings,
    and processing status. This is the primary table in the system.

    Context Engineering (Issue #244 - Handle Pattern):
        content_summary: LLM-generated summary for lightweight state refs
        content_sections: JSONB with code blocks, headings for partial loading
    """

    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    url: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    content_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'article', 'video', 'repo'
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Extracted text content. Stored with LZ4 compression (PostgreSQL 17 TOAST). "
        "Compression is transparent to application layer.",
    )
    # Embedding vector for semantic search (OpenAI text-embedding-3-small: 1536 dimensions)
    content_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    # Full-text search vector (automatically populated by database trigger)
    # Used for keyword-based search via PostgreSQL's GIN index
    search_vector: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)
    extraction_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    # Error tracking fields (Issue #441)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_at_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    # Context Engineering: Handle Pattern (Issue #244)
    # Summary for lightweight ArtifactRef in state (~500 tokens)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Section metadata for partial loading: code_blocks, headings, word_count
    content_sections: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    # Retry/Rerun tracking (Issue #544 follow-up)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rerun_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    previous_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    previous_artifact: Mapped["Artifact | None"] = relationship(
        "Artifact",
        foreign_keys=[previous_artifact_id],
        uselist=False,
    )
