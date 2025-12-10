"""Unit tests for model factory module."""

from unittest.mock import MagicMock, patch

from app.core.model_factory import (
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


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_anthropic(mock_settings, mock_init_chat_model):
    """Test get_chat_model with Anthropic provider."""
    # Setup mock settings
    mock_settings.LLM_MODEL = "claude-sonnet-4"
    mock_settings.resolved_llm_provider = MagicMock(return_value="anthropic")
    mock_settings.resolved_llm_model_name = MagicMock(return_value="claude-sonnet-4")
    mock_settings.OPENAI_API_KEY = None
    mock_settings.ANTHROPIC_API_KEY = "sk-ant-test-key"
    mock_settings.GOOGLE_API_KEY = None
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
    assert call_kwargs["model_provider"] == "anthropic"
    assert call_kwargs["api_key"] == "sk-ant-test-key"
    assert result == mock_model


@patch("app.core.model_factory.init_chat_model")
@patch("app.core.model_factory.settings")
def test_get_chat_model_with_xai(mock_settings, mock_init_chat_model):
    """Test get_chat_model with xAI provider (custom provider, no prefix stripping)."""
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
    mock_init_chat_model.assert_called_once()
    call_kwargs = mock_init_chat_model.call_args[1]
    assert call_kwargs["model_provider"] == "xai"
    assert call_kwargs["api_key"] == "xai-test-key"
    # xAI uses full identifier (not stripped)
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
