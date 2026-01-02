"""Agent finding model for multi-agent analysis results."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AgentFinding(Base):
    """Agent finding model storing results from specialized analysis agents.

    Each finding represents the output from a specific agent type (e.g.,
    Tech Comparator, Security Auditor) analyzing content from an Analysis.

    Status Tracking:
        - status: Execution status ('success', 'failed', 'skipped', 'timeout')
        - error_code: Machine-readable error identifier (e.g., 'TIMEOUT', 'VALIDATION_ERROR')
        - error_message: Human-readable error description for debugging
    """

    __tablename__ = "agent_findings"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    findings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )  # Structured findings from agent
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Status tracking columns
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success", index=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    analysis = relationship("Analysis", backref="agent_findings")
