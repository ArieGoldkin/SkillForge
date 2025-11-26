"""Database session management for async operations.

This module provides async database session management using SQLAlchemy's
async engine and session factory. It handles connection pooling, session
lifecycle, and provides a FastAPI dependency for database access.

Key Components:
    - get_async_database_url(): Converts sync PostgreSQL URL to async URL
    - engine: Global async engine with connection pooling
    - AsyncSessionLocal: Session factory for creating async sessions
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
    The engine is created at module import time. Ensure DATABASE_URL is
    configured before importing this module.

"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.constants import DB_MAX_OVERFLOW, DB_POOL_RECYCLE, DB_POOL_SIZE, DB_TIMEOUT


def get_async_database_url() -> str:
    """Convert synchronous PostgreSQL URL to async URL.

    Converts postgresql:// to postgresql+asyncpg:// for async operations.
    """
    if not settings.DATABASE_URL:
        msg = "DATABASE_URL is not set"
        raise ValueError(msg)
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


# Create async engine with connection timeout to prevent hanging
# connect_args sets asyncpg connection timeout (in seconds)
# pool_timeout prevents waiting indefinitely for a connection from the pool
# Note: asyncpg uses 'timeout' for connection timeout, 'command_timeout' for query timeout
# Disable pool_pre_ping in test mode to prevent hanging when database is unreachable
# (tests will handle connection errors gracefully)
# Use smaller connection pool in test mode to prevent exhaustion
_is_test_mode = os.getenv("PYTEST_CURRENT_TEST") is not None
_test_pool_size = 1  # Minimal pool size for tests to prevent exhaustion
_test_max_overflow = 1  # Minimal overflow for tests

engine = create_async_engine(
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

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,  # Manual flush control
    autocommit=False,
)


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
    # pool_timeout in engine config should prevent hanging
    # SQLAlchemy will raise an exception if connection cannot be obtained
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
