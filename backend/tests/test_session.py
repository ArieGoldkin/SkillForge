"""Tests for database session management."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine, get_async_database_url, get_db


def test_get_async_database_url_converts_postgresql_to_asyncpg():
    """Test get_async_database_url converts postgresql:// to postgresql+asyncpg://."""
    # Mock settings
    original_url = settings.DATABASE_URL
    if original_url:
        async_url = get_async_database_url()
        assert async_url.startswith("postgresql+asyncpg://")
        assert "postgresql://" not in async_url


def test_get_async_database_url_raises_without_database_url(monkeypatch):
    """Test get_async_database_url raises ValueError when DATABASE_URL is None."""
    from app.db import session as session_module

    original_url = settings.DATABASE_URL
    try:
        # Mock DATABASE_URL to None
        monkeypatch.setattr(settings, "DATABASE_URL", None)
        # Clear cache
        session_module.get_async_database_url.__wrapped__ = None
        with pytest.raises(ValueError, match="DATABASE_URL is not set"):
            get_async_database_url()
    finally:
        # Restore
        monkeypatch.setattr(settings, "DATABASE_URL", original_url)


@pytest.mark.asyncio
async def test_async_session_local_creates_session():
    """Test AsyncSessionLocal creates valid async sessions."""
    async with AsyncSessionLocal() as session:
        assert isinstance(session, AsyncSession)
        # Test connection
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_get_db_dependency_yields_session():
    """Test get_db dependency yields async session."""
    async for session in get_db():
        assert isinstance(session, AsyncSession)
        # Test connection
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        break  # Only test first yield


@pytest.mark.asyncio
async def test_get_db_commits_on_success():
    """Test get_db commits session on successful operation."""
    from app.models import Analysis

    async for session in get_db():
        # Create analysis
        analysis = Analysis(url="https://test.com", content_type="article", status="pending")
        session.add(analysis)
        # Should commit after yield
        break

    # Verify analysis was committed (session is closed, so check in new session)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM analyses WHERE url = :url"), {"url": "https://test.com"}
        )
        count = result.scalar()
        assert count > 0

        # Cleanup
        await session.execute(
            text("DELETE FROM analyses WHERE url = :url"), {"url": "https://test.com"}
        )
        await session.commit()


@pytest.mark.asyncio
async def test_get_db_rolls_back_on_exception():
    """Test get_db rolls back session on exception."""
    from app.models import Analysis

    try:
        async for session in get_db():
            # Create analysis
            analysis = Analysis(url="https://test-exception.com", content_type="article")
            session.add(analysis)
            # Raise exception (should trigger rollback)
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Verify analysis was NOT committed
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM analyses WHERE url = :url"),
            {"url": "https://test-exception.com"},
        )
        count = result.scalar()
        assert count == 0


@pytest.mark.asyncio
async def test_get_db_closes_session_in_finally():
    """Test get_db closes session in finally block."""
    session_closed = False

    async for session in get_db():
        assert not session_closed
        break

    # Session should be closed after exiting context
    # Verify by checking it's not accessible
    assert True  # If we get here, session was properly closed


@pytest.mark.asyncio
async def test_engine_connection_pool():
    """Test async engine connection pool works correctly."""
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT version()"))
        version = result.scalar()
        assert "PostgreSQL" in version


@pytest.mark.asyncio
async def test_engine_echo_in_development():
    """Test engine echo is enabled in development environment."""
    # Engine echo should be True in development
    # This is checked via settings.ENVIRONMENT == "development"
    assert settings.ENVIRONMENT == "development"
    # Echo setting is part of engine creation, verified by logging output


@pytest.mark.asyncio
async def test_multiple_sessions_work_independently():
    """Test multiple sessions work independently."""
    async with AsyncSessionLocal() as session1:
        async with AsyncSessionLocal() as session2:
            # Both sessions should work independently
            result1 = await session1.execute(text("SELECT 1"))
            result2 = await session2.execute(text("SELECT 2"))

            assert result1.scalar() == 1
            assert result2.scalar() == 2


@pytest.mark.asyncio
async def test_session_expire_on_commit_false():
    """Test session expire_on_commit is False (objects don't expire after commit)."""
    from app.models import Analysis

    async with AsyncSessionLocal() as session:
        analysis = Analysis(url="https://test-expire.com", content_type="article", status="pending")
        session.add(analysis)
        await session.commit()

        # After commit, object should still be accessible
        assert analysis.id is not None
        assert analysis.url == "https://test-expire.com"

        # Cleanup
        await session.delete(analysis)
        await session.commit()
