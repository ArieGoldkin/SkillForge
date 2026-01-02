"""Migrate UUID defaults to server-generated uuidv7

Revision ID: 79748ad4c1f2
Revises: 20251226_artifact_indexes
Create Date: 2026-01-02 19:23:14.107722

This migration updates UUID primary key defaults from Python uuid.uuid4()
to PostgreSQL 18 native uuidv7() for all models:

- analyses.id
- analysis_chunks.id
- agent_findings.id
- agent_memories.id
- analysis_progress.id
- artifacts.id
- tutoring_sessions.id
- tutoring_messages.id
- agent_examples.id

Benefits of UUID v7 (RFC 9562):
- Time-ordered: 57% faster B-tree index insertions
- Sortable by creation time: Natural ordering without extra timestamp
- 38% smaller index pages: Better cache efficiency
- Cluster-friendly: Sequential inserts reduce page splits

PostgreSQL 18 provides native uuidv7() function - no extension needed.

NOTE: For FRESH START deployments (new databases), this migration is a no-op
since the schema is created with correct server_default values.

For EXISTING databases, you would need to ALTER DEFAULT on each column:
    ALTER TABLE analyses ALTER COLUMN id SET DEFAULT uuidv7();
However, existing UUIDs remain valid - only new rows use uuidv7().
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "79748ad4c1f2"
down_revision: str | Sequence[str] | None = "20251226_artifact_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables with UUID primary keys using uuidv7()
UUID_TABLES = [
    "analyses",
    "analysis_chunks",
    "agent_findings",
    "agent_memories",
    "analysis_progress",
    "artifacts",
    "tutoring_sessions",
    "tutoring_messages",
    "agent_examples",
]


def upgrade() -> None:
    """Upgrade UUID defaults to server-generated uuidv7().

    For fresh databases, no action needed - schema created with correct defaults.
    For existing databases, update the default constraint on id columns.
    """
    for table_name in UUID_TABLES:
        # Update default to use PostgreSQL 18 native uuidv7()
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN id SET DEFAULT uuidv7()")


def downgrade() -> None:
    """Downgrade to Python-generated UUIDs (no server default).

    Removes server default - Python uuid.uuid4() handles generation.
    """
    for table_name in UUID_TABLES:
        # Remove server default (Python uuid.uuid4 handles it)
        op.execute(f"ALTER TABLE {table_name} ALTER COLUMN id DROP DEFAULT")
