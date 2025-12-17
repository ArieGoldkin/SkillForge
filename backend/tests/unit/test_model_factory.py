"""Unit tests for model factory module."""

from unittest.mock import MagicMock, patch
import pytest

from app.core.model_factory import (
    TASK_MODEL_MAP,
    _get_redis_cache_for_model,
    _resolve_model_from_registry,
    _should_strip_provider_prefix,
    get_chat_model,
)

# =============================================================================
# Tests for _resolve_model_from_registry
# =============================================================================


def test_resolve_model_from_registry_found():
    """Test resolving a model that exists in the registry."""
    # claude-haiku-3-5-20241022 is a registry key that maps to a different model_id
    model_id, provider = _resolve_model_from_registry("claude-haiku-3-5-20241022")
    assert model_id == "claude-3-5-haiku-20241022"  # Actual API model ID
    assert provider == "anthropic"


def test_resolve_model_from_registry_not_found():
    """Test resolving a model not in the registry returns original."""
    model_id, provider = _resolve_model_from_registry("some-unknown-model")
    assert model_id == "some-unknown-model"
    assert provider is None


def test_resolve_model_from_registry_gemini():
    """Test resolving Gemini model from registry."""
    model_id, provider = _resolve_model_from_registry("gemini-2.5-flash")
    assert model_id == "gemini-2.5-flash"  # Stable name
    assert provider == "google_genai"


def test_resolve_model_from_registry_gpt():
    """Test resolving GPT model from registry."""
    model_id, provider = _resolve_model_from_registry("gpt-4o-mini")
    assert model_id == "gpt-4o-mini"
    assert provider == "openai"


def test_should_strip_provider_prefix_openai():
    """Test _should_strip_provider_prefix returns True for OpenAI."""
    assert _should_strip_provider_prefix("openai") is True


def test_should_strip_provider_prefix_anthropic():
    """Test _should_strip_provider_prefix returns True for Anthropic."""
    assert _should_strip_provider_prefix("anthropic") is True


def test_should_strip_provider_prefix_google_genai():
    """Test _should_strip_provider_prefix returns True for Google GenAI."""
    assert _should_strip_provider_prefix("google_genai") is True


def test_should_strip_provider_prefix_xai():
    """Test _should_strip_provider_prefix returns False for xAI (custom provider)."""
    assert _should_strip_provider_prefix("xai") is False


def test_should_strip_provider_prefix_deepseek():
    """Test _should_strip_provider_prefix returns False for DeepSeek (custom provider)."""
    assert _should_strip_provider_prefix("deepseek") is False


def test_should_strip_provider_prefix_none():
    """Test _should_strip_provider_prefix returns False for None."""
    assert _should_strip_provider_prefix(None) is False


def test_should_strip_provider_prefix_unknown():
    """Test _should_strip_provider_prefix returns False for unknown provider."""
    assert _should_strip_provider_prefix("unknown_provider") is False


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_openai(mock_settings, mock_init_chat_model):
    """Test get_chat_model with OpenAI provider."""
    # Setup mock settings
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None

    # Mock the chat model
    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify init_chat_model was called correctly
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["model_provider"] == "openai"
    assert call_kwargs["api_key"] == "sk-test-key"
    assert mock_init_chat_model.call_args[0][0] == "gpt-5-mini"  # Stripped model name
    assert result == mock_model


