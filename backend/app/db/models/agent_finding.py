"""Agent finding model for multi-agent analysis results."""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import relationship

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

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    analysis_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type = Column(String(100), nullable=False, index=True)
    findings = Column(JSONB, nullable=False)  # Structured findings from agent
    confidence_score = Column(Float)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    # Status tracking columns
    status = Column(String(20), nullable=False, default="success", index=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationship
    analysis = relationship("Analysis", backref="agent_findings")
