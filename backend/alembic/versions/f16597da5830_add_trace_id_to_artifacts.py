"""add_trace_id_to_artifacts

Revision ID: f16597da5830
Revises: 6993f3ce8114
Create Date: 2025-12-19 14:27:04.435494

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f16597da5830'
down_revision: Union[str, Sequence[str], None] = '6993f3ce8114'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trace_id column to artifacts table for Langfuse integration.

    The trace_id column allows artifacts to be linked to their Langfuse traces,
    enabling observability and debugging of the analysis pipeline.
    """
    # Add trace_id column (nullable for existing artifacts)
    op.add_column(
        "artifacts",
        sa.Column("trace_id", sa.String(length=255), nullable=True),
    )

    # Add index for fast lookups by trace_id
    op.create_index(
        "ix_artifacts_trace_id",
        "artifacts",
        ["trace_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove trace_id column from artifacts table."""
    # Drop index first
    op.drop_index("ix_artifacts_trace_id", table_name="artifacts")

    # Drop column
    op.drop_column("artifacts", "trace_id")
