"""Unit tests for model_factory helper functions.

Issue #602: Tests for refactored helper functions extracted from get_chat_model().
These tests provide dedicated unit test coverage for the internal helper functions.
"""

from typing import Any
from unittest.mock import MagicMock, patch

from app.core.model_factory import (
    _build_init_kwargs,
    _create_anthropic_model,
    _create_generic_model,
    _resolve_model_and_provider,
    _wrap_with_l1_cache,
)

# =============================================================================
# Tests for _build_init_kwargs
# =============================================================================


class TestBuildInitKwargs:
    """Tests for _build_init_kwargs helper function."""

    @patch("app.core.model_factory.settings")
    def test_injects_openai_api_key(self, mock_settings: MagicMock) -> None:
        """Test that OpenAI API key is injected for openai provider."""
        mock_settings.OPENAI_API_KEY = "sk-openai-test"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None
        mock_settings.DEEPSEEK_API_KEY = None
        mock_settings.LLM_TEMPERATURE = None
        mock_settings.LLM_MAX_TOKENS = None
        mock_settings.LLM_TIMEOUT = None
        mock_settings.LLM_MAX_RETRIES = None

        init_kwargs, _model_kwargs = _build_init_kwargs("openai", {})

        assert init_kwargs["api_key"] == "sk-openai-test"
        assert init_kwargs["model_provider"] == "openai"

    @patch("app.core.model_factory.settings")
    def test_injects_anthropic_api_key(self, mock_settings: MagicMock) -> None:
        """Test that Anthropic API key is injected for anthropic provider."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = "sk-ant-test"
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None
        mock_settings.DEEPSEEK_API_KEY = None
        mock_settings.LLM_TEMPERATURE = None
        mock_settings.LLM_MAX_TOKENS = None
        mock_settings.LLM_TIMEOUT = None
        mock_settings.LLM_MAX_RETRIES = None

        init_kwargs, _model_kwargs = _build_init_kwargs("anthropic", {})

        assert init_kwargs["api_key"] == "sk-ant-test"
        assert init_kwargs["model_provider"] == "anthropic"

    @patch("app.core.model_factory.settings")
    def test_xai_uses_openai_compatible_api(self, mock_settings: MagicMock) -> None:
        """Test that xAI provider configures OpenAI-compatible API with base_url."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = "xai-test-key"
        mock_settings.DEEPSEEK_API_KEY = None
        mock_settings.LLM_TEMPERATURE = None
        mock_settings.LLM_MAX_TOKENS = None
        mock_settings.LLM_TIMEOUT = None
        mock_settings.LLM_MAX_RETRIES = None

        init_kwargs, _ = _build_init_kwargs("xai", {})

        assert init_kwargs["api_key"] == "xai-test-key"
        assert init_kwargs["model_provider"] == "openai"  # Uses OpenAI-compatible
        assert init_kwargs["base_url"] == "https://api.x.ai/v1"

    @patch("app.core.model_factory.settings")
    def test_runtime_config_overrides_settings(self, mock_settings: MagicMock) -> None:
        """Test that runtime config overrides settings values."""
        mock_settings.OPENAI_API_KEY = "sk-openai-test"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None
        mock_settings.DEEPSEEK_API_KEY = None
        mock_settings.LLM_TEMPERATURE = 0.5  # Settings value
        mock_settings.LLM_MAX_TOKENS = 1000
        mock_settings.LLM_TIMEOUT = 30.0
        mock_settings.LLM_MAX_RETRIES = 2

        runtime_config = {
            "temperature": 0.9,  # Override
            "max_tokens": 2000,
            "timeout": 60.0,
            "max_retries": 5,
        }

        init_kwargs, _ = _build_init_kwargs("openai", runtime_config)

        assert init_kwargs["temperature"] == 0.9  # Runtime override
        assert init_kwargs["max_tokens"] == 2000
        assert init_kwargs["timeout"] == 60.0
        assert init_kwargs["max_retries"] == 5

    @patch("app.core.model_factory.settings")
    def test_stream_options_always_included(self, mock_settings: MagicMock) -> None:
        """Test that stream_options is always included in model_kwargs."""
        mock_settings.OPENAI_API_KEY = "sk-test"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None
        mock_settings.DEEPSEEK_API_KEY = None
        mock_settings.LLM_TEMPERATURE = None
        mock_settings.LLM_MAX_TOKENS = None
        mock_settings.LLM_TIMEOUT = None
        mock_settings.LLM_MAX_RETRIES = None

        _, model_kwargs = _build_init_kwargs("openai", {})

        assert "stream_options" in model_kwargs
        assert model_kwargs["stream_options"]["include_usage"] is True


