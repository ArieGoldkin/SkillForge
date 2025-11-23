"""Health check endpoint for monitoring and deployment verification."""

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.session import engine

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str
    database: dict[str, str] | None = None
    ollama: dict[str, str] | None = None


async def check_database() -> dict[str, str] | None:
    """Check database connection status.

    Returns:
        Dictionary with database status, or None if DATABASE_URL is not configured.

    """
    if not settings.DATABASE_URL:
        return None

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        error_msg = str(e)
        return {"status": "disconnected", "error": error_msg}
    else:
        return {"status": "connected"}


@router.get("/health")
async def health_check() -> HealthStatus:
    """Health check endpoint for monitoring and deployment verification."""
    database_status = await check_database()

    return HealthStatus(
        status="healthy",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        database=database_status,
        ollama=None,  # To be implemented in Task 1.5.1
    )
