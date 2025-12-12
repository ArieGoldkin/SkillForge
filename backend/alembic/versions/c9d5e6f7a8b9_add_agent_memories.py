"""Add agent_memories table for RAG-based context engineering.

Revision ID: c9d5e6f7a8b9
Revises: b8c4d5e6f7a8
Create Date: 2025-12-10 21:00:00.000000

Issue #245: Agent Memory Access (RAG)
Sprint 11: Context Engineering

This table stores past findings, patterns, and summaries for agent recall:
- Reactive recall: Agents search via MCP tool
- Proactive recall: System pre-injects relevant context
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d5e6f7a8b9"
down_revision: str | None = "b8c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create agent_memories table with vector embedding support."""
    op.create_table(
        "agent_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "analysis_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("memory_type", sa.String(50), nullable=False, index=True),
        sa.Column("agent_type", sa.String(50), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("relevance_score", sa.Float(), default=1.0),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column(
            "memory_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Constraints
        sa.CheckConstraint(
            "memory_type IN ('analysis_summary', 'vulnerability_pattern', "
            "'best_practice', 'agent_finding')",
            name="chk_memory_type",
        ),
        sa.CheckConstraint(
            "relevance_score >= 0 AND relevance_score <= 1",
            name="chk_relevance_score_range",
        ),
    )

    # Create composite index for common query pattern
    op.create_index(
        "ix_agent_memories_type_created",
        "agent_memories",
        ["memory_type", "created_at"],
    )

    # Create HNSW index for fast semantic search
    op.execute(
        """
        CREATE INDEX ix_agent_memories_embedding_hnsw
        ON agent_memories
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )


def downgrade() -> None:
    """Drop agent_memories table."""
    op.drop_index("ix_agent_memories_embedding_hnsw", table_name="agent_memories")
    op.drop_index("ix_agent_memories_type_created", table_name="agent_memories")
    op.drop_table("agent_memories")
