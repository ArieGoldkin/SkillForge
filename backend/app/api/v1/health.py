"""Health check endpoint for monitoring and deployment verification."""

import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
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


async def check_ollama() -> dict[str, str] | None:
    """Check Ollama service connection and model availability.

    Returns:
        Dictionary with Ollama status, or None if Ollama is not configured.

    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Check if Ollama is accessible
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code >= 400:
                return {
                    "status": "unavailable",
                    "error": f"HTTP {response.status_code}",
                }

            # Check if required model is available
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            required_model = settings.OLLAMA_EMBEDDING_MODEL

            model_available = any(required_model.lower() in model.lower() for model in models)

            if model_available:
                return {"status": "connected", "model": required_model}
            else:
                return {
                    "status": "model_missing",
                    "error": f"Model '{required_model}' not found",
                    "available_models": ", ".join(models[:5]),  # Show first 5
                }

    except httpx.TimeoutException as e:
        logger.warning("ollama_health_check_timeout", error=str(e))
        return {"status": "timeout", "error": "Connection timeout"}
    except Exception as e:
        logger.warning("ollama_health_check_failed", error=str(e), error_type=type(e).__name__)
        return {"status": "disconnected", "error": str(e)[:100]}


@router.get("/health")
async def health_check() -> HealthStatus:
    """Health check endpoint for monitoring and deployment verification."""
    database_status = await check_database()
    ollama_status = await check_ollama()

    return HealthStatus(
        status="healthy",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        database=database_status,
        ollama=ollama_status,
    )
