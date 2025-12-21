"""Analysis model for content analysis pipeline."""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811

from app.db.base import Base


class Analysis(Base):
    """Analysis model representing a content analysis task.

    Stores information about URLs being analyzed, their content, embeddings,
    and processing status. This is the primary table in the system.

    Context Engineering (Issue #244 - Handle Pattern):
        content_summary: LLM-generated summary for lightweight state refs
        content_sections: JSONB with code blocks, headings for partial loading
    """

    __tablename__ = "analyses"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False, unique=True, index=True)
    content_type = Column(String(50), nullable=False)  # 'article', 'video', 'repo'
    title = Column(Text)
    raw_content = Column(Text)
    # Embedding vector for semantic search (OpenAI text-embedding-3-small: 1536 dimensions)
    content_embedding = Column(Vector(1536))
    # Full-text search vector (automatically populated by database trigger)
    # Used for keyword-based search via PostgreSQL's GIN index
    search_vector = Column(TSVECTOR)
    extraction_metadata = Column(JSONB)  # Metadata from content extraction
    status = Column(String(50), nullable=False, default="pending", index=True)
    # Error tracking fields (Issue #441)
    error_code = Column(String(50), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    failed_at_stage = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    # Context Engineering: Handle Pattern (Issue #244)
    # Summary for lightweight ArtifactRef in state (~500 tokens)
    content_summary = Column(Text)
    # Section metadata for partial loading: code_blocks, headings, word_count
    content_sections = Column(JSONB, default=dict)
