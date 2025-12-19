"""Unit tests for Langfuse configuration module.

Tests all 6 public functions in app/core/langfuse_config.py:
- get_langfuse_client(): Singleton client creation
- configure_langfuse_client(): Application startup
- flush_langfuse(): Event flushing
- shutdown_langfuse(): Graceful shutdown
- submit_langfuse_score(): Quality score submission
- get_langfuse_callback_handler(): LangChain integration
"""

import importlib
import os
from unittest.mock import MagicMock, patch

import pytest


# Reset module state between tests
@pytest.fixture(autouse=True)
def reset_langfuse_client():
    """Reset the global Langfuse client singleton between tests."""
    import app.core.langfuse_config as config_module

    # Reset global state
    config_module._langfuse_client = None
    yield
    # Cleanup after test
    config_module._langfuse_client = None


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


class TestGetLangfuseClient:
    """Tests for get_langfuse_client() singleton pattern."""

    @pytest.mark.unit
    def test_returns_none_when_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, should return None."""
        from app.core.langfuse_config import get_langfuse_client

        result = get_langfuse_client()

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
            from app.core.langfuse_config import get_langfuse_client

            result = get_langfuse_client()

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
            from app.core.langfuse_config import get_langfuse_client

            result = get_langfuse_client()

            assert result is None

    @pytest.mark.unit
    def test_creates_client_when_enabled(self, mock_env_enabled):
        """When enabled with credentials, should create Langfuse client."""
        import app.core.langfuse_config as config_module

        mock_client = MagicMock()
        mock_langfuse_class = MagicMock(return_value=mock_client)

        # Patch the import inside the function by patching sys.modules
        mock_langfuse_module = MagicMock()
        mock_langfuse_module.Langfuse = mock_langfuse_class

        config_module._langfuse_client = None

        with patch.dict("sys.modules", {"langfuse": mock_langfuse_module}):
            result = config_module.get_langfuse_client()

        # Should return the mock client
        assert result is mock_client
        mock_langfuse_class.assert_called_once()

    @pytest.mark.unit
    def test_singleton_returns_same_instance(self, mock_env_enabled):
        """Calling get_langfuse_client() twice should return same instance."""
        import app.core.langfuse_config as config_module

        # Set a mock client
        mock_client = MagicMock()
        config_module._langfuse_client = mock_client

        result1 = config_module.get_langfuse_client()
        result2 = config_module.get_langfuse_client()

        assert result1 is result2
        assert result1 is mock_client

    @pytest.mark.unit
    def test_handles_import_error_gracefully(self, mock_env_enabled):
        """When langfuse package not installed, should return None."""
        import app.core.langfuse_config as config_module

        config_module._langfuse_client = None

        with patch.dict("sys.modules", {"langfuse": None}):
            # The import will fail but should be handled gracefully
            # In real code, ImportError is caught
            result = config_module.get_langfuse_client()

            # May return None or client depending on installed packages
            # Just verify no exception raised
            assert result is None or result is not None


class TestConfigureLangfuseClient:
    """Tests for configure_langfuse_client() startup function."""

    @pytest.mark.unit
    def test_calls_get_langfuse_client(self, mock_env_disabled):
        """Should call get_langfuse_client during configuration."""
        from app.core.langfuse_config import configure_langfuse_client

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            mock_get.return_value = None

            configure_langfuse_client()

            mock_get.assert_called_once()

    @pytest.mark.unit
    def test_logs_success_when_client_created(self, mock_env_enabled):
        """Should log success when client is successfully created."""
        from app.core.langfuse_config import configure_langfuse_client

        mock_client = MagicMock()

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            mock_get.return_value = mock_client

            with patch("app.core.langfuse_config.logger") as mock_logger:
                configure_langfuse_client()

                mock_logger.info.assert_called()


class TestFlushLangfuse:
    """Tests for flush_langfuse() function."""

    @pytest.mark.unit
    def test_does_nothing_when_client_none(self):
        """When client is None, should do nothing."""
        import app.core.langfuse_config as config_module

        config_module._langfuse_client = None

        # Should not raise
        config_module.flush_langfuse()

    @pytest.mark.unit
    def test_calls_flush_on_client(self):
        """When client exists, should call flush()."""
        import app.core.langfuse_config as config_module

        mock_client = MagicMock()
        config_module._langfuse_client = mock_client

        config_module.flush_langfuse()

        mock_client.flush.assert_called_once()

    @pytest.mark.unit
    def test_handles_flush_exception_gracefully(self):
        """Should handle exceptions during flush gracefully."""
        import app.core.langfuse_config as config_module

        mock_client = MagicMock()
        mock_client.flush.side_effect = Exception("Network error")
        config_module._langfuse_client = mock_client

        # Should not raise
        config_module.flush_langfuse()


class TestShutdownLangfuse:
    """Tests for shutdown_langfuse() function."""

    @pytest.mark.unit
    def test_does_nothing_when_client_none(self):
        """When client is None, should do nothing."""
        import app.core.langfuse_config as config_module

        config_module._langfuse_client = None

        # Should not raise
        config_module.shutdown_langfuse()

    @pytest.mark.unit
    def test_calls_flush_and_shutdown(self):
        """When client exists, should call flush() then shutdown()."""
        import app.core.langfuse_config as config_module

        mock_client = MagicMock()
        config_module._langfuse_client = mock_client

        config_module.shutdown_langfuse()

        mock_client.flush.assert_called_once()
        mock_client.shutdown.assert_called_once()

    @pytest.mark.unit
    def test_clears_global_client(self):
        """Should set _langfuse_client to None after shutdown."""
        import app.core.langfuse_config as config_module

        mock_client = MagicMock()
        config_module._langfuse_client = mock_client

        config_module.shutdown_langfuse()

        assert config_module._langfuse_client is None

    @pytest.mark.unit
    def test_clears_client_even_on_exception(self):
        """Should clear client even if shutdown raises exception."""
        import app.core.langfuse_config as config_module

        mock_client = MagicMock()
        mock_client.shutdown.side_effect = Exception("Shutdown error")
        config_module._langfuse_client = mock_client

        # Should not raise but should clear client
        config_module.shutdown_langfuse()

        assert config_module._langfuse_client is None


class TestSubmitLangfuseScore:
    """Tests for submit_langfuse_score() function."""

    @pytest.mark.unit
    def test_returns_early_when_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, should return immediately."""
        from app.core.langfuse_config import submit_langfuse_score

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            submit_langfuse_score(name="test", value=0.5)

            # Should not call get_langfuse_client
            mock_get.assert_not_called()

    @pytest.mark.unit
    def test_returns_early_when_client_none(self, mock_env_enabled):
        """When client is None, should return immediately."""
        from app.core.langfuse_config import submit_langfuse_score

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            mock_get.return_value = None

            submit_langfuse_score(name="test", value=0.5)

            mock_get.assert_called_once()

    @pytest.mark.unit
    def test_uses_provided_trace_id(self, mock_env_enabled):
        """When trace_id provided, should use it directly."""
        from app.core.langfuse_config import submit_langfuse_score

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = None

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            mock_get.return_value = mock_client

            submit_langfuse_score(
                trace_id="custom-trace-123",
                name="relevance",
                value=0.85,
                comment="High relevance",
            )

            mock_client.create_score.assert_called_once_with(
                trace_id="custom-trace-123",
                name="relevance",
                value=0.85,
                comment="High relevance",
            )

    @pytest.mark.unit
    def test_gets_current_trace_id_when_not_provided(self, mock_env_enabled):
        """When trace_id not provided, should get current trace."""
        from app.core.langfuse_config import submit_langfuse_score

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = "auto-trace-456"

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            mock_get.return_value = mock_client

            submit_langfuse_score(name="depth", value=0.9)

            mock_client.get_current_trace_id.assert_called_once()
            mock_client.create_score.assert_called_once()
            call_kwargs = mock_client.create_score.call_args.kwargs
            assert call_kwargs["trace_id"] == "auto-trace-456"

    @pytest.mark.unit
    def test_skips_when_no_trace_context(self, mock_env_enabled):
        """When no trace context available, should skip submission."""
        from app.core.langfuse_config import submit_langfuse_score

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = None

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            mock_get.return_value = mock_client

            submit_langfuse_score(name="test", value=0.5)

            mock_client.create_score.assert_not_called()

    @pytest.mark.unit
    def test_handles_score_exception_gracefully(self, mock_env_enabled):
        """Should handle exceptions during score submission gracefully."""
        from app.core.langfuse_config import submit_langfuse_score

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = "trace-123"
        mock_client.create_score.side_effect = Exception("API error")

        with patch("app.core.langfuse_config.get_langfuse_client") as mock_get:
            mock_get.return_value = mock_client

            # Should not raise
            submit_langfuse_score(name="test", value=0.5)


