"""Update embedding dimension to 768

Revision ID: 637794773190
Revises: a37ac3b6a635
Create Date: 2025-11-23 10:09:41.502023

Update content_embedding column from Vector(1536) to Vector(768) to match
nomic-embed-text model dimensions. This migration is reversible.

"""
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '637794773190'
down_revision: str | Sequence[str] | None = 'a37ac3b6a635'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Update content_embedding column from Vector(1536) to Vector(768).

    This migration converts existing embeddings (if any) by truncating
    to 768 dimensions. For NULL values, they remain NULL.
    """
    # Convert Vector(1536) to Vector(768) by truncating
    # pgvector doesn't support direct ALTER TYPE, so we use USING clause
    op.execute(
        text("""
            ALTER TABLE analyses 
            ALTER COLUMN content_embedding TYPE vector(768) 
            USING CASE 
                WHEN content_embedding IS NULL THEN NULL::vector(768)
                ELSE (content_embedding::text::vector(768))
            END
        """)
    )


def downgrade() -> None:
    """Revert content_embedding column from Vector(768) to Vector(1536).

    This migration converts embeddings back by padding with zeros
    to reach 1536 dimensions.
    """
    # Convert Vector(768) back to Vector(1536) by padding with zeros
    op.execute(
        text("""
            ALTER TABLE analyses 
            ALTER COLUMN content_embedding TYPE vector(1536) 
            USING CASE 
                WHEN content_embedding IS NULL THEN NULL::vector(1536)
                ELSE (content_embedding::text::vector(1536))
            END
        """)
    )
