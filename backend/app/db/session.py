"""Database session management for async operations.

This module provides async database session management using SQLAlchemy's
async engine and session factory. It handles connection pooling, session
lifecycle, and provides a FastAPI dependency for database access.

Key Components:
    - get_async_database_url(): Converts sync PostgreSQL URL to async URL
    - get_engine(): Lazily creates the async engine with connection pooling
    - get_session_factory(): Lazily creates the session factory
    - get_db(): FastAPI dependency for database session injection

Connection Pooling:
    The engine is configured with:
    - pool_size: Number of connections to maintain (default: 5)
    - max_overflow: Additional connections beyond pool_size (default: 10)
    - pool_recycle: Recycle connections after 1 hour (default: 3600s)
    - pool_pre_ping: Verify connections before using (prevents stale connections)

Session Management:
    Sessions are created using async context managers and automatically:
    - Commit on successful request completion
    - Rollback on exceptions
    - Close after request completes

Usage:
    ```python
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import get_db


    @app.post("/items")
    async def create_item(db: AsyncSession = Depends(get_db)):
        # Use db session here
        item = Item(name="test")
        db.add(item)
        # Session auto-commits on successful return
        return item
    ```

Note:
    The engine is created lazily on first use. This allows the module to be
    imported without DATABASE_URL being set (required for CI environments
    that run linting/type checking without a database).

"""

import os
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

# Lazy initialization - engine and session factory are created on first use
_engine: "AsyncEngine | None" = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_database_url() -> str:
    """Convert synchronous PostgreSQL URL to async URL.

    Converts postgresql:// to postgresql+asyncpg:// for async operations.

    Raises:
        ValueError: If DATABASE_URL is not set

    """
    # Import settings lazily to avoid circular imports
    from app.core.config import settings

    if not settings.DATABASE_URL:
        msg = "DATABASE_URL is not set"
        raise ValueError(msg)
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


def get_engine() -> "AsyncEngine":
    """Get or create the async database engine.

    The engine is created lazily on first call. This allows the module
    to be imported without DATABASE_URL being set.

    Returns:
        The async SQLAlchemy engine

    Raises:
        ValueError: If DATABASE_URL is not set when engine is first created

    """
    global _engine  # noqa: PLW0603

    if _engine is None:
        from app.core.config import settings
        from app.core.constants import DB_MAX_OVERFLOW, DB_POOL_RECYCLE, DB_POOL_SIZE, DB_TIMEOUT

        # Detect test mode for connection pool sizing
        _is_test_mode = os.getenv("PYTEST_CURRENT_TEST") is not None
        _test_pool_size = 5  # Larger pool in tests to avoid async task starvation
        _test_max_overflow = 5

        _engine = create_async_engine(
            get_async_database_url(),
            echo=settings.ENVIRONMENT == "development",  # Log SQL in development
            pool_size=_test_pool_size if _is_test_mode else DB_POOL_SIZE,
            max_overflow=_test_max_overflow if _is_test_mode else DB_MAX_OVERFLOW,
            pool_recycle=DB_POOL_RECYCLE,
            pool_pre_ping=not _is_test_mode,  # Disable in tests to prevent hanging
            pool_timeout=DB_TIMEOUT,  # Timeout when getting connection from pool
            connect_args={
                "timeout": DB_TIMEOUT,  # Connection timeout in seconds (asyncpg parameter)
                "command_timeout": DB_TIMEOUT,  # Query execution timeout in seconds
                "server_settings": {
                    "application_name": "skillforge-backend",
                },
            },
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory.

    The factory is created lazily on first call.

    Returns:
        The async session factory

    """
    global _session_factory  # noqa: PLW0603

    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual flush control
            autocommit=False,
        )

    return _session_factory


# Backward compatibility: expose engine and AsyncSessionLocal as properties
# that lazily create the underlying objects
class _LazyEngine:
    """Lazy engine accessor for backward compatibility."""

    def __getattr__(self, name: str):
        return getattr(get_engine(), name)

    async def dispose(self):
        """Dispose the engine connections."""
        engine = get_engine()
        await engine.dispose()


class _LazySessionFactory:
    """Lazy session factory accessor for backward compatibility."""

    def __call__(self) -> AsyncSession:
        return get_session_factory()()

    def __getattr__(self, name: str):
        return getattr(get_session_factory(), name)


# Backward compatible exports - these are lazy wrappers
engine = _LazyEngine()
AsyncSessionLocal = _LazySessionFactory()


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency for FastAPI to get database session.

    Yields an async database session and ensures it's properly closed
    after the request completes.

    The pool_timeout in engine configuration (DB_TIMEOUT) should prevent
    hanging when getting connections from the pool. If a connection cannot
    be obtained within the timeout, SQLAlchemy will raise an exception.

    Usage:
        @app.post("/items")
        async def create_item(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
    """
    # Get the session factory lazily
    session_factory = get_session_factory()

    # pool_timeout in engine config should prevent hanging
    # SQLAlchemy will raise an exception if connection cannot be obtained
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
