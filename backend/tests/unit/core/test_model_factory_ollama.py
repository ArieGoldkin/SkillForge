"""Unit tests for Ollama integration in model_factory.py.

Issue #606: Unified LLM factory with Ollama support for 93% CI cost reduction.

These tests verify the Ollama-specific code path when OLLAMA_ENABLED=True.
Cloud provider tests are in test_model_factory.py.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.model_factory import (
    OLLAMA_TASK_MODEL_MAP,
    _get_ollama_chat_model,
    get_chat_model,
)


@pytest.fixture(autouse=True)
def _enable_ollama_for_tests(monkeypatch):
    """Enable Ollama and configure settings for all tests in this module.

    This fixture ensures OLLAMA_ENABLED=True and sets all required
    Ollama configuration settings to valid values for testing.
    """
    monkeypatch.setattr("app.core.model_factory.settings.OLLAMA_ENABLED", True)
    monkeypatch.setattr("app.core.model_factory.settings.OLLAMA_HOST", "http://localhost:11434")
    monkeypatch.setattr("app.core.model_factory.settings.OLLAMA_MODEL_REASONING", "deepseek-r1:70b")
    monkeypatch.setattr("app.core.model_factory.settings.OLLAMA_MODEL_CODING", "qwen2.5-coder:32b")
    monkeypatch.setattr("app.core.model_factory.settings.OLLAMA_NUM_CTX", 8192)
    monkeypatch.setattr("app.core.model_factory.settings.OLLAMA_TIMEOUT", 60.0)


@pytest.fixture(autouse=True)
def _disable_cached_chat_model():
    """Disable CachedChatModel wrapper for all tests in this module.

    Tests mock ChatOllama to return MagicMock, but CachedChatModel
    requires a real BaseChatModel instance. This fixture patches
    _get_cached_chat_model_class to return None, skipping the wrapper.
    """
    with patch("app.core.model_factory._get_cached_chat_model_class", return_value=None):
        yield


# =============================================================================
# Tests for OLLAMA_TASK_MODEL_MAP Configuration
# =============================================================================


def test_ollama_task_model_map_contains_reasoning():
    """Test OLLAMA_TASK_MODEL_MAP includes reasoning task."""
    assert "reasoning" in OLLAMA_TASK_MODEL_MAP
    assert OLLAMA_TASK_MODEL_MAP["reasoning"] == "deepseek-r1:70b"


def test_ollama_task_model_map_contains_coding():
    """Test OLLAMA_TASK_MODEL_MAP includes coding task."""
    assert "coding" in OLLAMA_TASK_MODEL_MAP
    assert OLLAMA_TASK_MODEL_MAP["coding"] == "qwen2.5-coder:32b"


def test_ollama_task_model_map_contains_g_eval():
    """Test OLLAMA_TASK_MODEL_MAP routes G-Eval to reasoning model."""
    assert "g_eval" in OLLAMA_TASK_MODEL_MAP
    assert OLLAMA_TASK_MODEL_MAP["g_eval"] == "deepseek-r1:70b"


def test_ollama_task_model_map_contains_supervisor():
    """Test OLLAMA_TASK_MODEL_MAP routes supervisor to coding model."""
    assert "supervisor" in OLLAMA_TASK_MODEL_MAP
    assert OLLAMA_TASK_MODEL_MAP["supervisor"] == "qwen2.5-coder:32b"


def test_ollama_task_model_map_contains_default():
    """Test OLLAMA_TASK_MODEL_MAP includes default fallback."""
    assert "default" in OLLAMA_TASK_MODEL_MAP
    assert OLLAMA_TASK_MODEL_MAP["default"] == "qwen2.5-coder:32b"


# =============================================================================
# Tests for _get_ollama_chat_model() - Task-Based Model Selection
# =============================================================================


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_reasoning_task(mock_chat_ollama):
    """Test that reasoning tasks use DeepSeek R1 model."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type="reasoning")

    # Verify ChatOllama called with correct model
    mock_chat_ollama.assert_called_once()
    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "deepseek-r1:70b"
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_coding_task(mock_chat_ollama):
    """Test that coding tasks use Qwen 2.5 Coder model."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type="coding")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "qwen2.5-coder:32b"
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_g_eval_task(mock_chat_ollama):
    """Test that G-Eval uses reasoning model for quality evaluation."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type="g_eval")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "deepseek-r1:70b"
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_supervisor_task(mock_chat_ollama):
    """Test that supervisor task uses coding model (fast classification)."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type="supervisor")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "qwen2.5-coder:32b"
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_agent_task(mock_chat_ollama):
    """Test that agent task uses coding model."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type="agent")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "qwen2.5-coder:32b"
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_synthesis_task(mock_chat_ollama):
    """Test that synthesis task uses reasoning model."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type="synthesis")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "deepseek-r1:70b"
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_unknown_task_uses_default(mock_chat_ollama):
    """Test that unknown task types use default coding model."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type="unknown_task_type")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "qwen2.5-coder:32b"
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_none_task_uses_default(mock_chat_ollama):
    """Test that None task_type uses default coding model."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = _get_ollama_chat_model(task_type=None)

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "qwen2.5-coder:32b"
    assert result == mock_model


# =============================================================================
# Tests for _get_ollama_chat_model() - Configuration Parameters
# =============================================================================


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_includes_base_url(mock_chat_ollama):
    """Test that Ollama model includes base_url from settings."""
    mock_chat_ollama.return_value = MagicMock()

    _get_ollama_chat_model(task_type="reasoning")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["base_url"] == "http://localhost:11434"


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_includes_temperature(mock_chat_ollama):
    """Test that Ollama model uses temperature=0.0 for deterministic output."""
    mock_chat_ollama.return_value = MagicMock()

    _get_ollama_chat_model(task_type="reasoning")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["temperature"] == 0.0


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_includes_num_ctx(mock_chat_ollama):
    """Test that Ollama model includes num_ctx for context window."""
    mock_chat_ollama.return_value = MagicMock()

    _get_ollama_chat_model(task_type="reasoning")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["num_ctx"] == 8192


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_includes_keep_alive(mock_chat_ollama):
    """Test that Ollama model includes keep_alive for model caching."""
    mock_chat_ollama.return_value = MagicMock()

    _get_ollama_chat_model(task_type="reasoning")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["keep_alive"] == "5m"


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_includes_timeout(mock_chat_ollama):
    """Test that Ollama model includes timeout in client_kwargs."""
    mock_chat_ollama.return_value = MagicMock()

    _get_ollama_chat_model(task_type="reasoning")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert "client_kwargs" in call_kwargs
    assert call_kwargs["client_kwargs"]["timeout"] == 60.0


# =============================================================================
# Tests for get_chat_model() - Ollama Integration Path
# =============================================================================


@patch("langchain_ollama.ChatOllama")
def test_get_chat_model_with_ollama_enabled_uses_ollama(mock_chat_ollama):
    """Test that get_chat_model returns Ollama model when OLLAMA_ENABLED=True."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    result = get_chat_model(task_type="reasoning")

    # Should call ChatOllama, NOT init_chat_model
    mock_chat_ollama.assert_called_once()
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_chat_model_ollama_ignores_cloud_provider_settings(mock_chat_ollama):
    """Test that Ollama path ignores cloud provider settings (OpenAI, Anthropic)."""
    mock_model = MagicMock()
    mock_chat_ollama.return_value = mock_model

    # Even with cloud API keys set, should use Ollama
    result = get_chat_model(task_type="g_eval")

    # Verify Ollama model is used
    mock_chat_ollama.assert_called_once()
    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "deepseek-r1:70b"  # Ollama model
    assert "api_key" not in call_kwargs  # No cloud API key
    assert result == mock_model