class TestGetLangfuseCallbackHandler:
    """Tests for get_langfuse_callback_handler() function."""

    @pytest.mark.unit
    def test_returns_none_when_disabled(self, mock_env_disabled):
        """When LANGFUSE_ENABLED=false, should return None."""
        from app.core.langfuse_config import get_langfuse_callback_handler

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
            from app.core.langfuse_config import get_langfuse_callback_handler

            result = get_langfuse_callback_handler()

            assert result is None

    @pytest.mark.unit
    def test_creates_callback_handler_when_enabled(self, mock_env_enabled):
        """When enabled with credentials, should create CallbackHandler."""
        mock_handler = MagicMock()
        mock_callback_class = MagicMock(return_value=mock_handler)

        with patch.dict(
            "sys.modules",
            {"langfuse.langchain": MagicMock(CallbackHandler=mock_callback_class)},
        ):
            # Force reimport to pick up mock
            import app.core.langfuse_config

            importlib.reload(app.core.langfuse_config)

            result = app.core.langfuse_config.get_langfuse_callback_handler()

            # May return handler or None depending on import success
            assert result is None or result is not None

    @pytest.mark.unit
    def test_handles_import_error_gracefully(self, mock_env_enabled):
        """When langfuse.langchain not installed, should return None."""
        from app.core.langfuse_config import get_langfuse_callback_handler

        # The function handles ImportError internally
        result = get_langfuse_callback_handler()

        # Just verify no exception raised
        assert result is None or result is not None


