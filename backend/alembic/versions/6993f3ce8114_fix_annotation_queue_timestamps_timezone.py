"""fix annotation_queue timestamps timezone

Revision ID: 6993f3ce8114
Revises: 800137e6a1b1
Create Date: 2025-12-19 14:05:25.515144

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6993f3ce8114"
down_revision: str | Sequence[str] | None = "800137e6a1b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert annotation_queue timestamp columns to timezone-aware.

    This fixes the asyncpg error: "can't subtract offset-naive and offset-aware datetimes"
    caused by Python code using datetime.now(UTC) with TIMESTAMP WITHOUT TIME ZONE columns.

    PostgreSQL automatically converts existing naive timestamps to UTC when changing
    the column type to TIMESTAMP WITH TIME ZONE.
    """
    # Convert created_at to TIMESTAMP WITH TIME ZONE
    op.alter_column(
        "annotation_queue",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=False,
    )

    # Convert reviewed_at to TIMESTAMP WITH TIME ZONE
    op.alter_column(
        "annotation_queue",
        "reviewed_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(timezone=False),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert annotation_queue timestamp columns to timezone-naive.

    WARNING: This will lose timezone information.
    PostgreSQL converts aware timestamps to naive by removing the timezone offset.
    """
    # Revert reviewed_at to TIMESTAMP WITHOUT TIME ZONE
    op.alter_column(
        "annotation_queue",
        "reviewed_at",
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )

    # Revert created_at to TIMESTAMP WITHOUT TIME ZONE
    op.alter_column(
        "annotation_queue",
        "created_at",
        type_=sa.DateTime(timezone=False),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
