"""Chunk-level embeddings for analyses."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import relationship

from app.db.base import Base


class AnalysisChunk(Base):
    """Chunk-level embeddings with path/granularity metadata."""

    __tablename__ = "analysis_chunks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False, index=True
    )
    granularity = Column(String(20), nullable=False)  # coarse | fine | summary
    path = Column(JSONB, nullable=False)  # list[str]
    section_title = Column(Text)
    chunk_idx = Column(Integer, nullable=False)
    chunk_total = Column(Integer, nullable=False)
    content_type = Column(String(50))
    language = Column(String(20))
    hash = Column(String(128), nullable=False)
    model = Column(String(100))
    model_version = Column(String(50))
    snippet = Column(Text)
    vector = Column(Vector(1536), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    analysis = relationship("Analysis", backref="chunks")

    def path_str(self) -> str:
        """Return a stringified path for convenience."""
        if isinstance(self.path, Sequence):
            return " / ".join(map(str, self.path))
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
        return self.vector  # type: ignore[return-value]

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
