"""Chunk-level embeddings for analyses."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalysisChunk(Base):
    """Chunk-level embeddings with path/granularity metadata.

    This model represents individual chunks of analyzed content with their embeddings,
    supporting semantic search, keyword search, and hierarchical navigation.

    Attributes:
        id: Unique chunk identifier
        analysis_id: Foreign key to parent analysis
        granularity: Chunk granularity level ('coarse', 'fine', 'summary')
        path: Hierarchical path as JSONB array (e.g., ["section", "subsection", "chunk"])
        section_title: Title of the section containing this chunk
        chunk_idx: Zero-based index of this chunk within its section
        chunk_total: Total number of chunks in this section
        content_type: Content type (denormalized from analyses for filtering)
        language: Language code (e.g., 'en', 'es')
        hash: SHA256 hash of normalized content (for deduplication)
        model: Embedding model name (e.g., 'text-embedding-3-small')
        model_version: Model version for cache invalidation
        snippet: Content preview (~200 chars)
        vector: 1536-dimensional embedding vector (OpenAI text-embedding-3-small)
        content_tsvector: Full-text search vector (auto-populated by trigger)
        token_count: Token count for telemetry and cost tracking
        embedding_latency_ms: Embedding generation latency for monitoring
        was_truncated: Whether content was truncated before embedding
        pii_flag: Whether PII was detected in this chunk (Issue #220)
        pii_types: List of detected PII types (e.g., ["email", "phone_us"])
        # - never contains actual PII
        created_at: Chunk creation timestamp
        updated_at: Last update timestamp (auto-updated)

    Indexes:
        - HNSW index on vector for fast semantic search
        - GIN index on content_tsvector for keyword search
        - B-tree index on (hash, model, model_version) for cache lookups
        - Composite indexes for common query patterns

    Constraints:
        - granularity must be 'coarse', 'fine', or 'summary'
        - chunk_idx must be non-negative
        - chunk_total must be positive
        - chunk_idx must be less than chunk_total

    """

    __tablename__ = "analysis_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunking metadata
    granularity: Mapped[str] = mapped_column(String(20), nullable=False)  # coarse | fine | summary
    path: Mapped[list[str]] = mapped_column(JSONB, nullable=False)  # list[str]
    section_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    chunk_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_total: Mapped[int] = mapped_column(Integer, nullable=False)

    # Content metadata
    content_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Denormalized for filtering
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Deduplication
    hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Embedding metadata
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Content preview
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Vector embedding
    vector: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    # Full-text search vector (auto-populated by database trigger)
    content_tsvector: Mapped[Any | None] = mapped_column(TSVECTOR, nullable=True)

    # Telemetry fields
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Token count for cost tracking
    embedding_latency_ms: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Embedding generation latency
    was_truncated: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Whether content was truncated

    # PII metadata (Issue #220)
    # Note: Only stores detection flags, NEVER actual PII values
    pii_flag: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Whether PII was detected
    pii_types: Mapped[list[str] | None] = mapped_column(
        JSONB, nullable=True
    )  # List of PII types detected, e.g., ["email", "phone_us"]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    analysis = relationship("Analysis", backref="chunks")

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            "granularity IN ('coarse', 'fine', 'summary')",
            name="chk_granularity",
        ),
        CheckConstraint(
            "chunk_idx >= 0",
            name="chk_chunk_idx_positive",
        ),
        CheckConstraint(
            "chunk_total > 0",
            name="chk_chunk_total_positive",
        ),
        CheckConstraint(
            "chunk_idx < chunk_total",
            name="chk_chunk_idx_lt_total",
        ),
    )

    def path_str(self) -> str:
        """Return a stringified path for convenience."""
        if isinstance(self.path, Sequence):
            return " / ".join(str(x) for x in self.path)
        return ""

    # Property aliases to provide consistent interface for SearchService
    @property
    def content(self) -> str | None:
        """Alias for snippet to provide consistent SearchService interface."""
        snippet_value = self.snippet
        return str(snippet_value) if snippet_value is not None else None

    @property
    def chunk_type(self) -> str:
        """Alias for granularity to provide consistent SearchService interface."""
        granularity_value = self.granularity
        return str(granularity_value) if granularity_value else "unknown"

    @property
    def embedding(self) -> list[float] | None:
        """Alias for vector to provide consistent SearchService interface."""
        return self.vector

    @property
    def chunk_metadata(self) -> dict:
        """Build metadata dict from individual fields for SearchService."""
        return {
            "section": self.section_title,
            "path": self.path,
            "content_type": self.content_type,
            "language": self.language,
            "chunk_idx": self.chunk_idx,
            "chunk_total": self.chunk_total,
        }
