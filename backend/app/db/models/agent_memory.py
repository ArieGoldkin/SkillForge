"""Agent memory model for RAG-based context engineering.

Issue #245: Agent Memory Access (RAG)
Implements reactive and proactive recall patterns from Google ADK's Context Engineering.
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MemoryType(str, Enum):
    """Types of memories that can be stored and retrieved."""

    ANALYSIS_SUMMARY = "analysis_summary"
    VULNERABILITY_PATTERN = "vulnerability_pattern"
    BEST_PRACTICE = "best_practice"
    AGENT_FINDING = "agent_finding"
    # Tier 3 Research Agent memory types
    USER_PREFERENCE = "user_preference"
    TREND_HISTORY = "trend_history"
    KNOWLEDGE_CONNECTION = "knowledge_connection"


class AgentMemory(Base):
    """Memory entries for agent context engineering.

    This model stores past findings, patterns, and summaries that agents
    can recall (reactively via tool or proactively via pre-injection).

    Attributes:
        id: Unique memory identifier
        analysis_id: Foreign key to source analysis (optional for patterns)
        memory_type: Type of memory (analysis_summary, vulnerability_pattern, etc.)
        agent_type: Which agent created this memory (security_auditor, etc.)
        content: The memory content text
        embedding: 1536-dimensional vector for semantic search
        relevance_score: Quality/relevance score (0-1) for ranking
        metadata: Flexible JSONB for additional context
        created_at: When the memory was created

    Indexes:
        - HNSW index on embedding for fast semantic search
        - B-tree on (memory_type, created_at) for filtered queries
        - B-tree on analysis_id for cascade deletes

    """

    __tablename__ = "agent_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )

    # Optional link to source analysis (some memories are cross-analysis patterns)
    analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Memory classification
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    agent_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Which agent created this

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

    # Quality metrics
    relevance_score: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )  # For ranking/filtering
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Track memory size

    # Flexible metadata (named memory_metadata to avoid SQLAlchemy MetaData conflict)
    memory_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    analysis = relationship("Analysis", backref="memories")

    # Table constraints and indexes
    __table_args__ = (
        CheckConstraint(
            "memory_type IN ('analysis_summary', 'vulnerability_pattern', "
            "'best_practice', 'agent_finding', 'user_preference', "
            "'trend_history', 'knowledge_connection')",
            name="chk_memory_type",
        ),
        CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 1",
            name="chk_relevance_score_range",
        ),
        # Composite index for common query pattern
        Index("ix_agent_memories_type_created", "memory_type", "created_at"),
    )

    @property
    def summary(self) -> str:
        """Return truncated content for preview."""
        max_preview = 200
        content_str = str(self.content) if self.content else ""
        if len(content_str) <= max_preview:
            return content_str
        return content_str[:max_preview] + "..."

    def to_snippet(self) -> dict:
        """Convert to lightweight snippet for injection into agent context."""
        return {
            "id": str(self.id),
            "type": str(self.memory_type),
            "content": str(self.content),
            "relevance": self.relevance_score,
            "metadata": self.memory_metadata or {},
        }
