"""Add status tracking columns to agent_findings table.

Revision ID: 20251223_agent_status
Revises: e4f4d69639db
Create Date: 2025-12-23 00:00:00.000000

Issue: Agent execution tracking - adds status, error_code, and error_message
columns to track agent execution outcomes (success, failed, skipped, timeout).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251223_agent_status"
down_revision: str | Sequence[str] | None = "e4f4d69639db"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add status tracking columns to agent_findings table.

    This migration adds three new columns to the agent_findings table:
    - status: Execution status ('success', 'failed', 'skipped', 'timeout')
    - error_code: Machine-readable error code (e.g., 'AGENT_NO_CODE', 'AGENT_TIMEOUT')
    - error_message: Human-readable error description
    """
    # Add status column with default 'success'
    op.add_column(
        "agent_findings",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="success",
            comment="Agent execution status: success, failed, skipped, timeout",
        ),
    )

    # Add error_code column for categorizing error types
    op.add_column(
        "agent_findings",
        sa.Column(
            "error_code",
            sa.String(50),
            nullable=True,
            comment="Machine-readable error code (e.g., 'AGENT_NO_CODE', 'AGENT_TIMEOUT')",
        ),
    )

    # Add error_message column for human-readable error descriptions
    op.add_column(
        "agent_findings",
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
            comment="Human-readable error description for debugging",
        ),
    )

    # Create index on status column for filtering by execution status
    op.create_index("ix_agent_findings_status", "agent_findings", ["status"])


def downgrade() -> None:
    """Remove status tracking columns from agent_findings table.

    This reverts the migration by dropping the index and columns.
    Note: This will permanently delete all status tracking data.
    """
    op.drop_index("ix_agent_findings_status", table_name="agent_findings")
    op.drop_column("agent_findings", "error_message")
    op.drop_column("agent_findings", "error_code")
    op.drop_column("agent_findings", "status")