@patch("app.core.model_factory.ChatAnthropic")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_anthropic(
    mock_settings, mock_get_redis_cache, mock_chat_anthropic
):
    """Test get_chat_model with Anthropic provider uses ChatAnthropic directly."""
    # Setup mock settings
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.OPENAI_API_KEY = None
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None
    mock_get_redis_cache.return_value = None

    # Mock the chat model
    mock_model = MagicMock()
    mock_chat_anthropic.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify ChatAnthropic was called correctly (not init_chat_model)
    mock_chat_anthropic.assert_called_once()
    call_kwargs = mock_chat_anthropic.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4"
    assert call_kwargs["api_key"] == "sk-ant-test-key"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_xai(mock_settings, mock_init_chat_model):
    """Test get_chat_model with xAI provider (uses OpenAI-compatible API with custom base_url)."""
    # Setup mock settings
    mock_settings.LLM_MODEL = "xai:grok-3-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="xai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="grok-3-mini")
    mock_settings.OPENAI_API_KEY = None
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = "xai-test-key"
    mock_settings.DEEPSEEK_API_KEY = None

    # Mock the chat model
    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify init_chat_model was called correctly
    # xAI uses OpenAI-compatible API with custom base_url
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["model_provider"] == "openai"  # Uses OpenAI provider for compatibility
    assert call_kwargs["api_key"] == "xai-test-key"
    assert call_kwargs["base_url"] == "https://api.x.ai/v1"  # Custom xAI endpoint
    # xAI uses full identifier (not stripped since provider != openai/anthropic/google_genai)
    assert mock_init_chat_model.call_args[0][0] == "xai:grok-3-mini"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_deepseek(mock_settings, mock_init_chat_model):
    """Test get_chat_model with DeepSeek provider (custom provider, no prefix stripping)."""
    # Setup mock settings
    mock_settings.LLM_MODEL = "deepseek-v3:deepseek-chat"
    mock_settings.resolved_llm_provider = MagicMock(return_value="deepseek")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="deepseek-chat")
    mock_settings.OPENAI_API_KEY = None
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = "deepseek-test-key"

    # Mock the chat model
    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify init_chat_model was called correctly
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["model_provider"] == "deepseek"
    assert call_kwargs["api_key"] == "deepseek-test-key"
    # DeepSeek uses full identifier (not stripped)
    assert mock_init_chat_model.call_args[0][0] == "deepseek-v3:deepseek-chat"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_google_genai(mock_settings, mock_init_chat_model):
    """Test get_chat_model with Google GenAI provider."""
    # Setup mock settings
    mock_settings.LLM_MODEL = "gemini-2.0-flash"
    mock_settings.resolved_llm_provider = MagicMock(return_value="google_genai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gemini-2.0-flash")
    mock_settings.OPENAI_API_KEY = None
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = "google-test-key"
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None

    # Mock the chat model
    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify init_chat_model was called correctly
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["model_provider"] == "google_genai"
    assert call_kwargs["api_key"] == "google-test-key"
    assert mock_init_chat_model.call_args[0][0] == "gemini-2.0-flash"  # Stripped model name
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_without_provider(mock_settings, mock_init_chat_model):
    """Test get_chat_model with auto-detected provider (None)."""
    # Setup mock settings
    mock_settings.LLM_MODEL = "some-model"
    mock_settings.resolved_llm_provider = MagicMock(return_value=None)
    mock_settings.resolved_llm_model_name = MagicMock(return_value="some-model")
    mock_settings.OPENAI_API_KEY = None
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None

    # Mock the chat model
    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify init_chat_model was called correctly (no provider or API key)
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert "model_provider" not in call_kwargs
    assert "api_key" not in call_kwargs
    assert mock_init_chat_model.call_args[0][0] == "some-model"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_strips_whitespace(mock_settings, mock_init_chat_model):
    """Test get_chat_model strips whitespace from LLM_MODEL."""
    # Setup mock settings with whitespace in model name
    mock_settings.LLM_MODEL = "  gpt-5-mini  "
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None

    # Mock the chat model
    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify the model identifier passed to init_chat_model is stripped (no whitespace)
    call_args = mock_init_chat_model.call_args
    assert call_args is not None
    # First positional arg should be the model identifier (stripped)
    assert call_args[0][0] == "gpt-5-mini"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_missing_api_key(mock_settings, mock_init_chat_model):
    """Test get_chat_model when API key is not set (should raise error)."""
    # Setup mock settings with OpenAI but no API key
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = None  # Missing API key
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None

    # Mock the chat model
    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call get_chat_model
    result = get_chat_model()

    # Verify init_chat_model was called (API key won't be in kwargs if None)
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["model_provider"] == "openai"
    assert "api_key" not in call_kwargs  # Not added if None
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_temperature(mock_settings, mock_init_chat_model):
    """Test get_chat_model passes temperature parameter when configured."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_TEMPERATURE = 0.7
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    result = get_chat_model()

    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["temperature"] == 0.7
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_max_tokens(mock_settings, mock_init_chat_model):
    """Test get_chat_model passes max_tokens parameter when configured."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = 2000
    mock_settings.LLM_TIMEOUT = None

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    result = get_chat_model()

    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["max_tokens"] == 2000
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_timeout(mock_settings, mock_init_chat_model):
    """Test get_chat_model passes timeout parameter when configured."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = 60.0

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    result = get_chat_model()

    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["timeout"] == 60.0
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_all_parameters(mock_settings, mock_init_chat_model):
    """Test get_chat_model passes all model parameters when configured."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_TEMPERATURE = 0.8
    mock_settings.LLM_MAX_TOKENS = 1500
    mock_settings.LLM_TIMEOUT = 45.0

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    result = get_chat_model()

    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["temperature"] == 0.8
    assert call_kwargs["max_tokens"] == 1500
    assert call_kwargs["timeout"] == 45.0
    assert result == mock_model


