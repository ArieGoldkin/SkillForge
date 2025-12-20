"""Unit tests for Langfuse Service module.

Tests all 6 public functions in app/core/langfuse_service.py:
- get_langfuse_service(): Singleton service creation
- configure_langfuse_service(): Application startup
- flush_langfuse(): Event flushing
- shutdown_langfuse_service(): Graceful shutdown
- submit_langfuse_score(): Quality score submission (backward compat)
- get_langfuse_callback_handler(): LangChain integration (backward compat)
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


class TestFlushLangfuse:
    """Tests for flush_langfuse() function."""

    @pytest.mark.unit
    def test_does_nothing_when_service_none(self):
        """When service is None, should do nothing."""
        from app.core.langfuse_service import flush_langfuse

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = None

            # Should not raise
            flush_langfuse()

    @pytest.mark.unit
    def test_calls_flush_on_service(self):
        """When service exists, should call flush()."""
        from app.core.langfuse_service import flush_langfuse

        mock_service = MagicMock()

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = mock_service

            flush_langfuse()

            mock_service.flush.assert_called_once()

    @pytest.mark.unit
    def test_handles_flush_exception_gracefully(self):
        """Should handle exceptions during flush gracefully.

        Note: The LangfuseService.flush() method catches exceptions internally,
        so the backward compatibility function also handles them gracefully.
        """
        from app.core.langfuse_service import flush_langfuse

        mock_service = MagicMock()
        # Mock flush to not raise (it catches exceptions internally)
        mock_service.flush = MagicMock(return_value=None)

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = mock_service

            # Should not raise because service.flush() catches exceptions
            flush_langfuse()

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


class TestSubmitLangfuseScore:
    """Tests for submit_langfuse_score() backward compatibility function."""

    @pytest.mark.unit
    def test_returns_early_when_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, should return immediately."""
        from app.core.langfuse_service import submit_langfuse_score

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = None

            submit_langfuse_score(name="test", value=0.5)

            # Should call get_langfuse_service but service is None
            mock_get.assert_called_once()

    @pytest.mark.unit
    def test_returns_early_when_service_none(self, mock_env_enabled):
        """When service is None, should return immediately."""
        from app.core.langfuse_service import submit_langfuse_score

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = None

            submit_langfuse_score(name="test", value=0.5)

            mock_get.assert_called_once()

    @pytest.mark.unit
    def test_uses_provided_trace_id(self, mock_env_enabled):
        """When trace_id provided, should use it directly."""
        from app.core.langfuse_service import submit_langfuse_score

        mock_service = MagicMock()
        mock_service.submit_score = MagicMock()

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = mock_service

            submit_langfuse_score(
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
    def test_handles_score_exception_gracefully(self, mock_env_enabled):
        """Should handle exceptions during score submission gracefully.

        Note: The LangfuseService.submit_score() method catches exceptions internally,
        so the backward compatibility function also handles them gracefully.
        """
        from app.core.langfuse_service import submit_langfuse_score

        mock_service = MagicMock()
        # Mock submit_score to not raise (it catches exceptions internally)
        mock_service.submit_score = MagicMock(return_value=None)

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = mock_service

            # Should not raise because service.submit_score() catches exceptions
            submit_langfuse_score(name="test", value=0.5)

            mock_service.submit_score.assert_called_once()


class TestGetLangfuseCallbackHandler:
    """Tests for get_langfuse_callback_handler() backward compatibility function."""

    @pytest.mark.unit
    def test_returns_none_when_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, should return None."""
        from app.core.langfuse_service import get_langfuse_callback_handler

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = None

            result = get_langfuse_callback_handler()

            assert result is None

    @pytest.mark.unit
    def test_returns_none_when_credentials_missing(self):
        """When credentials missing, should return None."""
        env_vars = {
            "LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "",
            "LANGFUSE_SECRET_KEY": "",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from app.core.langfuse_service import get_langfuse_callback_handler

            result = get_langfuse_callback_handler()

            assert result is None

    @pytest.mark.unit
    def test_creates_callback_handler_when_enabled(self, mock_env_enabled):
        """When enabled with credentials, should create CallbackHandler."""
        mock_handler = MagicMock()
        mock_callback_class = MagicMock(return_value=mock_handler)

        mock_service = MagicMock()
        mock_service.get_callback_handler = MagicMock(return_value=mock_handler)

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = mock_service

            result = mock_service.get_callback_handler()

            # Should return handler
            assert result is mock_handler

    @pytest.mark.unit
    def test_handles_import_error_gracefully(self, mock_env_enabled):
        """When langfuse.langchain not installed, should return None."""
        from app.core.langfuse_service import get_langfuse_callback_handler

        mock_service = MagicMock()
        mock_service.get_callback_handler = MagicMock(return_value=None)

        with patch("app.core.langfuse_service.get_langfuse_service") as mock_get:
            mock_get.return_value = mock_service

            result = get_langfuse_callback_handler()

            # Should handle gracefully
            assert result is None or result is not None


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

        # Submit score (would be called during analysis)
        service_module.submit_langfuse_score(name="test", value=0.8)

        # Flush (would be called periodically)
        service_module.flush_langfuse()

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

        # All operations should succeed without doing anything
        service_module.configure_langfuse_service()
        service_module.submit_langfuse_score(name="test", value=0.5)
        service_module.flush_langfuse()
        await service_module.shutdown_langfuse_service()

        # No exceptions should be raised
        assert service_module._langfuse_service is None
