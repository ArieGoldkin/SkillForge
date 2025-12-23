"""add_missing_agent_examples_columns

Revision ID: 5cfeff6daa44
Revises: c0a79c721014
Create Date: 2025-12-16 20:59:25.888473

Adds missing columns to agent_examples table:
- input_content_preview: First 2000 chars of input content for context
- source_analysis_id: Link back to originating analysis
- content_type: Classification (article, video, repo, etc.)
- difficulty_level: Difficulty classification (beginner, intermediate, advanced)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "5cfeff6daa44"
down_revision: Union[str, Sequence[str], None] = "c0a79c721014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing columns to agent_examples table."""
    # Add input_content_preview column
    op.add_column("agent_examples", sa.Column("input_content_preview", sa.Text(), nullable=True))

    # Add source_analysis_id column with optional FK to analyses table
    op.add_column(
        "agent_examples",
        sa.Column("source_analysis_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # Add content_type column with index
    op.add_column("agent_examples", sa.Column("content_type", sa.String(50), nullable=True))
    op.create_index("ix_agent_examples_content_type", "agent_examples", ["content_type"])

    # Add difficulty_level column
    op.add_column("agent_examples", sa.Column("difficulty_level", sa.String(20), nullable=True))


def downgrade() -> None:
    """Remove added columns from agent_examples table."""
    op.drop_column("agent_examples", "difficulty_level")
    op.drop_index("ix_agent_examples_content_type", table_name="agent_examples")
    op.drop_column("agent_examples", "content_type")
    op.drop_column("agent_examples", "source_analysis_id")
    op.drop_column("agent_examples", "input_content_preview")
