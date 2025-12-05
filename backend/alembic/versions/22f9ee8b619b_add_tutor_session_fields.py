"""Add tutor session fields.

Revision ID: 22f9ee8b619b
Revises: 1735171200000
Create Date: 2025-11-29 12:43:35.015976

Adds missing fields to tutoring_sessions table for tutor agent workflow:
- syllabus (JSONB): Generated curriculum structure
- current_section (INT): Current section index (0-based)
- current_lesson (INT): Current lesson index (0-based)
- current_phase (VARCHAR): Current workflow phase
- user_level (VARCHAR): User's skill level
- understanding_scores (JSONB): Per-concept understanding scores
- conversation_summary (TEXT): Summarized conversation history

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "22f9ee8b619b"
down_revision: str | Sequence[str] | None = "1735171200000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add tutor session fields to tutoring_sessions table."""
    # Add syllabus field (JSONB, nullable)
    op.add_column(
        "tutoring_sessions",
        sa.Column("syllabus", JSONB(), nullable=True),
    )

    # Add current_section field (INT, default 0, not null)
    op.add_column(
        "tutoring_sessions",
        sa.Column("current_section", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add current_lesson field (INT, default 0, not null)
    op.add_column(
        "tutoring_sessions",
        sa.Column("current_lesson", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add current_phase field (VARCHAR(50), default 'syllabus_generation', not null)
    op.add_column(
        "tutoring_sessions",
        sa.Column(
            "current_phase",
            sa.String(50),
            nullable=False,
            server_default="syllabus_generation",
        ),
    )

    # Add user_level field (VARCHAR(20), default 'intermediate', not null)
    op.add_column(
        "tutoring_sessions",
        sa.Column(
            "user_level",
            sa.String(20),
            nullable=False,
            server_default="intermediate",
        ),
    )

    # Add understanding_scores field (JSONB, default '{}', not null)
    op.add_column(
        "tutoring_sessions",
        sa.Column(
            "understanding_scores",
            JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )

    # Add conversation_summary field (TEXT, nullable)
    op.add_column(
        "tutoring_sessions",
        sa.Column("conversation_summary", sa.Text(), nullable=True),
    )

    # Create index on current_phase for querying active sessions by phase
    op.create_index(
        "ix_tutoring_sessions_current_phase",
        "tutoring_sessions",
        ["current_phase"],
    )


def downgrade() -> None:
    """Remove tutor session fields from tutoring_sessions table."""
    # Drop index first
    op.drop_index("ix_tutoring_sessions_current_phase", table_name="tutoring_sessions")

    # Drop columns in reverse order
    op.drop_column("tutoring_sessions", "conversation_summary")
    op.drop_column("tutoring_sessions", "understanding_scores")
    op.drop_column("tutoring_sessions", "user_level")
    op.drop_column("tutoring_sessions", "current_phase")
    op.drop_column("tutoring_sessions", "current_lesson")
    op.drop_column("tutoring_sessions", "current_section")
    op.drop_column("tutoring_sessions", "syllabus")
