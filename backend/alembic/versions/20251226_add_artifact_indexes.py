"""Add performance indexes to artifacts table.

Revision ID: 20251226_artifact_indexes
Revises: 20251226_audit_columns
Create Date: 2025-12-26 00:00:00.000000

Adds indexes to support common query patterns:
- Descending created_at for recent artifacts
- Descending download_count for popular artifacts
- Composite (analysis_id, version) for version lookups
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251226_artifact_indexes"
down_revision: str | Sequence[str] | None = "20251226_audit_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add performance indexes to artifacts table.

    Creates three indexes to optimize common query patterns:
    1. ix_artifacts_created_at_desc: For ordering by creation time (newest first)
    2. ix_artifacts_download_count_desc: For ordering by popularity
    3. ix_artifacts_analysis_version: For finding specific versions of analysis artifacts
    """
    # Index for ordering by created_at DESC (recent artifacts)
    op.create_index(
        "ix_artifacts_created_at_desc",
        "artifacts",
        [sa.text("created_at DESC")],
    )

    # Index for ordering by download_count DESC (popular artifacts)
    op.create_index(
        "ix_artifacts_download_count_desc",
        "artifacts",
        [sa.text("download_count DESC")],
    )

    # Composite index for finding artifacts by analysis_id and version
    # Useful for version history queries
    op.create_index(
        "ix_artifacts_analysis_version",
        "artifacts",
        ["analysis_id", "version"],
    )


def downgrade() -> None:
    """Remove performance indexes from artifacts table.

    Drops all three indexes added in the upgrade.
    """
    # Drop indexes in reverse order
    op.drop_index("ix_artifacts_analysis_version", table_name="artifacts")
    op.drop_index("ix_artifacts_download_count_desc", table_name="artifacts")
    op.drop_index("ix_artifacts_created_at_desc", table_name="artifacts")
