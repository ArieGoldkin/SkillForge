"""Health check endpoint for monitoring and deployment verification."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    version: str
    environment: str
    database: dict[str, str] | None = None
    ollama: dict[str, str] | None = None


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Health check endpoint for monitoring and deployment verification."""
    from app.core.config import settings

    return HealthStatus(
        status="healthy",
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        database=None,  # To be implemented in Task 1.2.5
        ollama=None,  # To be implemented in Task 1.5.1
    )
