"""add analysis_chunks table

Revision ID: 20251209120000
Revises:
Create Date: 2025-12-09 12:00:00.000000
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251209120000"
down_revision = "20251204091348"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_chunks",
        sa.Column(
            "id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "analysis_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analyses.id"),
            nullable=False,
        ),
        sa.Column("granularity", sa.String(length=20), nullable=False),
        sa.Column("path", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("section_title", sa.Text(), nullable=True),
        sa.Column("chunk_idx", sa.Integer(), nullable=False),
        sa.Column("chunk_total", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("hash", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("vector", Vector(1536), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_analysis_chunks_analysis_id ON analysis_chunks (analysis_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_analysis_chunks_granularity ON analysis_chunks (granularity)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_analysis_chunks_granularity")
    op.execute("DROP INDEX IF EXISTS ix_analysis_chunks_analysis_id")
    op.drop_table("analysis_chunks")
