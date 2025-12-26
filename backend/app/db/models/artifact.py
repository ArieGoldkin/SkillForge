"""Artifact model for generated implementation guides."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.annotation_queue import AnnotationQueue


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
    trace_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    # Note: explicit foreign_keys needed because Analysis.previous_artifact_id
    # creates a second FK path between Analysis and Artifact tables
    analysis = relationship(
        "Analysis",
        foreign_keys=[analysis_id],
        backref="artifacts",
    )
    annotation_queues: Mapped[list["AnnotationQueue"]] = relationship(
        "AnnotationQueue",
        back_populates="artifact",
        cascade="all, delete-orphan",
    )
