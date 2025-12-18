"""SQLAlchemy model for agent few-shot examples.

Stores high-quality agent outputs for few-shot prompting (Phase 1).
Used by SemanticExampleSelector to improve agent output quality.
"""

import uuid
from datetime import UTC, datetime

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import Boolean, Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811

from app.db.base import Base


class AgentExample(Base):
    """Store high-quality agent outputs for few-shot prompting.

    This model stores curated examples from the golden dataset that can be
    injected into agent prompts to improve output quality. Each example
    includes the input summary, output structure, quality score, and an
    embedding for semantic similarity search.

    Phase 1: Few-Shot Prompting - Week 1.2
    Target: 15-25% quality improvement through example injection

    Example:
        >>> example = AgentExample(
        ...     agent_type="tech_comparator",
        ...     input_summary="Comparing React vs Vue state management",
        ...     output_example={"key_differences": [...], "recommendation": "..."},
        ...     quality_score=0.95,
        ...     is_golden=True,
        ... )
        >>> session.add(example)

    """

    __tablename__ = "agent_examples"

    id = Column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    agent_type = Column(String(50), nullable=False, index=True)

    # Few-shot data
    input_summary = Column(Text, nullable=False)
    input_content_preview = Column(Text, nullable=True)  # First 2000 chars
    output_example = Column(JSON, nullable=False)
    context_note = Column(Text, nullable=True)

    # Quality metadata
    quality_score = Column(Float, nullable=False, default=1.0, index=True)
    is_golden = Column(Boolean, default=False)
    source_analysis_id = Column(PostgresUUID(as_uuid=True), nullable=True)

    # Semantic search (OpenAI text-embedding-3-small: 1536 dimensions)
    embedding = Column(Vector(1536), nullable=True)

    # Content classification
    content_type = Column(String(50), nullable=True, index=True)  # article, video, repo
    difficulty_level = Column(String(20), nullable=True)  # beginner, intermediate, advanced

    # Auditing
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AgentExample {self.agent_type}:{self.id}>"
