"""add_url_unique_constraint

Revision ID: 20251221_url_unique
Revises: f16597da5830
Create Date: 2025-12-21 00:00:00.000000

This migration enforces URL uniqueness in the analyses table by:
1. Removing duplicate URLs (keeping only the most recent analysis)
2. Converting the existing non-unique index to a unique constraint

Issue: #440
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '20251221_url_unique'
down_revision: Union[str, Sequence[str], None] = 'f16597da5830'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint to analyses.url column.

    This migration:
    1. Deletes duplicate analyses, keeping only the most recent by created_at
    2. Drops the existing non-unique index ix_analyses_url
    3. Creates a new unique index on the url column

    The deduplication query uses a CTE with ROW_NUMBER() to identify duplicates,
    ranking by created_at DESC (most recent first), and deletes all rows except
    the first (rank > 1).
    """
    # Step 1: Delete duplicate URLs, keeping only the most recent analysis
    # Using CTE with ROW_NUMBER() to identify duplicates
    op.execute(text("""
        WITH ranked_analyses AS (
            SELECT
                id,
                url,
                ROW_NUMBER() OVER (
                    PARTITION BY url
                    ORDER BY created_at DESC
                ) as rn
            FROM analyses
        )
        DELETE FROM analyses
        WHERE id IN (
            SELECT id
            FROM ranked_analyses
            WHERE rn > 1
        );
    """))

    # Step 2: Drop the existing non-unique index
    op.drop_index('ix_analyses_url', table_name='analyses')

    # Step 3: Create a new unique index on the url column
    op.create_index(
        'ix_analyses_url',
        'analyses',
        ['url'],
        unique=True
    )


def downgrade() -> None:
    """Remove unique constraint from analyses.url column.

    This reverts the migration by:
    1. Dropping the unique index
    2. Recreating the original non-unique index

    Note: This does NOT restore any deleted duplicate records.
    """
    # Drop the unique index
    op.drop_index('ix_analyses_url', table_name='analyses')

    # Recreate the original non-unique index
    op.create_index(
        'ix_analyses_url',
        'analyses',
        ['url'],
        unique=False
    )
