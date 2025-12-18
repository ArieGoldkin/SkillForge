"""Backfill content_tsvector for analysis_chunks and add trigger.

Revision ID: 20251218_backfill
Revises: 5cfeff6daa44
Create Date: 2025-12-18

This migration:
- Backfills content_tsvector for all existing analysis_chunks (411 rows)
- Creates a trigger to auto-populate content_tsvector on INSERT/UPDATE
- Creates a GIN index for fast full-text search on chunks

Issue #299-304: Retrieval Quality Initiative - Phase 2
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251218_backfill"
down_revision: str | Sequence[str] | None = "5cfeff6daa44"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill content_tsvector and create trigger for analysis_chunks."""
    # 1. Create trigger function to auto-update content_tsvector
    # Uses the 'snippet' column which contains the chunk text content
    op.execute(
        text("""
            CREATE OR REPLACE FUNCTION chunks_content_tsvector_update() RETURNS trigger AS $$
            BEGIN
              NEW.content_tsvector := to_tsvector('english', COALESCE(NEW.snippet, ''));
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
    )

    # 2. Create trigger on analysis_chunks table
    op.execute(
        text("""
            CREATE TRIGGER chunks_content_tsvector_trigger
            BEFORE INSERT OR UPDATE OF snippet ON analysis_chunks
            FOR EACH ROW EXECUTE FUNCTION chunks_content_tsvector_update();
        """)
    )

    # 3. Backfill content_tsvector for ALL existing rows
    op.execute(
        text("""
            UPDATE analysis_chunks
            SET content_tsvector = to_tsvector('english', COALESCE(snippet, ''))
            WHERE content_tsvector IS NULL
               OR content_tsvector = ''::tsvector;
        """)
    )

    # 4. Create GIN index for fast full-text search (if not exists)
    # Check and create only if missing to avoid errors
    op.execute(
        text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE indexname = 'ix_analysis_chunks_content_tsvector'
                ) THEN
                    CREATE INDEX ix_analysis_chunks_content_tsvector
                    ON analysis_chunks
                    USING GIN (content_tsvector);
                END IF;
            END;
            $$;
        """)
    )


def downgrade() -> None:
    """Remove tsvector trigger and clear content_tsvector."""
    # Drop GIN index
    op.execute(
        text("""
            DROP INDEX IF EXISTS ix_analysis_chunks_content_tsvector;
        """)
    )

    # Drop trigger
    op.execute(
        text("""
            DROP TRIGGER IF EXISTS chunks_content_tsvector_trigger ON analysis_chunks;
        """)
    )

    # Drop trigger function
    op.execute(
        text("""
            DROP FUNCTION IF EXISTS chunks_content_tsvector_update();
        """)
    )

    # Note: We don't clear content_tsvector as the column may be used elsewhere
    # Just remove the auto-population mechanism
