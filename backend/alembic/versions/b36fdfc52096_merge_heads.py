"""merge_heads

Revision ID: b36fdfc52096
Revises: 20251210_add_pii_columns, c9d5e6f7a8b9
Create Date: 2025-12-11 21:18:21.696932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b36fdfc52096'
down_revision: Union[str, Sequence[str], None] = ('20251210_add_pii_columns', 'c9d5e6f7a8b9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
