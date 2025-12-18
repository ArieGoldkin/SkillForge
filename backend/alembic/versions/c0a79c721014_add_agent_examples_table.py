"""Add agent_examples table for Few-Shot Prompting.

Revision ID: c0a79c721014
Revises: 500313d1cac9
Create Date: 2025-12-16 20:35:59.147503

Phase 1, Week 1.1: Few-Shot Prompting Infrastructure
This table stores high-quality agent examples with embeddings for semantic retrieval.
Supports dynamic few-shot example selection based on input similarity.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c0a79c721014"
down_revision: str | None = "500313d1cac9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create agent_examples table with vector embedding support."""
    op.create_table(
        "agent_examples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False, index=True),
        # Few-shot data
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column(
            "output_example",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("context_note", sa.Text(), nullable=True),
        # Quality metadata
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_golden", sa.Boolean(), nullable=False, server_default="false"),
        # Semantic search
        sa.Column("embedding", Vector(1536), nullable=False),
        # Auditing
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Constraints
        sa.CheckConstraint(
            "quality_score >= 0.0 AND quality_score <= 1.0",
            name="chk_quality_score_range",
        ),
    )

    # Create index for quality filtering
    op.create_index(
        "ix_agent_examples_quality",
        "agent_examples",
        ["quality_score"],
    )

    # Create composite index for common query pattern (agent + quality)
    op.create_index(
        "ix_agent_examples_type_quality",
        "agent_examples",
        ["agent_type", "quality_score"],
    )

    # Create IVFFlat index for fast semantic search
    # IVFFlat is better for smaller datasets (<1M rows) than HNSW
    op.execute(
        """
        CREATE INDEX ix_agent_examples_embedding_ivfflat
        ON agent_examples
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    """Drop agent_examples table."""
    op.drop_index("ix_agent_examples_embedding_ivfflat", table_name="agent_examples")
    op.drop_index("ix_agent_examples_type_quality", table_name="agent_examples")
    op.drop_index("ix_agent_examples_quality", table_name="agent_examples")
    # agent_type index is dropped automatically with the table
    op.drop_table("agent_examples")
