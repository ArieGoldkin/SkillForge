"""AnalysisChunk model for semantic and full-text search.

This model maps to the existing analysis_chunks table in the database,
which stores embeddings for content chunks from analyses. The schema
supports both semantic search via pgvector and metadata-based filtering.

Table schema (existing):
- id: UUID primary key
- analysis_id: UUID foreign key to analyses
- granularity: varchar(20) - chunk granularity level
- path: JSONB - hierarchical path to chunk
- section_title: text - section heading
- chunk_idx: integer - chunk index within section
- chunk_total: integer - total chunks in section
- content_type: varchar(50) - type of content
- language: varchar(20) - content language
- hash: varchar(128) - content hash for deduplication
- model: varchar(100) - embedding model used
- model_version: varchar(50) - model version
- snippet: text - the actual content text
- vector: vector(1536) - embedding vector
- created_at: timestamp with timezone
- updated_at: timestamp with timezone
"""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import relationship

from app.db.base import Base


class AnalysisChunk(Base):
    """AnalysisChunk model representing searchable content chunks.

    Maps to the existing analysis_chunks table which stores chunked content
    from analyses with vector embeddings for semantic search.

    Attributes:
        id: UUID primary key
        analysis_id: Foreign key to parent analysis
        granularity: Chunk granularity level (e.g., 'section', 'paragraph')
        path: Hierarchical path to chunk location (JSONB)
        section_title: Section heading/title
        chunk_idx: Index of this chunk within its section
        chunk_total: Total chunks in the section
        content_type: Type of content (e.g., 'article', 'code')
        language: Content language
        hash: Content hash for deduplication
        model: Embedding model name
        model_version: Embedding model version
        snippet: The actual text content (searchable)
        vector: 1536-dimensional embedding vector
        created_at: When the chunk was created
        updated_at: When the chunk was last updated

    """

    __tablename__ = "analysis_chunks"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id"),
        nullable=False,
        index=True,
    )

    # Chunk identification
    granularity = Column(String(20), nullable=False)  # 'section', 'paragraph', etc.
    path = Column(JSONB, nullable=False)  # Hierarchical path
    section_title = Column(Text, nullable=True)
    chunk_idx = Column(Integer, nullable=False)
    chunk_total = Column(Integer, nullable=False)

    # Content metadata
    content_type = Column(String(50), nullable=True)
    language = Column(String(20), nullable=True)
    hash = Column(String(128), nullable=False)  # Content hash

    # Embedding info
    model = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)

    # Content
    snippet = Column(Text, nullable=True)  # The actual text content

    # Embedding vector for semantic search (1536 dimensions for OpenAI)
    vector = Column(Vector(1536), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationship to parent analysis
    analysis = relationship("Analysis", backref="chunks")

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
