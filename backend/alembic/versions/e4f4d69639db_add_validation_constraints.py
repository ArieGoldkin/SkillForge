"""Add validation constraints to analyses table.

Revision ID: e4f4d69639db
Revises: 20251222_lz4_compression
Create Date: 2025-12-22 19:40:00.000000

Database-level validation constraints for data integrity:
- Complete analyses must have raw_content
- Embeddings must be exactly 1536 dimensions
- Complete analyses must have extraction_metadata

Issue: Data Validation Architecture (Phase 6)
"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4f4d69639db"
down_revision: str | Sequence[str] | None = "20251222_lz4_compression"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add validation constraints to analyses table.

    Constraints:
    1. Complete analyses must have raw_content (NOT NULL)
    2. Embeddings must be exactly 1536 dimensions when present
    3. Complete analyses must have extraction_metadata (NOT NULL)

    Steps:
    1. Fix existing data that violates constraints (set status to 'failed' if incomplete)
    2. Add constraints
    """
    # Step 1: Fix existing data - mark incomplete 'complete' records as 'failed'
    op.execute(
        text(
            """
            UPDATE analyses
            SET status = 'failed',
                error_code = 'DATA_VALIDATION_FAILED',
                error_message = 'Analysis marked as complete but missing required data (migration fix)'
            WHERE status = 'complete'
            AND (raw_content IS NULL OR extraction_metadata IS NULL)
            """
        )
    )

    # Step 2: Fix embeddings with wrong dimensions
    # Note: We can't easily check vector dimensions in SQL without casting
    # So we'll let the constraint handle this - invalid embeddings will be caught
    # by the constraint when trying to insert/update

    # Constraint 1: Complete analyses must have raw_content
    op.execute(
        text(
            """
            ALTER TABLE analyses
            ADD CONSTRAINT check_complete_has_content
            CHECK (status != 'complete' OR raw_content IS NOT NULL)
            """
        )
    )

    # Constraint 2: Embeddings must be 1536 dimensions when present
    # pgvector provides vector_dims() function to check dimensions
    op.execute(
        text(
            """
            ALTER TABLE analyses
            ADD CONSTRAINT check_embedding_dimensions
            CHECK (
                content_embedding IS NULL
                OR vector_dims(content_embedding) = 1536
            )
            """
        )
    )

    # Constraint 3: Complete analyses must have extraction_metadata
    op.execute(
        text(
            """
            ALTER TABLE analyses
            ADD CONSTRAINT check_complete_has_metadata
            CHECK (status != 'complete' OR extraction_metadata IS NOT NULL)
            """
        )
    )


def downgrade() -> None:
    """Remove validation constraints from analyses table."""
    op.drop_constraint("check_complete_has_content", "analyses", type_="check")
    op.drop_constraint("check_embedding_dimensions", "analyses", type_="check")
    op.drop_constraint("check_complete_has_metadata", "analyses", type_="check")
