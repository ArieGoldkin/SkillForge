"""Tests for health check endpoint with database."""

import pytest
from fastapi import status

from app.api.v1.health import check_database


@pytest.mark.asyncio
async def test_check_database_returns_connected_when_database_available(requires_database):
    """Test check_database returns connected status when database is available."""
    result = await check_database()

    assert result is not None
    assert result["status"] == "connected"


@pytest.mark.asyncio
async def test_check_database_returns_none_when_no_database_url(monkeypatch):
    """Test check_database returns None when DATABASE_URL is not configured."""
    from app.api.v1 import health as health_module
    from app.core.config import settings

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
async def test_check_database_returns_error_on_connection_failure(monkeypatch, requires_database):
    """Test check_database returns error status when connection fails.

    Note: This test is challenging because the engine is created at module import
    time. We mock the engine's connection to simulate a connection failure.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.api.v1.health import check_database
    from sqlalchemy.exc import SQLAlchemyError

    # Mock the engine.begin() to raise a SQLAlchemyError
    with patch("app.api.v1.health.engine") as mock_engine:
        # Create a mock async context manager that raises an error
        mock_begin = MagicMock()
        mock_begin.__aenter__ = AsyncMock(side_effect=SQLAlchemyError("Connection failed"))
        mock_begin.__aexit__ = AsyncMock(return_value=None)
        mock_engine.begin.return_value = mock_begin

        result = await check_database()

        assert result is not None
        assert result["status"] == "disconnected"
        assert "error" in result


@pytest.mark.asyncio
async def test_health_endpoint_includes_database_status():
    """Test health check endpoint includes database status."""
    import httpx

    from app.core.config import settings
    from app.main import app

    # Skip if DATABASE_URL is set to avoid event loop conflicts
    # The engine is created at import time with a different event loop
    # and causes conflicts when TestClient/AsyncClient tries to use it
    if settings.DATABASE_URL:
        pytest.skip(
            "Skipping to avoid event loop conflicts when DATABASE_URL is set. "
            "Engine connections created at import time conflict with test event loops."
        )

    # Use AsyncClient with ASGITransport to avoid event loop conflicts
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "database" in data
        assert data["database"] is None


@pytest.mark.asyncio
async def test_health_endpoint_database_status_connected(requires_database, reset_engine_connections):
    """Test health check endpoint shows database as connected when available."""
    import httpx

    from app.main import app

    # Use AsyncClient with ASGITransport to avoid event loop conflicts
    # reset_engine_connections ensures connections are created in test's event loop
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["database"]["status"] == "connected"