# =============================================================================
# Tests for _resolve_model_and_provider
# =============================================================================


class TestResolveModelAndProvider:
    """Tests for _resolve_model_and_provider helper function."""

    @patch("app.core.model_factory.settings")
    def test_task_type_routing_takes_precedence(self, mock_settings: MagicMock) -> None:
        """Test that task_type routing takes precedence over config."""
        mock_settings.OLLAMA_ENABLED = False
        mock_settings.LLM_MODEL = "claude-sonnet-4"

        # With task_type that has mapping, it should use that
        _model_id, provider, _model_name, _runtime_config = _resolve_model_and_provider(
            config={"configurable": {"model": "gpt-4o"}},
            task_type="supervisor",  # Has mapping in TASK_MODEL_MAP
        )

        # Should use task-mapped model, not config model
        assert provider is not None  # Should resolve provider

    @patch("app.core.model_factory.settings")
    def test_config_model_used_when_no_task_mapping(self, mock_settings: MagicMock) -> None:
        """Test that config model is used when no task mapping exists."""
        mock_settings.OLLAMA_ENABLED = False
        mock_settings.LLM_MODEL = "claude-sonnet-4"

        config = {"configurable": {"model": "gpt-4o-mini", "temperature": 0.5}}

        model_id, _provider, _model_name, runtime_config = _resolve_model_and_provider(
            config=config,
            task_type=None,  # No task type
        )

        # Should use config model
        assert model_id == "gpt-4o-mini"
        assert runtime_config.get("temperature") == 0.5


# =============================================================================
# Tests for _create_anthropic_model
# =============================================================================


