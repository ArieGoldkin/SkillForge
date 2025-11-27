"""Analysis model for content analysis pipeline."""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811

from app.db.base import Base


class Analysis(Base):
    """Analysis model representing a content analysis task.

    Stores information about URLs being analyzed, their content, embeddings,
    and processing status. This is the primary table in the system.
    """

    __tablename__ = "analyses"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False, index=True)
    content_type = Column(String(50), nullable=False)  # 'article', 'video', 'repo'
    title = Column(Text)
    raw_content = Column(Text)
    # Embedding vector for semantic search (OpenAI text-embedding-3-small: 1536 dimensions)
    content_embedding = Column(Vector(1536))
    extraction_metadata = Column(JSONB)  # Metadata from content extraction
    status = Column(String(50), nullable=False, default="pending", index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
