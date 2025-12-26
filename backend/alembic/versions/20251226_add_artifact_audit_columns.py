"""Add audit columns to artifacts table.

Revision ID: 20251226_audit_columns
Revises: 20251225_retry_rerun
Create Date: 2025-12-26 00:00:00.000000

Adds updated_at, is_deleted, and deleted_at columns to support soft delete
and audit trail functionality for artifacts.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251226_audit_columns"
down_revision: str | Sequence[str] | None = "20251225_retry_rerun"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add audit columns to artifacts table.

    This migration adds three audit columns:
    - updated_at: Timestamp of last update (initialized to created_at for existing rows)
    - is_deleted: Boolean flag for soft delete (default False)
    - deleted_at: Timestamp when artifact was soft deleted (nullable)

    Also creates a partial index on is_deleted = false for active artifacts.
    """
    # Add updated_at column - first as nullable with now() default
    op.add_column(
        "artifacts",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=sa.text("now()"),
            comment="Timestamp of last update",
        ),
    )

    # Update existing rows: set updated_at = created_at
    op.execute("UPDATE artifacts SET updated_at = created_at WHERE updated_at IS NULL")

    # Now make it non-nullable and remove server_default
    op.alter_column("artifacts", "updated_at", nullable=False, server_default=None)

    # Add is_deleted column with default False
    op.add_column(
        "artifacts",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="Soft delete flag",
        ),
    )

    # Add deleted_at column (nullable)
    op.add_column(
        "artifacts",
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when artifact was soft deleted",
        ),
    )

    # Create index on is_deleted for filtering active artifacts
    op.create_index(
        "ix_artifacts_is_deleted",
        "artifacts",
        ["is_deleted"],
    )

    # Create partial index for active artifacts (is_deleted = false)
    # This improves query performance when filtering for non-deleted artifacts
    op.execute(
        """
        CREATE INDEX ix_artifacts_active
        ON artifacts (id, analysis_id, created_at)
        WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    """Remove audit columns from artifacts table.

    This reverts the migration by dropping the partial index, regular index,
    and audit columns.
    Note: This will permanently delete all soft delete and audit trail data.
    """
    # Drop partial index for active artifacts
    op.drop_index("ix_artifacts_active", table_name="artifacts")

    # Drop regular index on is_deleted
    op.drop_index("ix_artifacts_is_deleted", table_name="artifacts")

    # Drop columns in reverse order
    op.drop_column("artifacts", "deleted_at")
    op.drop_column("artifacts", "is_deleted")
    op.drop_column("artifacts", "updated_at")
