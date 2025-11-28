"""Initial database schema.

Revision ID: a37ac3b6a635
Revises: e3c50d69e442
Create Date: 2025-11-21 11:01:23.783466

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a37ac3b6a635"
down_revision: str | Sequence[str] | None = "e3c50d69e442"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create initial database schema with all tables."""
    # Create analyses table
    op.create_table(
        "analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("content_embedding", Vector(1536), nullable=True),
        sa.Column("extraction_metadata", JSONB(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_analyses_url", "analyses", ["url"])
    op.create_index("ix_analyses_status", "analyses", ["status"])

    # Create agent_findings table
    op.create_table(
        "agent_findings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", UUID(as_uuid=True), nullable=False),
        sa.Column("agent_type", sa.String(100), nullable=False),
        sa.Column("findings", JSONB(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_agent_findings_analysis_id", "agent_findings", ["analysis_id"])
    op.create_index("ix_agent_findings_agent_type", "agent_findings", ["agent_type"])

    # Create artifacts table
    op.create_table(
        "artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", UUID(as_uuid=True), nullable=False),
        sa.Column("markdown_content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("artifact_metadata", JSONB(), nullable=True),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_artifacts_analysis_id", "artifacts", ["analysis_id"])

    # Create tutoring_sessions table
    op.create_table(
        "tutoring_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", UUID(as_uuid=True), nullable=True),
        sa.Column("session_metadata", JSONB(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_tutoring_sessions_analysis_id", "tutoring_sessions", ["analysis_id"])
    op.create_index("ix_tutoring_sessions_status", "tutoring_sessions", ["status"])

    # Create tutoring_messages table
    op.create_table(
        "tutoring_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["tutoring_sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_tutoring_messages_session_id", "tutoring_messages", ["session_id"])

    # Create analysis_progress table
    op.create_table(
        "analysis_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("analysis_id", UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("progress_data", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["analyses.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_analysis_progress_analysis_id", "analysis_progress", ["analysis_id"])
    op.create_index("ix_analysis_progress_stage", "analysis_progress", ["stage"])
    op.create_index("ix_analysis_progress_status", "analysis_progress", ["status"])


def downgrade() -> None:
    """Drop all tables in reverse order."""
    op.drop_index("ix_analysis_progress_status", table_name="analysis_progress")
    op.drop_index("ix_analysis_progress_stage", table_name="analysis_progress")
    op.drop_index("ix_analysis_progress_analysis_id", table_name="analysis_progress")
    op.drop_table("analysis_progress")

    op.drop_index("ix_tutoring_messages_session_id", table_name="tutoring_messages")
    op.drop_table("tutoring_messages")

    op.drop_index("ix_tutoring_sessions_status", table_name="tutoring_sessions")
    op.drop_index("ix_tutoring_sessions_analysis_id", table_name="tutoring_sessions")
    op.drop_table("tutoring_sessions")

    op.drop_index("ix_artifacts_analysis_id", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_agent_findings_agent_type", table_name="agent_findings")
    op.drop_index("ix_agent_findings_analysis_id", table_name="agent_findings")
    op.drop_table("agent_findings")

    op.drop_index("ix_analyses_status", table_name="analyses")
    op.drop_index("ix_analyses_url", table_name="analyses")
    op.drop_table("analyses")
