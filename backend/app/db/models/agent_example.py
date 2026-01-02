"""SQLAlchemy model for agent few-shot examples.

Stores high-quality agent outputs for few-shot prompting (Phase 1).
Used by SemanticExampleSelector to improve agent output quality.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Float, String, Text, text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column

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

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Few-shot data
    input_summary: Mapped[str] = mapped_column(Text, nullable=False)
    input_content_preview: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # First 2000 chars
    output_example: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    context_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Quality metadata
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, index=True)
    is_golden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True), nullable=True
    )

    # Semantic search (OpenAI text-embedding-3-small: 1536 dimensions)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    # Content classification
    content_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )  # article, video, repo
    difficulty_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # beginner, intermediate, advanced

    # Auditing
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<AgentExample {self.agent_type}:{self.id}>"
