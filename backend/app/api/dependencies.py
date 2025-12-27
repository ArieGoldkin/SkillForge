"""Shared FastAPI dependencies for dependency injection.

This module provides reusable dependency functions for FastAPI endpoints.
Dependencies are injected using FastAPI's Depends() mechanism, enabling
easy testing and mocking.

Available Dependencies:
    - get_db: Database session dependency
    - get_settings: Application settings dependency
"""

from collections.abc import AsyncGenerator
from contextlib import aclosing

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db as _get_db


async def get_database_session() -> AsyncGenerator[AsyncSession]:
    """Dependency for FastAPI to get database session.

    Provides an async database session that is automatically committed
    on success and rolled back on exceptions. The session is closed
    after the request completes.

    Usage:
        ```python
        @router.post("/items")
        async def create_item(db: AsyncSession = Depends(get_database_session)):
            # Use db session here
            item = Item(name="test")
            db.add(item)
            # Session auto-commits on successful return
            return item
        ```

    Yields:
        AsyncSession: SQLAlchemy async session

    """
    async with aclosing(_get_db()) as db_gen:
        async for session in db_gen:
            yield session


def get_app_settings() -> Settings:
    """Dependency for FastAPI to get application settings.

    Provides access to the cached settings instance. The settings are
    loaded once and cached for performance.

    Usage:
        ```python
        @router.get("/config")
        async def get_config(settings: Settings = Depends(get_app_settings)):
            return {"environment": settings.ENVIRONMENT}
        ```

    Returns:
        Settings: Application settings instance

    """
    return get_settings()


# Convenience aliases for common usage patterns
get_db = get_database_session
settings = get_app_settings
