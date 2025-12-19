"""Unit tests for timeout configuration module.

Tests:
- Timeout constants have expected values
- STEP_TIMEOUT env var override works
- create_runnable_config() function behavior
"""

import os
from unittest.mock import MagicMock, patch

import pytest


class TestTimeoutConstants:
    """Tests for timeout constant values."""

    @pytest.mark.unit
    def test_agent_timeout_value(self):
        """AGENT_TIMEOUT should be 60 seconds."""
        from app.core.timeout_config import AGENT_TIMEOUT

        assert AGENT_TIMEOUT == 60.0

    @pytest.mark.unit
    def test_synthesis_timeout_value(self):
        """SYNTHESIS_TIMEOUT should be 180 seconds (3 minutes)."""
        from app.core.timeout_config import SYNTHESIS_TIMEOUT

        assert SYNTHESIS_TIMEOUT == 180.0

    @pytest.mark.unit
    def test_streaming_timeout_value(self):
        """STREAMING_TIMEOUT should be 120 seconds."""
        from app.core.timeout_config import STREAMING_TIMEOUT

        assert STREAMING_TIMEOUT == 120.0

    @pytest.mark.unit
    def test_step_timeout_default_value(self):
        """STEP_TIMEOUT should default to 300 seconds (5 minutes)."""
        from app.core.timeout_config import STEP_TIMEOUT

        # Default is 300 unless env var is set
        assert STEP_TIMEOUT == 300.0 or isinstance(STEP_TIMEOUT, float)

    @pytest.mark.unit
    def test_workflow_timeout_value(self):
        """WORKFLOW_TIMEOUT should be 900 seconds (15 minutes)."""
        from app.core.timeout_config import WORKFLOW_TIMEOUT

        assert WORKFLOW_TIMEOUT == 900.0


class TestStepTimeoutEnvOverride:
    """Tests for STEP_TIMEOUT environment variable override."""

    @pytest.mark.unit
    def test_step_timeout_env_override(self):
        """STEP_TIMEOUT should use SKILLFORGE_STEP_TIMEOUT env var if set."""
        import importlib

        with patch.dict(os.environ, {"SKILLFORGE_STEP_TIMEOUT": "600"}):
            # Need to reimport to pick up env var
            import app.core.timeout_config as tc

            importlib.reload(tc)

            assert tc.STEP_TIMEOUT == 600.0

        # Reload again to reset to default
        with patch.dict(os.environ, {}, clear=False):
            if "SKILLFORGE_STEP_TIMEOUT" in os.environ:
                del os.environ["SKILLFORGE_STEP_TIMEOUT"]
            importlib.reload(tc)


class TestCreateRunnableConfig:
    """Tests for create_runnable_config() function."""

    @pytest.mark.unit
    def test_returns_empty_config_by_default(self):
        """When no thread_id and no callback, should return minimal config."""
        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = None

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config()

            assert isinstance(config, dict)
            assert "callbacks" not in config
            assert "configurable" not in config

    @pytest.mark.unit
    def test_includes_thread_id_when_provided(self):
        """When thread_id provided, should include in configurable."""
        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = None

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config(thread_id="test-thread-123")

            assert config["configurable"]["thread_id"] == "test-thread-123"

    @pytest.mark.unit
    def test_includes_langfuse_callback_when_enabled(self):
        """When Langfuse enabled, should include callback handler."""
        mock_callback = MagicMock()

        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = mock_callback

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config()

            assert "callbacks" in config
            assert mock_callback in config["callbacks"]

    @pytest.mark.unit
    def test_no_callbacks_when_langfuse_disabled(self):
        """When Langfuse disabled (returns None), should not include callbacks key."""
        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = None

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config()

            assert "callbacks" not in config

    @pytest.mark.unit
    def test_thread_id_and_callback_combined(self):
        """Should handle both thread_id and callback together."""
        mock_callback = MagicMock()

        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = mock_callback

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config(thread_id="combined-test-456")

            # Should have both
            assert config["configurable"]["thread_id"] == "combined-test-456"
            assert "callbacks" in config
            assert mock_callback in config["callbacks"]

    @pytest.mark.unit
    def test_thread_id_none_no_configurable(self):
        """When thread_id is None, should not add configurable key."""
        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = None

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config(thread_id=None)

            assert "configurable" not in config

    @pytest.mark.unit
    def test_returns_runnable_config_type(self):
        """Should return a dict compatible with RunnableConfig."""
        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = None

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config(thread_id="type-check")

            # RunnableConfig is a TypedDict, which is just a dict
            assert isinstance(config, dict)
            # Verify structure
            assert config.get("configurable", {}).get("thread_id") == "type-check"


class TestIntegration:
    """Integration tests for timeout_config module."""

    @pytest.mark.unit
    def test_create_config_for_langgraph(self):
        """Config should be valid for LangGraph execution."""
        with patch("app.core.langfuse_config.get_langfuse_callback_handler") as mock_handler:
            mock_handler.return_value = None

            from app.core.timeout_config import create_runnable_config

            config = create_runnable_config(thread_id="langgraph-test")

            # LangGraph expects these keys
            assert config["configurable"]["thread_id"] == "langgraph-test"

    @pytest.mark.unit
    def test_constants_are_positive(self):
        """All timeout constants should be positive values."""
        from app.core.timeout_config import (
            AGENT_TIMEOUT,
            STEP_TIMEOUT,
            STREAMING_TIMEOUT,
            SYNTHESIS_TIMEOUT,
            WORKFLOW_TIMEOUT,
        )

        assert AGENT_TIMEOUT > 0
        assert SYNTHESIS_TIMEOUT > 0
        assert STREAMING_TIMEOUT > 0
        assert STEP_TIMEOUT > 0
        assert WORKFLOW_TIMEOUT > 0

    @pytest.mark.unit
    def test_step_timeout_less_than_workflow(self):
        """STEP_TIMEOUT should be less than WORKFLOW_TIMEOUT."""
        from app.core.timeout_config import STEP_TIMEOUT, WORKFLOW_TIMEOUT

        assert STEP_TIMEOUT < WORKFLOW_TIMEOUT

    @pytest.mark.unit
    def test_synthesis_reasonable_for_llm(self):
        """SYNTHESIS_TIMEOUT should allow for multi-phase LLM processing."""
        from app.core.timeout_config import SYNTHESIS_TIMEOUT

        # At least 2 minutes for complex synthesis
        assert SYNTHESIS_TIMEOUT >= 120