# =============================================================================
# Tests for TASK_MODEL_MAP (Model Routing)
# =============================================================================


def test_task_model_map_contains_supervisor():
    """Test TASK_MODEL_MAP includes supervisor routing to Haiku."""
    assert "supervisor" in TASK_MODEL_MAP
    assert TASK_MODEL_MAP["supervisor"] == "claude-haiku-3-5-20241022"


def test_task_model_map_contains_g_eval():
    """Test TASK_MODEL_MAP includes g_eval routing to Gemini Flash."""
    assert "g_eval" in TASK_MODEL_MAP
    assert TASK_MODEL_MAP["g_eval"] == "gemini-3-flash"


def test_task_model_map_excludes_agents():
    """Test TASK_MODEL_MAP does not route agents (use default model)."""
    assert "agent" not in TASK_MODEL_MAP
    assert "synthesis" not in TASK_MODEL_MAP


@patch("app.core.model_factory.ChatAnthropic")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_task_routing_supervisor(
    mock_settings, mock_get_redis_cache, mock_chat_anthropic
):
    """Test get_chat_model routes supervisor task to Claude Haiku."""
    # Setup mock settings (default is Anthropic Sonnet)
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"
    mock_settings.OPENAI_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None
    mock_get_redis_cache.return_value = None

    mock_model = MagicMock()
    mock_chat_anthropic.return_value = mock_model

    # Call with supervisor task type
    result = get_chat_model(task_type="supervisor")

    # Verify ChatAnthropic was called with Haiku model
    mock_chat_anthropic.assert_called_once()
    call_kwargs = mock_chat_anthropic.call_args[1]
    # Should route to Haiku API model ID (after registry resolution)
    assert call_kwargs["model"] == "claude-3-5-haiku-20241022"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_task_routing_g_eval(
    mock_settings, mock_get_redis_cache, mock_init_chat_model
):
    """Test get_chat_model routes g_eval task to Gemini Flash."""
    # Setup mock settings (default is Anthropic Sonnet)
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.GOOGLE_API_KEY = "google-test-key"
    mock_settings.OPENAI_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None
    mock_get_redis_cache.return_value = None

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call with g_eval task type
    result = get_chat_model(task_type="g_eval")

    # Verify init_chat_model was called with Gemini model
    mock_init_chat_model.assert_called_once()
    # First positional arg should be gemini-3-flash
    assert mock_init_chat_model.call_args[0][0] == "gemini-3-flash"
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["model_provider"] == "google_genai"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_without_task_routing(
    mock_settings, mock_get_redis_cache, mock_init_chat_model
):
    """Test get_chat_model uses default model when no task_type provided."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None
    mock_get_redis_cache.return_value = None

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call without task_type
    result = get_chat_model()

    # Verify default model is used
    mock_init_chat_model.assert_called_once()
    assert mock_init_chat_model.call_args[0][0] == "gpt-5-mini"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_unknown_task_type_uses_default(
    mock_settings, mock_get_redis_cache, mock_init_chat_model
):
    """Test get_chat_model uses default model for unknown task_type."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None
    mock_get_redis_cache.return_value = None

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    # Call with unknown task_type
    result = get_chat_model(task_type="unknown_task")

    # Verify default model is used (not in TASK_MODEL_MAP)
    mock_init_chat_model.assert_called_once()
    assert mock_init_chat_model.call_args[0][0] == "gpt-5-mini"
    assert result == mock_model


# =============================================================================
# Tests for Redis Cache Integration
# =============================================================================


@patch("app.shared.services.cache.get_semantic_cache")
def test_get_redis_cache_for_model_success(mock_get_semantic_cache):
    """Test _get_redis_cache_for_model returns cache when available."""
    mock_cache = MagicMock()
    mock_get_semantic_cache.return_value = mock_cache

    result = _get_redis_cache_for_model()

    assert result == mock_cache
    mock_get_semantic_cache.assert_called_once()


