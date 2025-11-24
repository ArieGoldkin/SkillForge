"""Tests for database migrations."""

import pytest
from sqlalchemy import text

from app.db.base import Base
from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_vector_extension_exists(requires_database, reset_engine_connections):
    """Test PGVector extension is enabled in database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        extension = result.scalar_one_or_none()
        assert extension == "vector"


@pytest.mark.asyncio
async def test_all_tables_exist(requires_database, reset_engine_connections):
    """Test all 6 tables exist in database."""
    expected_tables = [
        "analyses",
        "agent_findings",
        "artifacts",
        "tutoring_sessions",
        "tutoring_messages",
        "analysis_progress",
    ]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
        )
        existing_tables = [row[0] for row in result.fetchall()]

        for table in expected_tables:
            assert table in existing_tables, f"Table {table} not found in database"


@pytest.mark.asyncio
async def test_analyses_table_columns(requires_database, reset_engine_connections):
    """Test analyses table has all required columns."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'analyses'
                ORDER BY column_name
                """
            )
        )
        columns = {row[0]: (row[1], row[2]) for row in result.fetchall()}

        assert "id" in columns
        assert "url" in columns
        assert "content_type" in columns
        assert "status" in columns
        assert "created_at" in columns
        assert "updated_at" in columns
        assert columns["url"][1] == "NO"  # NOT NULL
        assert columns["content_type"][1] == "NO"  # NOT NULL


@pytest.mark.asyncio
async def test_analyses_table_has_vector_column(requires_database, reset_engine_connections):
    """Test analyses table has vector embedding column."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT column_name, udt_name
                FROM information_schema.columns
                WHERE table_name = 'analyses' AND column_name = 'content_embedding'
                """
            )
        )
        row = result.fetchone()
        assert row is not None
        assert row[1] == "vector"  # Vector type


@pytest.mark.asyncio
async def test_foreign_key_constraints_exist(requires_database, reset_engine_connections):
    """Test all foreign key constraints are created correctly."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    conname as constraint_name,
                    conrelid::regclass as table_name,
                    confrelid::regclass as foreign_table
                FROM pg_constraint
                WHERE contype = 'f'
                ORDER BY conrelid::regclass::text
                """
            )
        )
        foreign_keys = [(row[0], str(row[1]), str(row[2])) for row in result.fetchall()]

        # Verify expected foreign keys exist
        fk_tables = {fk[1]: fk[2] for fk in foreign_keys}

        assert "agent_findings" in fk_tables
        assert fk_tables["agent_findings"] == "analyses"

        assert "artifacts" in fk_tables
        assert fk_tables["artifacts"] == "analyses"

        assert "tutoring_sessions" in fk_tables
        assert fk_tables["tutoring_sessions"] == "analyses"

        assert "tutoring_messages" in fk_tables
        assert fk_tables["tutoring_messages"] == "tutoring_sessions"

        assert "analysis_progress" in fk_tables
        assert fk_tables["analysis_progress"] == "analyses"


@pytest.mark.asyncio
async def test_indexes_exist(requires_database, reset_engine_connections):
    """Test all expected indexes are created."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                ORDER BY indexname
                """
            )
        )
        indexes = [row[0] for row in result.fetchall()]

        # Check for key indexes
        expected_indexes = [
            "ix_analyses_url",
            "ix_analyses_status",
            "ix_agent_findings_analysis_id",
            "ix_artifacts_analysis_id",
        ]

        for index in expected_indexes:
            assert any(index in idx for idx in indexes), f"Index {index} not found"


@pytest.mark.asyncio
async def test_cascade_delete_foreign_keys(requires_database, reset_engine_connections):
    """Test foreign keys have CASCADE delete where appropriate."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    conname,
                    conrelid::regclass as table_name,
                    pg_get_constraintdef(oid) as constraint_def
                FROM pg_constraint
                WHERE contype = 'f' AND conrelid::regclass::text IN (
                    'agent_findings', 'artifacts', 'analysis_progress'
                )
                """
            )
        )
        constraints = result.fetchall()

        for constraint_name, table_name, constraint_def in constraints:
            assert "ON DELETE CASCADE" in constraint_def, (
                f"Foreign key {constraint_name} on {table_name} should have CASCADE delete"
            )


@pytest.mark.asyncio
async def test_set_null_delete_foreign_key(requires_database, reset_engine_connections):
    """Test tutoring_sessions foreign key has SET NULL delete."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE contype = 'f'
                  AND conrelid::regclass::text = 'tutoring_sessions'
                  AND confrelid::regclass::text = 'analyses'
                """
            )
        )
        constraint_def = result.scalar_one_or_none()

        assert constraint_def is not None
        assert "ON DELETE SET NULL" in constraint_def


@pytest.mark.asyncio
async def test_models_match_schema(requires_database, reset_engine_connections):
    """Test SQLAlchemy models match database schema."""
    async with AsyncSessionLocal() as session:
        # Get all model tables
        tables = Base.metadata.tables

        # Verify each model table exists in database
        for table_name in tables.keys():
            result = await session.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_name = :table_name
                    """
                ),
                {"table_name": table_name},
            )
            exists = result.scalar() > 0
            assert exists, f"Table {table_name} from models does not exist in database"


@pytest.mark.asyncio
async def test_uuid_primary_keys(requires_database, reset_engine_connections):
    """Test all tables use UUID primary keys."""
    async with AsyncSessionLocal() as session:
        tables = [
            "analyses",
            "agent_findings",
            "artifacts",
            "tutoring_sessions",
            "tutoring_messages",
            "analysis_progress",
        ]

        for table in tables:
            result = await session.execute(
                text(
                    """
                    SELECT data_type
                    FROM information_schema.columns
                    WHERE table_name = :table AND column_name = 'id'
                    """
                ),
                {"table": table},
            )
            data_type = result.scalar_one_or_none()
            assert data_type == "uuid", f"Table {table} primary key should be UUID, got {data_type}"
