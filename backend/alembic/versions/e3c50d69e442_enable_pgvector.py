"""Enable PGVector extension.

Revision ID: e3c50d69e442
Revises:
Create Date: 2025-11-21 10:58:42.455497

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3c50d69e442"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable PGVector extension for vector similarity search."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    """Disable PGVector extension."""
    op.execute("DROP EXTENSION IF EXISTS vector;")
