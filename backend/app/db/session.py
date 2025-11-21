"""Database session management for async operations."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


def get_async_database_url() -> str:
    """Convert synchronous PostgreSQL URL to async URL.

    Converts postgresql:// to postgresql+asyncpg:// for async operations.
    """
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set")
    return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


# Create async engine
engine = create_async_engine(
    get_async_database_url(),
    echo=settings.ENVIRONMENT == "development",  # Log SQL in development
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Don't expire objects after commit
    autoflush=False,  # Manual flush control
    autocommit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for FastAPI to get database session.

    Yields an async database session and ensures it's properly closed
    after the request completes.

    Usage:
        @app.post("/items")
        async def create_item(db: AsyncSession = Depends(get_db)):
            # Use db session here
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