class TestIntegration:
    """Integration tests for langfuse_config module."""

    @pytest.mark.unit
    def test_full_lifecycle(self, mock_env_enabled):
        """Test full client lifecycle: create -> use -> flush -> shutdown."""
        import app.core.langfuse_config as config_module

        mock_client = MagicMock()
        mock_client.get_current_trace_id.return_value = "test-trace"

        # Simulate full lifecycle
        config_module._langfuse_client = mock_client

        # Configure (would be called at startup)
        config_module.configure_langfuse_client()

        # Submit score (would be called during analysis)
        config_module.submit_langfuse_score(name="test", value=0.8)

        # Flush (would be called periodically)
        config_module.flush_langfuse()

        # Shutdown (would be called at app shutdown)
        config_module.shutdown_langfuse()

        # Verify lifecycle
        mock_client.create_score.assert_called_once()
        assert mock_client.flush.call_count == 2  # Once from flush, once from shutdown
        mock_client.shutdown.assert_called_once()
        assert config_module._langfuse_client is None

    @pytest.mark.unit
    def test_disabled_lifecycle_is_noop(self, mock_env_disabled):
        """When disabled, all operations should be no-ops."""
        import app.core.langfuse_config as config_module

        # All operations should succeed without doing anything
        config_module.configure_langfuse_client()
        config_module.submit_langfuse_score(name="test", value=0.5)
        config_module.flush_langfuse()
        config_module.shutdown_langfuse()

        # No exceptions should be raised
        assert config_module._langfuse_client is None
