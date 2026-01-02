"""Progress model for workflow progress tracking."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisProgress(Base):
    """Analysis progress model tracking workflow stages and status.

    Stores progress information for each stage of the analysis pipeline,
    enabling monitoring and resumability of long-running workflows.
    """

    __tablename__ = "analysis_progress"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    progress_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # Stage-specific progress information
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
