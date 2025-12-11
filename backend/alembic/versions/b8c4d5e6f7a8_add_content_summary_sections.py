"""Add content_summary and content_sections columns for Handle Pattern.

Revision ID: b8c4d5e6f7a8
Revises: 22f9ee8b619b
Create Date: 2025-12-10 20:00:00.000000

Issue #244: Handle Pattern for Large Payloads
Sprint 11: Context Engineering

These columns enable the Handle Pattern from Google ADK's Context Engineering:
- content_summary: LLM-generated summary (~500 tokens) always available in state
- content_sections: JSONB with code blocks, headings, word count for partial loading
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b8c4d5e6f7a8"
down_revision: str | None = "22f9ee8b619b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add content_summary and content_sections to analyses table."""
    # Add content_summary column for always-available summaries
    op.add_column(
        "analyses",
        sa.Column(
            "content_summary",
            sa.Text(),
            nullable=True,
            comment="LLM-generated summary for Handle Pattern (~500 tokens)",
        ),
    )

    # Add content_sections JSONB column for section metadata
    op.add_column(
        "analyses",
        sa.Column(
            "content_sections",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
            comment="Section metadata: code_blocks, headings, word_count",
        ),
    )


def downgrade() -> None:
    """Remove content_summary and content_sections columns."""
    op.drop_column("analyses", "content_sections")
    op.drop_column("analyses", "content_summary")