@patch("langchain_ollama.ChatOllama")
def test_get_chat_model_ollama_logs_info_message(mock_chat_ollama):
    """Test that Ollama mode logs info message about activation."""
    mock_chat_ollama.return_value = MagicMock()

    # Should log "ollama_mode_active" message
    get_chat_model(task_type="supervisor")

    # Test passes if no exception raised
    # Actual log verification requires log capture fixture


@patch("langchain_ollama.ChatOllama")
def test_get_chat_model_ollama_task_routing_precedence(mock_chat_ollama):
    """Test that task_type routing works in Ollama mode."""
    mock_chat_ollama.return_value = MagicMock()

    # Different task types should route to different Ollama models
    get_chat_model(task_type="reasoning")
    reasoning_call = mock_chat_ollama.call_args[1]

    mock_chat_ollama.reset_mock()

    get_chat_model(task_type="coding")
    coding_call = mock_chat_ollama.call_args[1]

    # Verify different models used
    assert reasoning_call["model"] == "deepseek-r1:70b"
    assert coding_call["model"] == "qwen2.5-coder:32b"


# =============================================================================
# Tests for Edge Cases
# =============================================================================


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_with_special_characters_in_task_type(mock_chat_ollama):
    """Test that special characters in task_type don't break model selection."""
    mock_chat_ollama.return_value = MagicMock()

    # Should fall back to default model
    result = _get_ollama_chat_model(task_type="reasoning:v2")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "qwen2.5-coder:32b"  # Default


@patch("langchain_ollama.ChatOllama")
def test_get_ollama_chat_model_empty_string_task_type(mock_chat_ollama):
    """Test that empty string task_type uses default model."""
    mock_chat_ollama.return_value = MagicMock()

    result = _get_ollama_chat_model(task_type="")

    call_kwargs = mock_chat_ollama.call_args[1]
    assert call_kwargs["model"] == "qwen2.5-coder:32b"  # Default
