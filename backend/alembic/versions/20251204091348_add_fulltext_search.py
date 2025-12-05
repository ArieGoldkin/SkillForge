"""Add full-text search capabilities to analyses table.

Revision ID: 20251204091348
Revises: 22f9ee8b619b
Create Date: 2025-12-04 09:13:48

This migration adds:
- search_vector (TSVECTOR): Full-text search vector for title, url, raw_content
- GIN index for fast full-text search
- HNSW index for vector similarity search (CRITICAL - previously missing!)
- Trigger function to auto-update search_vector on INSERT/UPDATE
- Partial index for completed analyses
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251204091348"
down_revision: str | Sequence[str] | None = "22f9ee8b619b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add full-text search capabilities to analyses table."""
    # 1. Add search_vector column (TSVECTOR, nullable for existing rows)
    op.execute(
        text("""
            ALTER TABLE analyses
            ADD COLUMN search_vector TSVECTOR
        """)
    )

    # 2. Create trigger function to auto-update search_vector
    op.execute(
        text("""
            CREATE OR REPLACE FUNCTION analyses_search_vector_update() RETURNS trigger AS $$
            BEGIN
              NEW.search_vector :=
                setweight(to_tsvector('english', COALESCE(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(NEW.url, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(NEW.raw_content, '')), 'C');
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
    )

    # 3. Create trigger on analyses table
    op.execute(
        text("""
            CREATE TRIGGER analyses_search_vector_trigger
            BEFORE INSERT OR UPDATE OF title, url, raw_content ON analyses
            FOR EACH ROW EXECUTE FUNCTION analyses_search_vector_update();
        """)
    )

    # 4. Populate search_vector for existing rows
    op.execute(
        text("""
            UPDATE analyses SET search_vector =
              setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
              setweight(to_tsvector('english', COALESCE(url, '')), 'B') ||
              setweight(to_tsvector('english', COALESCE(raw_content, '')), 'C');
        """)
    )

    # 5. Create GIN index for full-text search
    op.create_index(
        "ix_analyses_search_vector", "analyses", ["search_vector"], postgresql_using="gin"
    )

    # 6. Create HNSW index for vector similarity search (CRITICAL - previously missing!)
    # Using vector_cosine_ops for cosine similarity
    # m=16: number of connections per layer (good balance of speed/accuracy)
    # ef_construction=64: size of dynamic candidate list during index construction
    op.execute(
        text("""
            CREATE INDEX ix_analyses_embedding_hnsw ON analyses
            USING hnsw (content_embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
        """)
    )

    # 7. Create partial index for completed analyses (optimizes common queries)
    op.create_index(
        "ix_analyses_completed",
        "analyses",
        ["created_at"],
        postgresql_where=text("status = 'complete'"),
    )


def downgrade() -> None:
    """Remove full-text search capabilities from analyses table."""
    # Drop indexes (reverse order)
    op.drop_index("ix_analyses_completed", table_name="analyses")
    op.drop_index("ix_analyses_embedding_hnsw", table_name="analyses")
    op.drop_index("ix_analyses_search_vector", table_name="analyses")

    # Drop trigger
    op.execute(
        text("""
            DROP TRIGGER IF EXISTS analyses_search_vector_trigger ON analyses;
        """)
    )

    # Drop trigger function
    op.execute(
        text("""
            DROP FUNCTION IF EXISTS analyses_search_vector_update();
        """)
    )

    # Drop search_vector column
    op.execute(
        text("""
            ALTER TABLE analyses
            DROP COLUMN IF EXISTS search_vector;
        """)
    )
