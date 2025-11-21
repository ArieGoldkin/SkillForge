"""Tests for health check endpoint with database."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.api.v1.health import check_database


@pytest.mark.asyncio
async def test_check_database_returns_connected_when_database_available():
    """Test check_database returns connected status when database is available."""
    from app.core.config import settings

    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")

    result = await check_database()

    assert result is not None
    assert result["status"] == "connected"


@pytest.mark.asyncio
async def test_check_database_returns_none_when_no_database_url(monkeypatch):
    """Test check_database returns None when DATABASE_URL is not configured."""
    from app.core.config import settings
    from app.api.v1 import health as health_module

    original_url = settings.DATABASE_URL
    try:
        monkeypatch.setattr(settings, "DATABASE_URL", None)
        # Reload module to pick up change
        import importlib
        importlib.reload(health_module)

        result = await health_module.check_database()
        assert result is None
    finally:
        monkeypatch.setattr(settings, "DATABASE_URL", original_url)
        import importlib
        importlib.reload(health_module)


@pytest.mark.asyncio
async def test_check_database_returns_error_on_connection_failure(monkeypatch):
    """Test check_database returns error status when connection fails."""
    from app.core.config import settings
    from app.api.v1 import health as health_module

    original_url = settings.DATABASE_URL
    try:
        # Set invalid database URL
        monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://invalid:invalid@localhost:9999/invalid")
        import importlib
        importlib.reload(health_module)

        result = await health_module.check_database()

        assert result is not None
        assert result["status"] == "disconnected"
        assert "error" in result
    finally:
        monkeypatch.setattr(settings, "DATABASE_URL", original_url)
        import importlib
        importlib.reload(health_module)


def test_health_endpoint_includes_database_status(client):
    """Test health check endpoint includes database status."""
    from app.core.config import settings

    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "database" in data

    if settings.DATABASE_URL:
        assert data["database"] is not None
        assert "status" in data["database"]
    else:
        assert data["database"] is None


def test_health_endpoint_database_status_connected(client):
    """Test health check endpoint shows database as connected when available."""
    from app.core.config import settings

    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")

    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["database"]["status"] == "connected"
