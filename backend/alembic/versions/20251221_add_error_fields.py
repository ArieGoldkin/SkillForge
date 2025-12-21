"""Add error tracking fields to analyses table.

Revision ID: 20251221_error_fields
Revises: 20251221_url_unique
Create Date: 2025-12-21 00:00:00.000000

Issue #441: Failed extractions need proper error tracking.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251221_error_fields"
down_revision: str | Sequence[str] | None = "20251221_url_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add error tracking fields.

    This migration adds three new columns to the analyses table:
    - error_code: Machine-readable error code (e.g., 'EXTRACTION_FAILED')
    - error_message: Human-readable error message
    - failed_at_stage: Workflow stage where failure occurred
    """
    op.add_column("analyses", sa.Column("error_code", sa.String(50), nullable=True))
    op.add_column("analyses", sa.Column("error_message", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("failed_at_stage", sa.String(50), nullable=True))

    # Create index on error_code for filtering failed analyses
    op.create_index("ix_analyses_error_code", "analyses", ["error_code"])


def downgrade() -> None:
    """Remove error tracking fields.

    This reverts the migration by dropping the index and columns.
    Note: This will permanently delete all error tracking data.
    """
    op.drop_index("ix_analyses_error_code", table_name="analyses")
    op.drop_column("analyses", "failed_at_stage")
    op.drop_column("analyses", "error_message")
    op.drop_column("analyses", "error_code")