@patch("app.shared.services.cache.get_semantic_cache")
def test_get_redis_cache_for_model_failure_returns_none(mock_get_semantic_cache):
    """Test _get_redis_cache_for_model returns None on Redis failure."""
    mock_get_semantic_cache.side_effect = Exception("Redis connection failed")

    result = _get_redis_cache_for_model()

    assert result is None


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_redis_cache(
    mock_settings, mock_get_redis_cache, mock_init_chat_model
):
    """Test get_chat_model includes Redis cache when available."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None

    mock_cache = MagicMock()
    mock_get_redis_cache.return_value = mock_cache

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    result = get_chat_model()

    # Verify cache is passed to init_chat_model
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["cache"] == mock_cache
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_without_redis_cache(
    mock_settings, mock_get_redis_cache, mock_init_chat_model
):
    """Test get_chat_model works without Redis cache."""
    mock_settings.LLM_MODEL = "gpt-5-mini"
    mock_settings.resolved_llm_provider = MagicMock(return_value="openai")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="gpt-5-mini")
    mock_settings.OPENAI_API_KEY = "sk-test-key"
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None

    mock_get_redis_cache.return_value = None  # Redis unavailable

    mock_model = MagicMock()
    mock_init_chat_model.return_value = mock_model

    result = get_chat_model()

    # Verify no cache is passed
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert "cache" not in call_kwargs
    assert result == mock_model


# =============================================================================
# Tests for Anthropic Prompt Caching
# =============================================================================


@patch("app.core.model_factory.ChatAnthropic")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_anthropic_with_5m_cache(
    mock_settings, mock_get_redis_cache, mock_chat_anthropic
):
    """Test Anthropic model with default 5m cache TTL (no beta header)."""
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"  # Default
    mock_settings.OPENAI_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None
    mock_get_redis_cache.return_value = None

    mock_model = MagicMock()
    mock_chat_anthropic.return_value = mock_model

    result = get_chat_model()

    # Verify ChatAnthropic called WITHOUT betas (5m uses default caching)
    mock_chat_anthropic.assert_called_once()
    call_kwargs = mock_chat_anthropic.call_args[1]
    assert "betas" not in call_kwargs
    assert call_kwargs["api_key"] == "sk-ant-test-key"
    assert result == mock_model


@patch("app.core.model_factory.ChatAnthropic")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_anthropic_with_1h_cache(
    mock_settings, mock_get_redis_cache, mock_chat_anthropic
):
    """Test Anthropic model with 1h extended cache TTL (requires beta header)."""
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "1h"  # Extended
    mock_settings.OPENAI_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None
    mock_get_redis_cache.return_value = None

    mock_model = MagicMock()
    mock_chat_anthropic.return_value = mock_model

    result = get_chat_model()

    # Verify ChatAnthropic called WITH betas for extended cache
    mock_chat_anthropic.assert_called_once()
    call_kwargs = mock_chat_anthropic.call_args[1]
    assert call_kwargs["betas"] == ["extended-cache-ttl-2025-04-11"]
    assert call_kwargs["api_key"] == "sk-ant-test-key"
    assert result == mock_model


@patch("app.core.model_factory.ChatAnthropic")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_anthropic_uses_chat_anthropic_class(
    mock_settings, mock_get_redis_cache, mock_chat_anthropic
):
    """Test that Anthropic provider uses ChatAnthropic class directly."""
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"
    mock_settings.OPENAI_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = 0.7
    mock_settings.LLM_MAX_TOKENS = 2000
    mock_settings.LLM_TIMEOUT = 60.0
    mock_settings.LLM_MAX_RETRIES = 3
    mock_get_redis_cache.return_value = None

    mock_model = MagicMock()
    mock_chat_anthropic.return_value = mock_model

    result = get_chat_model()

    # Verify ChatAnthropic was called (not init_chat_model)
    mock_chat_anthropic.assert_called_once()
    call_kwargs = mock_chat_anthropic.call_args[1]
    assert call_kwargs["model"] == "claude-sonnet-4"
    assert call_kwargs["api_key"] == "sk-ant-test-key"
    assert call_kwargs["temperature"] == 0.7
    assert call_kwargs["max_tokens"] == 2000
    assert call_kwargs["timeout"] == 60.0
    assert call_kwargs["max_retries"] == 3
    assert result == mock_model


@patch("app.core.model_factory.ChatAnthropic")
@patch("app.core.model_factory._get_redis_cache_for_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_anthropic_with_redis_cache(
    mock_settings, mock_get_redis_cache, mock_chat_anthropic
):
    """Test Anthropic model includes Redis cache when available."""
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"
    mock_settings.OPENAI_API_KEY = None
    mock_settings.GOOGLE_API_KEY = None
    mock_settings.XAI_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.LLM_TEMPERATURE = None
    mock_settings.LLM_MAX_TOKENS = None
    mock_settings.LLM_TIMEOUT = None
    mock_settings.LLM_MAX_RETRIES = None

    mock_cache = MagicMock()
    mock_get_redis_cache.return_value = mock_cache

    mock_model = MagicMock()
    mock_chat_anthropic.return_value = mock_model

    result = get_chat_model()

    # Verify Redis cache is passed to ChatAnthropic
    mock_chat_anthropic.assert_called_once()
    call_kwargs = mock_chat_anthropic.call_args[1]
    assert call_kwargs["cache"] == mock_cache
    assert result == mock_model
