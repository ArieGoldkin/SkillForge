"""Migrate embeddings from Ollama (768) to OpenAI (1536).

Revision ID: 1735171200000
Revises: 637794773190
Create Date: 2025-11-25

This migration changes the content_embedding column type from Vector(768) to Vector(1536).
pgvector will handle dimension conversion automatically during the type change.
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1735171200000"
down_revision: str | Sequence[str] | None = "637794773190"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Migrate to OpenAI embeddings (1536 dimensions).

    Changes column type from Vector(768) to Vector(1536).
    Existing embeddings are set to NULL since dimensions are incompatible.
    """
    # Step 1: Set all existing embeddings to NULL (incompatible dimensions)
    op.execute(
        text("""
            UPDATE analyses
            SET content_embedding = NULL
            WHERE content_embedding IS NOT NULL
        """)
    )

    # Step 2: Change column type to Vector(1536)
    op.execute(
        text("""
            ALTER TABLE analyses
            ALTER COLUMN content_embedding TYPE vector(1536)
            USING NULL::vector(1536)
        """)
    )


def downgrade() -> None:
    """Revert to Ollama embeddings (768 dimensions).

    Changes column type from Vector(1536) back to Vector(768).
    Existing embeddings are set to NULL since dimensions are incompatible.
    """
    # Step 1: Set all existing embeddings to NULL (incompatible dimensions)
    op.execute(
        text("""
            UPDATE analyses
            SET content_embedding = NULL
            WHERE content_embedding IS NOT NULL
        """)
    )

    # Step 2: Change column type back to Vector(768)
    op.execute(
        text("""
            ALTER TABLE analyses
            ALTER COLUMN content_embedding TYPE vector(768)
            USING NULL::vector(768)
        """)
    )
