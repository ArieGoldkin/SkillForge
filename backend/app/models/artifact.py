"""Artifact model for generated implementation guides."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Artifact(Base):
    """Artifact model storing generated implementation guides.

    Artifacts are markdown documents generated from analysis results,
    containing implementation guides, tutorials, and reference materials.
    """

    __tablename__ = "artifacts"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    markdown_content = Column(Text, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    artifact_metadata = Column(JSONB)  # topics, tags, complexity, etc.
    download_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Relationship
    analysis = relationship("Analysis", backref="artifacts")