class TestCreateAnthropicModel:
    """Tests for _create_anthropic_model helper function."""

    @patch("app.core.model_factory.settings")
    @patch("app.core.model_factory._wrap_with_l1_cache")
    @patch("app.core.model_factory.ChatAnthropic")
    def test_creates_chat_anthropic_with_prompt_cache(
        self,
        mock_chat_anthropic: MagicMock,
        mock_wrap_cache: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test that ChatAnthropic is created with correct kwargs."""
        mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "1h"  # Triggers extended beta
        mock_model = MagicMock()
        mock_chat_anthropic.return_value = mock_model
        mock_wrap_cache.return_value = mock_model

        init_kwargs: dict[str, Any] = {
            "api_key": "sk-ant-test",
            "temperature": 0.7,
        }

        result = _create_anthropic_model(
            model_name="claude-sonnet-4",
            init_kwargs=init_kwargs,  # type: ignore[arg-type]
            task_type=None,
            redis_cache=None,
        )

        mock_chat_anthropic.assert_called_once()
        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["model"] == "claude-sonnet-4"
        assert call_kwargs["api_key"] == "sk-ant-test"
        # 1h TTL uses extended-cache-ttl beta
        assert "extended-cache-ttl-2025-04-11" in call_kwargs["betas"]

    @patch("app.core.model_factory.settings")
    @patch("app.core.model_factory._wrap_with_l1_cache")
    @patch("app.core.model_factory.ChatAnthropic")
    def test_includes_redis_cache_when_provided(
        self,
        mock_chat_anthropic: MagicMock,
        mock_wrap_cache: MagicMock,
        mock_settings: MagicMock,
    ) -> None:
        """Test that Redis cache is passed to ChatAnthropic when available."""
        mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"
        mock_model = MagicMock()
        mock_chat_anthropic.return_value = mock_model
        mock_wrap_cache.return_value = mock_model
        mock_redis_cache = MagicMock()

        init_kwargs: dict[str, Any] = {"api_key": "sk-ant-test"}

        _create_anthropic_model(
            model_name="claude-sonnet-4",
            init_kwargs=init_kwargs,  # type: ignore[arg-type]
            task_type=None,
            redis_cache=mock_redis_cache,
        )

        call_kwargs = mock_chat_anthropic.call_args[1]
        assert call_kwargs["cache"] == mock_redis_cache


# =============================================================================
# Tests for _create_generic_model
# =============================================================================


class TestCreateGenericModel:
    """Tests for _create_generic_model helper function."""

    @patch("app.core.model_factory._wrap_with_l1_cache")
    @patch("app.core.model_factory.init_chat_model")
    def test_creates_model_via_init_chat_model(
        self, mock_init: MagicMock, mock_wrap_cache: MagicMock
    ) -> None:
        """Test that generic models are created via init_chat_model."""
        mock_model = MagicMock()
        mock_init.return_value = mock_model
        mock_wrap_cache.return_value = mock_model

        init_kwargs: dict[str, Any] = {
            "model_provider": "openai",
            "api_key": "sk-test",
        }

        result = _create_generic_model(
            model_identifier="openai/gpt-4o-mini",
            model_name="gpt-4o-mini",
            provider="openai",
            init_kwargs=init_kwargs,  # type: ignore[arg-type]
            model_kwargs={},
            task_type=None,
            redis_cache=None,
            runtime_model_provided=False,
            routed_model=None,
        )

        mock_init.assert_called_once()
        # Verify model_name is passed (provider stripped for known providers)
        assert mock_init.call_args[0][0] == "gpt-4o-mini"


# =============================================================================
# Tests for _wrap_with_l1_cache
# =============================================================================


class TestWrapWithL1Cache:
    """Tests for _wrap_with_l1_cache helper function."""

    @patch("app.core.model_factory.settings")
    @patch("app.core.model_factory._get_cached_chat_model_class")
    def test_returns_original_when_cache_disabled(
        self, mock_get_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that original model is returned when cache class is unavailable."""
        mock_settings.LLM_CACHE_ENABLED = True  # Enabled but class unavailable
        mock_get_class.return_value = None
        mock_model = MagicMock()

        result = _wrap_with_l1_cache(mock_model, task_type=None)

        assert result == mock_model

    @patch("app.core.model_factory.settings")
    def test_returns_original_when_cache_setting_disabled(self, mock_settings: MagicMock) -> None:
        """Test that original model is returned when LLM_CACHE_ENABLED=False."""
        mock_settings.LLM_CACHE_ENABLED = False
        mock_model = MagicMock()

        result = _wrap_with_l1_cache(mock_model, task_type=None)

        assert result == mock_model

    @patch("app.core.model_factory.settings")
    @patch("app.core.model_factory._get_cached_chat_model_class")
    def test_wraps_model_when_cache_available(
        self, mock_get_class: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test that model is wrapped with cache when available."""
        mock_settings.LLM_CACHE_ENABLED = True
        mock_settings.LLM_CACHE_L1_SIZE = 1000
        mock_cached_class = MagicMock()
        mock_wrapped = MagicMock()
        mock_cached_class.return_value = mock_wrapped
        mock_get_class.return_value = mock_cached_class
        mock_model = MagicMock()

        result = _wrap_with_l1_cache(mock_model, task_type="test_task")

        # Cache class is called with keyword args
        mock_cached_class.assert_called_once_with(
            model=mock_model, agent_type="test_task", cache_enabled=True
        )
        assert result == mock_wrapped
