"""Harden embedding pipeline with indexes and constraints.

This migration implements Issue #215 requirements:
- HNSW index on vector column for fast semantic search
- Full-text search with tsvector + GIN index
- Hash-based deduplication index
- Composite indexes for common query patterns
- Check constraints for data integrity
- Telemetry columns for observability

Revision ID: 20251210_harden
Revises: 20251209120000
Create Date: 2025-12-10 00:00:00.000000

"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251210_harden"
down_revision: str | Sequence[str] | None = "20251209120000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply schema hardening for embedding pipeline."""
    # ============================================================================
    # PHASE 1: Add new columns
    # ============================================================================

    # Add full-text search vector (will be populated by trigger)
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD COLUMN IF NOT EXISTS content_tsvector TSVECTOR
        """)
    )

    # Add telemetry columns for observability
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD COLUMN IF NOT EXISTS token_count INTEGER,
            ADD COLUMN IF NOT EXISTS embedding_latency_ms FLOAT,
            ADD COLUMN IF NOT EXISTS was_truncated BOOLEAN DEFAULT FALSE
        """)
    )

    # ============================================================================
    # PHASE 2: Create trigger for auto-updating content_tsvector
    # ============================================================================

    # Create trigger function
    op.execute(
        text("""
            CREATE OR REPLACE FUNCTION analysis_chunks_tsvector_update() RETURNS trigger AS $$
            BEGIN
              NEW.content_tsvector :=
                setweight(to_tsvector('english', COALESCE(NEW.section_title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.snippet, '')), 'B');
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
    )

    # Create trigger on analysis_chunks table
    op.execute(
        text("""
            CREATE TRIGGER analysis_chunks_tsvector_trigger
            BEFORE INSERT OR UPDATE OF section_title, snippet ON analysis_chunks
            FOR EACH ROW EXECUTE FUNCTION analysis_chunks_tsvector_update();
        """)
    )

    # ============================================================================
    # PHASE 3: Backfill content_tsvector for existing rows
    # ============================================================================

    op.execute(
        text("""
            UPDATE analysis_chunks SET content_tsvector =
              setweight(to_tsvector('english', COALESCE(section_title, '')), 'A') ||
              setweight(to_tsvector('english', COALESCE(snippet, '')), 'B')
            WHERE content_tsvector IS NULL;
        """)
    )

    # ============================================================================
    # PHASE 4: Create indexes
    # ============================================================================
    # NOTE: Not using CONCURRENTLY as it cannot run inside transaction blocks.
    # For production with existing data, consider running these manually outside Alembic.

    # HNSW index for vector similarity search (semantic search)
    # Using cosine distance operator for normalized embeddings
    # Parameters: m=16 (connections per layer), ef_construction=64 (build quality)
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_analysis_chunks_vector_hnsw
            ON analysis_chunks
            USING hnsw (vector vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)
    )

    # GIN index for full-text search (keyword search)
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_analysis_chunks_content_tsvector
            ON analysis_chunks
            USING GIN (content_tsvector);
        """)
    )

    # Hash-based deduplication index (includes model + version)
    # Non-unique to allow same content with different models
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_analysis_chunks_hash_model
            ON analysis_chunks (hash, model, model_version);
        """)
    )

    # Single-column hash index for fast cache lookups
    # Note: This is created by SQLAlchemy model (index=True), but ensure it exists
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_analysis_chunks_hash
            ON analysis_chunks (hash);
        """)
    )

    # Composite index for hierarchical search (analysis + granularity)
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_analysis_chunks_analysis_granularity
            ON analysis_chunks (analysis_id, granularity);
        """)
    )

    # Composite index for filtered search (content_type + created_at)
    # Partial index: only where content_type is not null
    op.execute(
        text("""
            CREATE INDEX IF NOT EXISTS ix_analysis_chunks_content_type_created
            ON analysis_chunks (content_type, created_at DESC)
            WHERE content_type IS NOT NULL;
        """)
    )

    # ============================================================================
    # PHASE 5: Add check constraints for data integrity
    # ============================================================================

    # Ensure granularity is one of the valid values
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD CONSTRAINT IF NOT EXISTS chk_granularity
            CHECK (granularity IN ('coarse', 'fine', 'summary'));
        """)
    )

    # Ensure chunk_idx is non-negative
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD CONSTRAINT IF NOT EXISTS chk_chunk_idx_positive
            CHECK (chunk_idx >= 0);
        """)
    )

    # Ensure chunk_total is positive
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD CONSTRAINT IF NOT EXISTS chk_chunk_total_positive
            CHECK (chunk_total > 0);
        """)
    )

    # Ensure chunk_idx < chunk_total (logical consistency)
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD CONSTRAINT IF NOT EXISTS chk_chunk_idx_lt_total
            CHECK (chunk_idx < chunk_total);
        """)
    )

    # ============================================================================
    # PHASE 6: Update foreign key constraint to cascade deletes
    # ============================================================================

    # Drop existing foreign key constraint
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            DROP CONSTRAINT IF EXISTS analysis_chunks_analysis_id_fkey;
        """)
    )

    # Add foreign key constraint with CASCADE delete
    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD CONSTRAINT analysis_chunks_analysis_id_fkey
            FOREIGN KEY (analysis_id) REFERENCES analyses(id)
            ON DELETE CASCADE;
        """)
    )

    # ============================================================================
    # PHASE 7: Create trigger for auto-updating updated_at
    # ============================================================================

    # Create reusable trigger function if it doesn't exist
    op.execute(
        text("""
            CREATE OR REPLACE FUNCTION update_updated_at_column() RETURNS trigger AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
    )

    # Create trigger on analysis_chunks
    op.execute(
        text("""
            DROP TRIGGER IF EXISTS update_analysis_chunks_updated_at ON analysis_chunks;
        """)
    )

    op.execute(
        text("""
            CREATE TRIGGER update_analysis_chunks_updated_at
            BEFORE UPDATE ON analysis_chunks
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)
    )


def downgrade() -> None:
    """Rollback schema hardening changes."""
    # ============================================================================
    # Remove triggers
    # ============================================================================

    op.execute(
        text("""
            DROP TRIGGER IF EXISTS update_analysis_chunks_updated_at ON analysis_chunks;
        """)
    )

    op.execute(
        text("""
            DROP TRIGGER IF EXISTS analysis_chunks_tsvector_trigger ON analysis_chunks;
        """)
    )

    op.execute(
        text("""
            DROP FUNCTION IF EXISTS analysis_chunks_tsvector_update();
        """)
    )

    # Note: Keep update_updated_at_column() function as it may be used by other tables

    # ============================================================================
    # Remove foreign key constraint and restore original
    # ============================================================================

    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            DROP CONSTRAINT IF EXISTS analysis_chunks_analysis_id_fkey;
        """)
    )

    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            ADD CONSTRAINT analysis_chunks_analysis_id_fkey
            FOREIGN KEY (analysis_id) REFERENCES analyses(id);
        """)
    )

    # ============================================================================
    # Remove check constraints
    # ============================================================================

    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            DROP CONSTRAINT IF EXISTS chk_granularity,
            DROP CONSTRAINT IF EXISTS chk_chunk_idx_positive,
            DROP CONSTRAINT IF EXISTS chk_chunk_total_positive,
            DROP CONSTRAINT IF EXISTS chk_chunk_idx_lt_total;
        """)
    )

    # ============================================================================
    # Remove indexes
    # ============================================================================

    op.execute(text("DROP INDEX IF EXISTS ix_analysis_chunks_content_type_created"))
    op.execute(text("DROP INDEX IF EXISTS ix_analysis_chunks_analysis_granularity"))
    op.execute(text("DROP INDEX IF EXISTS ix_analysis_chunks_hash"))
    op.execute(text("DROP INDEX IF EXISTS ix_analysis_chunks_hash_model"))
    op.execute(text("DROP INDEX IF EXISTS ix_analysis_chunks_content_tsvector"))
    op.execute(text("DROP INDEX IF EXISTS ix_analysis_chunks_vector_hnsw"))

    # ============================================================================
    # Remove columns
    # ============================================================================

    op.execute(
        text("""
            ALTER TABLE analysis_chunks
            DROP COLUMN IF EXISTS content_tsvector,
            DROP COLUMN IF EXISTS token_count,
            DROP COLUMN IF EXISTS embedding_latency_ms,
            DROP COLUMN IF EXISTS was_truncated;
        """)
    )
