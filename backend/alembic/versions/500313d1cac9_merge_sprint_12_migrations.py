"""merge_sprint_12_migrations

Revision ID: 500313d1cac9
Revises: 20251210_add_pii_columns, c9d5e6f7a8b9
Create Date: 2025-12-11 21:03:38.399079

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "500313d1cac9"
down_revision: str | Sequence[str] | None = ("20251210_add_pii_columns", "c9d5e6f7a8b9")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
