"""Enable LZ4 compression for raw_content column.

Revision ID: 20251222_lz4_compression
Revises: 20251221_error_fields
Create Date: 2025-12-22 00:00:00.000000

PostgreSQL 17 Feature: LZ4 TOAST Compression
- Faster compression/decompression (2-3x vs pglz)
- Better performance for text content
- Transparent to application layer

Issue: Optimize raw_content storage
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "20251222_lz4_compression"
down_revision: str | Sequence[str] | None = "20251221_error_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable LZ4 compression for raw_content column.

    Steps:
    1. Set storage to EXTENDED (required for compression)
    2. Set compression method to lz4
    3. Existing data will be recompressed on next UPDATE
    """
    # Step 1: Set storage to EXTENDED (allows compression)
    # PLAIN = no compression, EXTENDED = TOAST with compression
    op.execute(
        text("""
            ALTER TABLE analyses 
            ALTER COLUMN raw_content 
            SET STORAGE EXTENDED;
        """)
    )

    # Step 2: Set compression method to lz4
    # Requires PostgreSQL 14+ (we're on 17, so safe)
    op.execute(
        text("""
            ALTER TABLE analyses 
            ALTER COLUMN raw_content 
            SET COMPRESSION lz4;
        """)
    )

    # Step 3: Force recompression of existing data
    # This updates all rows, triggering compression
    # Note: This is optional but recommended for immediate benefits
    op.execute(
        text("""
            UPDATE analyses 
            SET raw_content = raw_content 
            WHERE raw_content IS NOT NULL;
        """)
    )


def downgrade() -> None:
    """Revert to default pglz compression.

    Steps:
    1. Reset compression to default (pglz)
    2. Keep EXTENDED storage (still allows compression)
    """
    # Reset to default compression (pglz)
    op.execute(
        text("""
            ALTER TABLE analyses 
            ALTER COLUMN raw_content 
            SET COMPRESSION DEFAULT;
        """)
    )

    # Optional: Reset storage to PLAIN if you want no compression
    # We keep EXTENDED to maintain compression capability
    # op.execute(text("""
    #     ALTER TABLE analyses 
    #     ALTER COLUMN raw_content 
    #     SET STORAGE PLAIN;
    # """))
