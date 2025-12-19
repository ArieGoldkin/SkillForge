"""Annotation queue model for storing pending reviews.

This model tracks artifacts that need human review, either due to low quality
scores or manual flagging by users. Feedback is also submitted to Langfuse
as scores for observability.
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import UUID, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.artifact import Artifact


class AnnotationQueue(Base):
    """Model for annotation queue entries.

    Tracks artifacts that need human review, either due to low quality
    scores or manual flagging by users.

    Attributes:
        id: Primary key (auto-increment)
        artifact_id: Foreign key to artifacts table
        trace_id: Optional Langfuse trace ID for linking feedback
        reason: Why this was queued (low_quality, flagged_by_user, etc.)
        status: Current status (pending, reviewed, skipped)
        metadata: Additional context (scores, comments, user info)
        created_at: When this was queued
        reviewed_at: When this was reviewed (if applicable)

    """

    __tablename__ = "annotation_queue"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Foreign keys
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Langfuse trace ID (optional - may not have trace)
    trace_id: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        index=True,
    )

    # Queue metadata
    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Reason for queuing: 'low_quality', 'flagged_by_user', 'negative_feedback'",
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="pending",
        comment="Status: 'pending', 'reviewed', 'skipped'",
        index=True,
    )

    # Metadata (quality scores, user info, etc.)
    queue_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional context: quality_scores, user_id, comments",
    )

    # Timestamps (timezone-aware for PostgreSQL TIMESTAMP WITH TIME ZONE)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    artifact: Mapped["Artifact"] = relationship(
        "Artifact",
        back_populates="annotation_queues",
    )

    # Composite indexes for efficient queries
    __table_args__ = (
        Index("idx_annotation_queue_status_created", "status", "created_at"),
        Index("idx_annotation_queue_artifact_status", "artifact_id", "status"),
    )

    def __repr__(self) -> str:
        """Return string representation for debugging."""
        return f"<AnnotationQueue id={self.id} artifact_id={self.artifact_id} status={self.status}>"
