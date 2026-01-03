"""Artifact model for generated implementation guides."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.annotation_queue import AnnotationQueue


class Artifact(Base):
    """Artifact model storing generated implementation guides.

    Artifacts are markdown documents generated from analysis results,
    containing implementation guides, tutorials, and reference materials.

    Uses SQLAlchemy 2.0 style Mapped[] annotations for proper type inference.
    """

    __tablename__ = "artifacts"

    # Primary key and foreign keys
    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content fields
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    artifact_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

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

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
