"""Progress model for workflow progress tracking."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811

from app.db.base import Base


class AnalysisProgress(Base):
    """Analysis progress model tracking workflow stages and status.

    Stores progress information for each stage of the analysis pipeline,
    enabling monitoring and resumability of long-running workflows.
    """

    __tablename__ = "analysis_progress"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    progress_data = Column(JSONB)  # Stage-specific progress information
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
