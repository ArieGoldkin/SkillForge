"""Health check endpoint for monitoring and deployment verification."""

import asyncio
import os

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.constants import DB_TEST_TIMEOUT, DB_TIMEOUT, MAX_ERROR_MESSAGE_LENGTH
from app.core.logging import get_logger
from app.db.session import engine

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str
    database: dict[str, str] | None = None


async def check_database() -> dict[str, str] | None:
    """Check database connection status.

    Returns:
        Dictionary with database status, or None if DATABASE_URL is not configured.

    """
    if not settings.DATABASE_URL:
        return None

    try:
        # Add timeout to prevent hanging on unavailable database
        # Use longer timeout in tests (detected via PYTEST_CURRENT_TEST)
        timeout_seconds = DB_TEST_TIMEOUT if os.environ.get("PYTEST_CURRENT_TEST") else DB_TIMEOUT
        async with asyncio.timeout(timeout_seconds):
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
    except TimeoutError:
        return {"status": "timeout", "error": "Connection timeout"}
    except SQLAlchemyError as e:
        error_msg = str(e)
        return {"status": "disconnected", "error": error_msg[:MAX_ERROR_MESSAGE_LENGTH]}
    except Exception as e:
        error_msg = str(e)
        return {"status": "error", "error": error_msg[:MAX_ERROR_MESSAGE_LENGTH]}
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
    )
