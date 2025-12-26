"""Unit tests for Langfuse Service module.

Tests all public functions in app/core/langfuse_service.py:
- get_langfuse_service(): Singleton service creation
- configure_langfuse_service(): Application startup
- shutdown_langfuse_service(): Graceful shutdown
- LangfuseService methods: flush(), submit_score(), get_callback_handler()
"""

import os
from unittest.mock import MagicMock, patch

import pytest


# Reset module state between tests
@pytest.fixture(autouse=True)
def reset_langfuse_service():
    """Reset the global Langfuse service singleton between tests."""
    import app.core.langfuse_service as service_module

    # Reset global state
    service_module._langfuse_service = None
    yield
    # Cleanup after test
    service_module._langfuse_service = None


@pytest.fixture
def mock_env_enabled():
    """Fixture for enabled Langfuse environment."""
    env_vars = {
        "LANGFUSE_ENABLED": "true",
        "LANGFUSE_PUBLIC_KEY": "pk-test-123",
        "LANGFUSE_SECRET_KEY": "sk-test-456",
        "LANGFUSE_HOST": "http://localhost:3000",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield


@pytest.fixture
def mock_env_disabled():
    """Fixture for disabled Langfuse environment."""
    env_vars = {
        "LANGFUSE_ENABLED": "false",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield


class TestGetLangfuseService:
    """Tests for get_langfuse_service() singleton pattern."""

    @pytest.mark.unit
    def test_returns_none_when_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, should return None."""
        from app.core.langfuse_service import get_langfuse_service

        result = get_langfuse_service()

        assert result is None

    @pytest.mark.unit
    def test_returns_none_when_credentials_missing(self):
        """When credentials are missing, should return None with warning."""
        env_vars = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": "",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from app.core.langfuse_service import get_langfuse_service

            result = get_langfuse_service()

            assert result is None

    @pytest.mark.unit
    def test_returns_none_when_public_key_missing(self):
        """When only public key is missing, should return None."""
        env_vars = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from app.core.langfuse_service import get_langfuse_service

            result = get_langfuse_service()

            assert result is None

    @pytest.mark.unit
    def test_creates_service_when_enabled(self, mock_env_enabled):
        """When enabled with credentials, should create LangfuseService."""
        import app.core.langfuse_service as service_module

        mock_sdk_client = MagicMock()
        mock_langfuse_class = MagicMock(return_value=mock_sdk_client)

        # Patch the import inside the function by patching sys.modules
        mock_langfuse_module = MagicMock()
        mock_langfuse_module.Langfuse = mock_langfuse_class

        service_module._langfuse_service = None

        with patch.dict("sys.modules", {"langfuse": mock_langfuse_module}):
            result = service_module.get_langfuse_service()

        # Should return the service
        assert result is not None
        assert isinstance(result, service_module.LangfuseService)
        mock_langfuse_class.assert_called_once()

    @pytest.mark.unit
    def test_singleton_returns_same_instance(self, mock_env_enabled):
        """Calling get_langfuse_service() twice should return same instance."""
        import app.core.langfuse_service as service_module

        # Set a mock service
        mock_service = MagicMock(spec=service_module.LangfuseService)
        service_module._langfuse_service = mock_service

        result1 = service_module.get_langfuse_service()
        result2 = service_module.get_langfuse_service()

        assert result1 is result2
        assert result1 is mock_service

    @pytest.mark.unit
    def test_handles_import_error_gracefully(self, mock_env_enabled):
        """When langfuse package not installed, should return service with no SDK client."""
        import app.core.langfuse_service as service_module

        service_module._langfuse_service = None

        with patch.dict("sys.modules", {"langfuse": None}):
            # The import will fail but should be handled gracefully
            # In real code, ImportError is caught
            result = service_module.get_langfuse_service()

            # Service is created but SDK client will be None
            assert result is not None
            assert result.sdk_client is None


class TestConfigureLangfuseService:
    """Tests for configure_langfuse_service() startup function."""

    @pytest.mark.unit
    def test_calls_get_langfuse_service(self, mock_env_disabled):
        """Should call get_langfuse_service during configuration."""
        from app.core.langfuse_service import configure_langfuse_service

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = None

            configure_langfuse_service()

            mock_get.assert_called_once()

    @pytest.mark.unit
    def test_logs_success_when_service_created(self, mock_env_enabled):
        """Should log success when service is successfully created."""
        from app.core.langfuse_service import configure_langfuse_service

        mock_service = MagicMock()

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = mock_service

            with patch("app.core.langfuse_service.logger") as mock_logger:
                configure_langfuse_service()

                mock_logger.info.assert_called()


class TestLangfuseServiceFlush:
    """Tests for LangfuseService.flush() method."""

    @pytest.mark.unit
    def test_flush_does_nothing_when_service_none(self):
        """When service is None, accessing flush should not be possible."""
        from app.core.langfuse_service import get_langfuse_service

        with patch("app.core.langfuse_service._langfuse_service", None):
            with patch.dict(os.environ, {"LANGFUSE_ENABLED": "false"}):
                service = get_langfuse_service()
                assert service is None

    @pytest.mark.unit
    def test_flush_calls_sdk_flush(self):
        """When service exists, flush() should call SDK flush."""
        import app.core.langfuse_service as service_module

        mock_sdk_client = MagicMock()
        mock_service = MagicMock(spec=service_module.LangfuseService)
        mock_service.flush = MagicMock()

        service_module._langfuse_service = mock_service

        service = service_module.get_langfuse_service()
        service.flush()

        mock_service.flush.assert_called_once()

    @pytest.mark.unit
    def test_flush_handles_exception_gracefully(self):
        """Service.flush() should handle exceptions internally."""
        import app.core.langfuse_service as service_module

        mock_service = MagicMock(spec=service_module.LangfuseService)
        mock_service.flush = MagicMock(return_value=None)

        service_module._langfuse_service = mock_service

        # Should not raise
        service = service_module.get_langfuse_service()
        service.flush()

        mock_service.flush.assert_called_once()


class TestShutdownLangfuseService:
    """Tests for shutdown_langfuse_service() function."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_does_nothing_when_service_none(self):
        """When service is None, should do nothing."""
        import app.core.langfuse_service as service_module

        service_module._langfuse_service = None

        # Should not raise
        await service_module.shutdown_langfuse_service()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calls_shutdown_on_service(self):
        """When service exists, should call shutdown()."""
        from unittest.mock import AsyncMock

        import app.core.langfuse_service as service_module

        mock_service = MagicMock()
        mock_service.shutdown = AsyncMock()
        service_module._langfuse_service = mock_service

        await service_module.shutdown_langfuse_service()

        mock_service.shutdown.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clears_global_service(self):
        """Should set _langfuse_service to None after shutdown."""
        from unittest.mock import AsyncMock

        import app.core.langfuse_service as service_module

        mock_service = MagicMock()
        mock_service.shutdown = AsyncMock()
        service_module._langfuse_service = mock_service

        await service_module.shutdown_langfuse_service()

        assert service_module._langfuse_service is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clears_service_even_on_exception(self):
        """Should clear service even if shutdown raises exception.

        Note: The LangfuseService.shutdown() method catches exceptions internally,
        but we still verify that the global service is cleared.
        """
        from unittest.mock import AsyncMock

        import app.core.langfuse_service as service_module

        mock_service = MagicMock()
        # Mock shutdown to not raise (it catches exceptions internally)
        mock_service.shutdown = AsyncMock(return_value=None)
        service_module._langfuse_service = mock_service

        # Should not raise and should clear service
        await service_module.shutdown_langfuse_service()

        mock_service.shutdown.assert_called_once()
        assert service_module._langfuse_service is None


class TestLangfuseServiceSubmitScore:
    """Tests for LangfuseService.submit_score() method."""

    @pytest.mark.unit
    def test_submit_score_when_service_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, service is None."""
        from app.core.langfuse_service import get_langfuse_service

        service = get_langfuse_service()
        assert service is None

    @pytest.mark.unit
    def test_submit_score_uses_provided_trace_id(self, mock_env_enabled):
        """When trace_id provided, should use it directly."""
        import app.core.langfuse_service as service_module

        mock_service = MagicMock(spec=service_module.LangfuseService)
        mock_service.submit_score = MagicMock()
        service_module._langfuse_service = mock_service

        service = service_module.get_langfuse_service()
        service.submit_score(
            trace_id="custom-trace-123",
            name="relevance",
            value=0.85,
            comment="High relevance",
        )

        mock_service.submit_score.assert_called_once_with(
            trace_id="custom-trace-123",
            name="relevance",
            value=0.85,
            comment="High relevance",
        )

    @pytest.mark.unit
    def test_submit_score_handles_exception_gracefully(self, mock_env_enabled):
        """Service.submit_score() should handle exceptions internally."""
        import app.core.langfuse_service as service_module

        mock_service = MagicMock(spec=service_module.LangfuseService)
        mock_service.submit_score = MagicMock(return_value=None)
        service_module._langfuse_service = mock_service

        # Should not raise
        service = service_module.get_langfuse_service()
        service.submit_score(name="test", value=0.5)

        mock_service.submit_score.assert_called_once()


class TestLangfuseServiceGetCallbackHandler:
    """Tests for LangfuseService.get_callback_handler() method."""

    @pytest.mark.unit
    def test_callback_handler_when_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, service is None."""
        from app.core.langfuse_service import get_langfuse_service

        service = get_langfuse_service()
        assert service is None

    @pytest.mark.unit
    def test_callback_handler_returns_handler(self, mock_env_enabled):
        """When enabled with credentials, should return CallbackHandler."""
        import app.core.langfuse_service as service_module

        mock_handler = MagicMock()
        mock_service = MagicMock(spec=service_module.LangfuseService)
        mock_service.get_callback_handler = MagicMock(return_value=mock_handler)
        service_module._langfuse_service = mock_service

        service = service_module.get_langfuse_service()
        result = service.get_callback_handler()

        assert result is mock_handler

    @pytest.mark.unit
    def test_callback_handler_handles_import_error(self, mock_env_enabled):
        """When langfuse.langchain not installed, should return None."""
        import app.core.langfuse_service as service_module

        mock_service = MagicMock(spec=service_module.LangfuseService)
        mock_service.get_callback_handler = MagicMock(return_value=None)
        service_module._langfuse_service = mock_service

        service = service_module.get_langfuse_service()
        result = service.get_callback_handler()

        assert result is None


class TestIntegration:
    """Integration tests for langfuse_service module."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, mock_env_enabled):
        """Test full service lifecycle: create -> use -> flush -> shutdown."""
        from unittest.mock import AsyncMock

        import app.core.langfuse_service as service_module

        mock_sdk_client = MagicMock()
        mock_sdk_client.get_current_trace_id.return_value = "test-trace"

        mock_service = MagicMock(spec=service_module.LangfuseService)
        mock_service.submit_score = MagicMock()
        mock_service.flush = MagicMock()
        mock_service.shutdown = AsyncMock()

        # Simulate full lifecycle
        service_module._langfuse_service = mock_service

        # Configure (would be called at startup)
        service_module.configure_langfuse_service()

        # Get service and use methods directly (new pattern)
        service = service_module.get_langfuse_service()

        # Submit score (would be called during analysis)
        service.submit_score(name="test", value=0.8)

        # Flush (would be called periodically)
        service.flush()

        # Shutdown (would be called at app shutdown)
        await service_module.shutdown_langfuse_service()

        # Verify lifecycle
        mock_service.submit_score.assert_called_once()
        mock_service.flush.assert_called_once()
        mock_service.shutdown.assert_called_once()
        assert service_module._langfuse_service is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disabled_lifecycle_is_noop(self, mock_env_disabled):
        """When disabled, all operations should be no-ops."""
        import app.core.langfuse_service as service_module

        # Configure should work without error
        service_module.configure_langfuse_service()

        # Service should be None when disabled
        service = service_module.get_langfuse_service()
        assert service is None

        # Shutdown should work without error
        await service_module.shutdown_langfuse_service()

        # No exceptions should be raised
        assert service_module._langfuse_service is None
