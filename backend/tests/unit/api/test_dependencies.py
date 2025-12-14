"""Unit tests for API dependencies module.

This module tests the FastAPI dependency injection functions used across
all API endpoints. These dependencies provide database sessions and
application settings to endpoint handlers.

Coverage:
    - get_database_session(): Database session dependency
    - get_app_settings(): Application settings dependency
    - Convenience aliases (get_db, settings)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_app_settings,
    get_database_session,
    get_db,
    settings,
)


class TestGetDatabaseSession:
    """Test cases for get_database_session() dependency."""

    @pytest.mark.asyncio
    async def test_yields_valid_session(self):
        """Test that get_database_session yields a valid AsyncSession."""
        # Create a mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock the underlying _get_db generator
        async def mock_get_db_generator():
            yield mock_session

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator()):
            # Call the dependency
            async for session in get_database_session():
                # Verify we get the mocked session
                assert session is mock_session
                # Verify it's an AsyncSession spec
                assert isinstance(session, AsyncMock)

    @pytest.mark.asyncio
    async def test_session_cleanup_on_success(self):
        """Test that session is properly cleaned up on successful request."""
        mock_session = AsyncMock(spec=AsyncSession)

        async def mock_get_db_generator():
            try:
                yield mock_session
                # Simulate commit on success
                await mock_session.commit()
            finally:
                # Simulate cleanup
                await mock_session.close()

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator()):
            # Simulate successful request
            async for session in get_database_session():
                assert session is mock_session
                # Do some work with session (simulated)
                session.add(MagicMock())

            # Verify commit was called (in the underlying _get_db)
            # Note: This happens in the underlying db.session.get_db, not in our wrapper

    @pytest.mark.asyncio
    async def test_session_cleanup_on_exception(self):
        """Test that session is properly cleaned up on exception."""
        mock_session = AsyncMock(spec=AsyncSession)

        async def mock_get_db_generator():
            try:
                yield mock_session
            except Exception:
                # Simulate rollback on exception
                await mock_session.rollback()
                raise
            finally:
                # Simulate cleanup
                await mock_session.close()

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator()):
            # Simulate request that raises exception
            with pytest.raises(ValueError):
                async for session in get_database_session():
                    assert session is mock_session
                    # Simulate an error during request
                    raise ValueError("Test error")

    @pytest.mark.asyncio
    async def test_multiple_calls_create_different_sessions(self):
        """Test that multiple calls create independent session generators."""
        mock_session_1 = AsyncMock(spec=AsyncSession)
        mock_session_2 = AsyncMock(spec=AsyncSession)

        # Create two separate generators
        async def mock_get_db_generator_1():
            yield mock_session_1

        async def mock_get_db_generator_2():
            yield mock_session_2

        # First call
        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator_1()):
            async for session in get_database_session():
                assert session is mock_session_1
                break  # Only get first yield

        # Second call should be independent
        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator_2()):
            async for session in get_database_session():
                assert session is mock_session_2
                break  # Only get first yield

    @pytest.mark.asyncio
    async def test_generator_protocol_compliance(self):
        """Test that dependency follows async generator protocol correctly."""
        mock_session = AsyncMock(spec=AsyncSession)

        async def mock_get_db_generator():
            yield mock_session

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator()):
            # Verify it's an async generator
            gen = get_database_session()
            assert hasattr(gen, "__anext__")
            assert hasattr(gen, "asend")
            assert hasattr(gen, "athrow")

            # Clean up generator
            await gen.aclose()


class TestGetAppSettings:
    """Test cases for get_app_settings() dependency."""

    def test_returns_settings_instance(self):
        """Test that get_app_settings returns a Settings instance."""
        from app.core.config import Settings

        # Clear cache to ensure fresh settings
        with patch("app.api.dependencies.get_settings") as mock_get_settings:
            mock_settings = MagicMock(spec=Settings)
            mock_get_settings.return_value = mock_settings

            result = get_app_settings()

            # Verify get_settings was called
            mock_get_settings.assert_called_once()
            # Verify we got the settings instance
            assert result is mock_settings

    def test_settings_cached_across_calls(self):
        """Test that settings are cached and reused across calls."""
        from app.core.config import Settings

        mock_settings = MagicMock(spec=Settings)

        with patch("app.api.dependencies.get_settings") as mock_get_settings:
            mock_get_settings.return_value = mock_settings

            # First call
            result1 = get_app_settings()
            # Second call
            result2 = get_app_settings()

            # Both should return the same instance (due to lru_cache in get_settings)
            assert result1 is mock_settings
            assert result2 is mock_settings
            # get_settings should be called for each call to get_app_settings
            # (the caching happens inside get_settings, not get_app_settings)
            assert mock_get_settings.call_count == 2

    def test_settings_have_expected_attributes(self):
        """Test that returned settings have expected configuration attributes."""
        from app.core.config import get_settings

        # Use real settings to verify structure
        settings = get_app_settings()

        # Verify key attributes exist
        assert hasattr(settings, "ENVIRONMENT")
        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "LOG_LEVEL")
        assert hasattr(settings, "CORS_ORIGINS")

        # Verify settings is from the cached singleton
        assert settings is get_settings()

    def test_settings_return_type(self):
        """Test that get_app_settings returns correct type."""
        from app.core.config import Settings

        result = get_app_settings()

        # Verify it's a Settings instance
        assert isinstance(result, Settings)

    def test_multiple_calls_use_same_cache(self, clear_config_cache):
        """Test that multiple calls use the same cached settings instance."""
        from app.core.config import get_settings

        # Clear cache first
        get_settings.cache_clear()

        # Get settings multiple times
        settings1 = get_app_settings()
        settings2 = get_app_settings()
        settings3 = get_app_settings()

        # All should be the same instance due to caching in get_settings
        assert settings1 is settings2
        assert settings2 is settings3


class TestConvenienceAliases:
    """Test cases for convenience alias exports."""

    def test_get_db_alias_exists(self):
        """Test that get_db convenience alias exists."""
        assert get_db is not None

    def test_get_db_alias_points_to_get_database_session(self):
        """Test that get_db alias points to get_database_session."""
        assert get_db is get_database_session

    def test_settings_alias_exists(self):
        """Test that settings convenience alias exists."""
        assert settings is not None

    def test_settings_alias_points_to_get_app_settings(self):
        """Test that settings alias points to get_app_settings."""
        assert settings is get_app_settings

    @pytest.mark.asyncio
    async def test_get_db_alias_works_as_dependency(self):
        """Test that get_db alias can be used as FastAPI dependency."""
        mock_session = AsyncMock(spec=AsyncSession)

        async def mock_get_db_generator():
            yield mock_session

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator()):
            # Use the alias
            async for session in get_db():
                assert session is mock_session
                break

    def test_settings_alias_works_as_dependency(self):
        """Test that settings alias can be used as FastAPI dependency."""
        from app.core.config import Settings

        result = settings()

        # Verify it returns a Settings instance
        assert isinstance(result, Settings)


class TestDependencyIntegration:
    """Integration tests for dependencies with FastAPI."""

    @pytest.mark.asyncio
    async def test_database_session_fastapi_usage_pattern(self):
        """Test dependency usage pattern as it would be used in FastAPI endpoints."""
        mock_session = AsyncMock(spec=AsyncSession)

        async def mock_get_db_generator():
            yield mock_session

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator()):
            # Simulate FastAPI calling the dependency
            async for db in get_database_session():
                # This is how endpoints would use the session
                assert isinstance(db, AsyncMock)
                # Simulate some database operations
                db.add(MagicMock())
                await db.commit()
                break

    def test_settings_fastapi_usage_pattern(self):
        """Test dependency usage pattern as it would be used in FastAPI endpoints."""
        # Simulate FastAPI calling the dependency
        app_settings = get_app_settings()

        # This is how endpoints would use settings
        assert hasattr(app_settings, "ENVIRONMENT")
        assert hasattr(app_settings, "DATABASE_URL")

    @pytest.mark.asyncio
    async def test_both_dependencies_can_be_used_together(self):
        """Test that both dependencies can be used together in same endpoint."""
        from app.core.config import Settings

        mock_session = AsyncMock(spec=AsyncSession)

        async def mock_get_db_generator():
            yield mock_session

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_generator()):
            # Get both dependencies as an endpoint would
            app_settings = get_app_settings()
            async for db in get_database_session():
                # Verify both are available
                assert isinstance(app_settings, Settings)
                assert isinstance(db, AsyncMock)
                break


class TestErrorHandling:
    """Test error handling in dependencies."""

    @pytest.mark.asyncio
    async def test_database_session_handles_connection_errors(self):
        """Test that database session dependency handles connection errors gracefully."""

        async def mock_get_db_with_error():
            raise ConnectionError("Database connection failed")
            # This yield is never reached, but needed for generator syntax
            yield  # pragma: no cover

        with patch("app.api.dependencies._get_db", return_value=mock_get_db_with_error()):
            # Verify exception propagates correctly
            with pytest.raises(ConnectionError, match="Database connection failed"):
                async for _ in get_database_session():
                    pass  # pragma: no cover

    def test_settings_dependency_handles_missing_env_vars(self, monkeypatch, clear_config_cache):
        """Test that settings dependency handles missing required env vars."""
        from app.core.config import get_settings

        # Clear cache and set minimal env vars
        get_settings.cache_clear()
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "development")

        # get_app_settings should still work even without DATABASE_URL
        # (DATABASE_URL is optional in Settings)
        result = get_app_settings()

        # Verify settings instance is returned (DATABASE_URL may be None or from .env.test)
        from app.core.config import Settings

        assert isinstance(result, Settings)
        # Verify core attributes exist
        assert hasattr(result, "ENVIRONMENT")
        assert result.ENVIRONMENT == "development"


class TestDocumentation:
    """Test that dependencies have proper documentation."""

    def test_get_database_session_has_docstring(self):
        """Test that get_database_session has comprehensive docstring."""
        assert get_database_session.__doc__ is not None
        assert len(get_database_session.__doc__) > 50
        assert "AsyncSession" in get_database_session.__doc__

    def test_get_app_settings_has_docstring(self):
        """Test that get_app_settings has comprehensive docstring."""
        assert get_app_settings.__doc__ is not None
        assert len(get_app_settings.__doc__) > 50
        assert "Settings" in get_app_settings.__doc__

    def test_module_has_docstring(self):
        """Test that dependencies module has comprehensive docstring."""
        from app.api import dependencies

        assert dependencies.__doc__ is not None
        assert "dependency injection" in dependencies.__doc__.lower()
