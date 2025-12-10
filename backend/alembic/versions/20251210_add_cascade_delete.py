"""add cascade delete for analysis_chunks

Revision ID: 20251210_cascade
Revises: 20251210_harden_embedding_pipeline
Create Date: 2025-12-10 12:00:00.000000

This migration adds ON DELETE CASCADE to the analysis_id foreign key
in analysis_chunks table. This ensures that when an analysis is deleted,
all its chunks are automatically deleted.

This is critical for:
- TTL-based cleanup (draft analyses expiration)
- Manual analysis deletion
- Data consistency
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251210_cascade"
down_revision = "20251210_harden_embedding_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add ON DELETE CASCADE to analysis_chunks.analysis_id foreign key."""
    # Drop existing foreign key constraint
    op.drop_constraint(
        "analysis_chunks_analysis_id_fkey",
        "analysis_chunks",
        type_="foreignkey",
    )

    # Re-create with ON DELETE CASCADE
    op.create_foreign_key(
        "analysis_chunks_analysis_id_fkey",
        "analysis_chunks",
        "analyses",
        ["analysis_id"],
        ["id"],
        ondelete="CASCADE",  # Add cascade delete
    )


def downgrade() -> None:
    """Remove ON DELETE CASCADE from analysis_chunks.analysis_id foreign key."""
    # Drop foreign key with CASCADE
    op.drop_constraint(
        "analysis_chunks_analysis_id_fkey",
        "analysis_chunks",
        type_="foreignkey",
    )

    # Re-create without ON DELETE CASCADE (original state)
    op.create_foreign_key(
        "analysis_chunks_analysis_id_fkey",
        "analysis_chunks",
        "analyses",
        ["analysis_id"],
        ["id"],
    )
