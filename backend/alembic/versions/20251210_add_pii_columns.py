"""Add PII columns to analysis_chunks table.

Revision ID: 20251210_add_pii_columns
Revises: 20251210_add_cascade_delete
Create Date: 2025-12-10

Issue #220: PII/Safety Guardrails

Adds columns to track PII detection metadata:
- pii_flag: Boolean indicating if PII was detected
- pii_types: JSONB array of detected PII types (e.g., ["email", "phone_us"])

IMPORTANT: These columns store detection metadata only, never actual PII values.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20251210_add_pii_columns"
down_revision = "20251210_add_cascade_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add PII tracking columns to analysis_chunks."""
    # Add pii_flag column with default False
    op.add_column(
        "analysis_chunks",
        sa.Column(
            "pii_flag",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
            comment="Whether PII was detected in this chunk (Issue #220)",
        ),
    )

    # Add pii_types JSONB column for storing detected PII type names
    op.add_column(
        "analysis_chunks",
        sa.Column(
            "pii_types",
            JSONB(),
            nullable=True,
            comment="Types of PII detected, e.g., ['email', 'phone_us'] (Issue #220)",
        ),
    )

    # Create partial index for efficient PII queries
    # Only indexes rows where pii_flag is true (sparse index)
    op.create_index(
        "ix_analysis_chunks_pii_flag",
        "analysis_chunks",
        ["pii_flag"],
        postgresql_where=sa.text("pii_flag = true"),
    )


def downgrade() -> None:
    """Remove PII tracking columns."""
    op.drop_index("ix_analysis_chunks_pii_flag", table_name="analysis_chunks")
    op.drop_column("analysis_chunks", "pii_types")
    op.drop_column("analysis_chunks", "pii_flag")
