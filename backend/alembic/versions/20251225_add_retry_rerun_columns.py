"""Add retry and rerun support columns to analyses table.

Revision ID: 20251225_retry_rerun
Revises: 20251223_agent_status
Create Date: 2025-12-25 00:00:00.000000

Issue #544 follow-up: Add retry/rerun tracking for failed and completed analyses.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID  # noqa: N811

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251225_retry_rerun"
down_revision: str | Sequence[str] | None = "20251223_agent_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add retry and rerun tracking columns to analyses table.

    This migration adds four new columns to the analyses table:
    - retry_count: Track retry attempts for failed analyses
    - last_retry_at: Timestamp of last retry trigger
    - rerun_count: Track rerun attempts for completed analyses
    - previous_artifact_id: Archive old artifact before rerun
    """
    # Add retry_count column with default 0
    op.add_column(
        "analyses",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of retry attempts for failed analyses",
        ),
    )

    # Add last_retry_at column for tracking when last retry was triggered
    op.add_column(
        "analyses",
        sa.Column(
            "last_retry_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last retry attempt",
        ),
    )

    # Add rerun_count column with default 0
    op.add_column(
        "analyses",
        sa.Column(
            "rerun_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Number of rerun attempts for completed analyses",
        ),
    )

    # Add previous_artifact_id column to archive old artifact before rerun
    op.add_column(
        "analyses",
        sa.Column(
            "previous_artifact_id",
            PostgresUUID(as_uuid=True),
            nullable=True,
            comment="UUID of previous artifact before rerun (FK to artifacts.id)",
        ),
    )

    # Add foreign key constraint for previous_artifact_id
    op.create_foreign_key(
        "fk_analyses_previous_artifact",
        "analyses",
        "artifacts",
        ["previous_artifact_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Create index on retry_count for querying failed analyses that can be retried
    op.create_index("ix_analyses_retry_count", "analyses", ["retry_count"])


def downgrade() -> None:
    """Remove retry and rerun tracking columns from analyses table.

    This reverts the migration by dropping the index, foreign key, and columns.
    Note: This will permanently delete all retry/rerun tracking data.
    """
    # Drop index first
    op.drop_index("ix_analyses_retry_count", table_name="analyses")

    # Drop foreign key constraint
    op.drop_constraint("fk_analyses_previous_artifact", "analyses", type_="foreignkey")

    # Drop columns in reverse order
    op.drop_column("analyses", "previous_artifact_id")
    op.drop_column("analyses", "rerun_count")
    op.drop_column("analyses", "last_retry_at")
    op.drop_column("analyses", "retry_count")
