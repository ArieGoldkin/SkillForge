"""Unit tests for provider configuration registry.

Tests the provider-specific configuration for multi-provider LLM support,
ensuring correct parameters are returned for each provider's streaming
and structured output requirements.
"""

import pytest

from app.core.provider_config import (
    PROVIDER_REGISTRY,
    ProviderConfig,
    get_config_for_provider,
    get_provider_for_model,
    get_streaming_kwargs,
    get_structured_output_kwargs,
    is_openai_compatible,
    supports_usage_in_stream,
)

# =============================================================================
# Tests for PROVIDER_REGISTRY
# =============================================================================


class TestProviderRegistry:
    """Tests for PROVIDER_REGISTRY contents."""

    def test_registry_contains_all_six_providers(self):
        """Verify all 6 providers are registered."""
        expected = {"openai", "anthropic", "google_genai", "xai", "deepseek", "ollama"}
        assert set(PROVIDER_REGISTRY.keys()) == expected

    def test_registry_values_are_provider_config(self):
        """Verify all registry values are ProviderConfig instances."""
        for provider, config in PROVIDER_REGISTRY.items():
            assert isinstance(config, ProviderConfig), f"{provider} is not ProviderConfig"

    def test_provider_config_is_frozen(self):
        """Verify ProviderConfig is immutable (frozen dataclass)."""
        config = PROVIDER_REGISTRY["openai"]
        with pytest.raises(AttributeError):
            config.supports_usage_in_stream = False  # type: ignore[misc]


class TestOpenAIConfig:
    """Tests for OpenAI provider configuration."""

    def test_openai_streaming_kwargs(self):
        """OpenAI should have stream_options for usage tracking."""
        config = PROVIDER_REGISTRY["openai"]
        assert config.streaming_kwargs == {"stream_options": {"include_usage": True}}

    def test_openai_structured_output_kwargs(self):
        """OpenAI should have strict=True for JSON mode."""
        config = PROVIDER_REGISTRY["openai"]
        assert config.structured_output_kwargs == {"strict": True}

    def test_openai_supports_usage_in_stream(self):
        """OpenAI supports usage_metadata in streaming chunks."""
        config = PROVIDER_REGISTRY["openai"]
        assert config.supports_usage_in_stream is True

    def test_openai_is_openai_compatible(self):
        """OpenAI is OpenAI-compatible (obviously)."""
        config = PROVIDER_REGISTRY["openai"]
        assert config.openai_compatible is True


class TestAnthropicConfig:
    """Tests for Anthropic provider configuration."""

    def test_anthropic_streaming_kwargs_empty(self):
        """Anthropic should have no streaming kwargs."""
        config = PROVIDER_REGISTRY["anthropic"]
        assert config.streaming_kwargs == {}

    def test_anthropic_structured_output_kwargs_empty(self):
        """Anthropic should have no structured output kwargs (no strict mode)."""
        config = PROVIDER_REGISTRY["anthropic"]
        assert config.structured_output_kwargs == {}

    def test_anthropic_no_usage_in_stream(self):
        """Anthropic doesn't provide usage in streaming chunks."""
        config = PROVIDER_REGISTRY["anthropic"]
        assert config.supports_usage_in_stream is False

    def test_anthropic_not_openai_compatible(self):
        """Anthropic is not OpenAI-compatible."""
        config = PROVIDER_REGISTRY["anthropic"]
        assert config.openai_compatible is False


class TestGoogleGenAIConfig:
    """Tests for Google GenAI (Gemini) provider configuration."""

    def test_google_genai_streaming_kwargs_empty(self):
        """Google GenAI should have no streaming kwargs."""
        config = PROVIDER_REGISTRY["google_genai"]
        assert config.streaming_kwargs == {}

    def test_google_genai_structured_output_kwargs_empty(self):
        """Google GenAI should have no structured output kwargs."""
        config = PROVIDER_REGISTRY["google_genai"]
        assert config.structured_output_kwargs == {}

    def test_google_genai_no_usage_in_stream(self):
        """Google GenAI doesn't provide usage in streaming chunks."""
        config = PROVIDER_REGISTRY["google_genai"]
        assert config.supports_usage_in_stream is False


class TestXAIConfig:
    """Tests for xAI (Grok) provider configuration."""

    def test_xai_streaming_kwargs_openai_compatible(self):
        """XAI should have OpenAI-compatible stream_options."""
        config = PROVIDER_REGISTRY["xai"]
        assert config.streaming_kwargs == {"stream_options": {"include_usage": True}}

    def test_xai_structured_output_kwargs_openai_compatible(self):
        """XAI should have OpenAI-compatible strict mode."""
        config = PROVIDER_REGISTRY["xai"]
        assert config.structured_output_kwargs == {"strict": True}

    def test_xai_supports_usage_in_stream(self):
        """XAI supports usage_metadata in streaming chunks."""
        config = PROVIDER_REGISTRY["xai"]
        assert config.supports_usage_in_stream is True

    def test_xai_is_openai_compatible(self):
        """XAI uses OpenAI-compatible API."""
        config = PROVIDER_REGISTRY["xai"]
        assert config.openai_compatible is True


class TestDeepSeekConfig:
    """Tests for DeepSeek provider configuration."""

    def test_deepseek_streaming_kwargs_openai_compatible(self):
        """DeepSeek should have OpenAI-compatible stream_options."""
        config = PROVIDER_REGISTRY["deepseek"]
        assert config.streaming_kwargs == {"stream_options": {"include_usage": True}}

    def test_deepseek_structured_output_kwargs_openai_compatible(self):
        """DeepSeek should have OpenAI-compatible strict mode."""
        config = PROVIDER_REGISTRY["deepseek"]
        assert config.structured_output_kwargs == {"strict": True}

    def test_deepseek_supports_usage_in_stream(self):
        """DeepSeek supports usage_metadata in streaming chunks."""
        config = PROVIDER_REGISTRY["deepseek"]
        assert config.supports_usage_in_stream is True

    def test_deepseek_is_openai_compatible(self):
        """DeepSeek uses OpenAI-compatible API."""
        config = PROVIDER_REGISTRY["deepseek"]
        assert config.openai_compatible is True


class TestOllamaConfig:
    """Tests for Ollama (local) provider configuration."""

    def test_ollama_streaming_kwargs_empty(self):
        """Ollama should have no streaming kwargs."""
        config = PROVIDER_REGISTRY["ollama"]
        assert config.streaming_kwargs == {}

    def test_ollama_structured_output_kwargs_empty(self):
        """Ollama should have no structured output kwargs."""
        config = PROVIDER_REGISTRY["ollama"]
        assert config.structured_output_kwargs == {}

    def test_ollama_no_usage_in_stream(self):
        """Ollama doesn't provide usage in streaming chunks."""
        config = PROVIDER_REGISTRY["ollama"]
        assert config.supports_usage_in_stream is False

    def test_ollama_not_openai_compatible(self):
        """Ollama is not OpenAI-compatible."""
        config = PROVIDER_REGISTRY["ollama"]
        assert config.openai_compatible is False


# =============================================================================
# Tests for get_streaming_kwargs()
# =============================================================================


class TestGetStreamingKwargs:
    """Tests for get_streaming_kwargs() function."""

    def test_openai_returns_stream_options(self):
        """OpenAI should return stream_options for usage tracking."""
        kwargs = get_streaming_kwargs("openai")
        assert kwargs == {"stream_options": {"include_usage": True}}

    def test_anthropic_returns_empty(self):
        """Anthropic should return empty dict (no streaming kwargs)."""
        kwargs = get_streaming_kwargs("anthropic")
        assert kwargs == {}

    def test_google_genai_returns_empty(self):
        """Google GenAI should return empty dict."""
        kwargs = get_streaming_kwargs("google_genai")
        assert kwargs == {}

    def test_xai_returns_stream_options(self):
        """XAI (OpenAI-compatible) should return stream_options."""
        kwargs = get_streaming_kwargs("xai")
        assert kwargs == {"stream_options": {"include_usage": True}}

    def test_deepseek_returns_stream_options(self):
        """DeepSeek (OpenAI-compatible) should return stream_options."""
        kwargs = get_streaming_kwargs("deepseek")
        assert kwargs == {"stream_options": {"include_usage": True}}

    def test_ollama_returns_empty(self):
        """Ollama should return empty dict."""
        kwargs = get_streaming_kwargs("ollama")
        assert kwargs == {}

    def test_none_provider_returns_empty(self):
        """None provider should return empty dict."""
        kwargs = get_streaming_kwargs(None)
        assert kwargs == {}

    def test_unknown_provider_returns_empty(self):
        """Unknown provider should return empty dict (safe default)."""
        kwargs = get_streaming_kwargs("unknown_provider")
        assert kwargs == {}

    def test_returns_copy_not_reference(self):
        """Should return a copy to prevent mutation of registry."""
        kwargs1 = get_streaming_kwargs("openai")
        kwargs2 = get_streaming_kwargs("openai")
        kwargs1["modified"] = True
        assert "modified" not in kwargs2

    def test_original_registry_unchanged_after_mutation(self):
        """Mutating returned kwargs should not affect registry."""
        kwargs = get_streaming_kwargs("openai")
        kwargs["stream_options"]["include_usage"] = False
        # Original should still be True
        original = PROVIDER_REGISTRY["openai"].streaming_kwargs
        assert original["stream_options"]["include_usage"] is True


# =============================================================================
# Tests for get_structured_output_kwargs()
# =============================================================================


class TestGetStructuredOutputKwargs:
    """Tests for get_structured_output_kwargs() function."""

    def test_openai_returns_strict(self):
        """OpenAI should return strict=True for JSON mode."""
        kwargs = get_structured_output_kwargs("openai")
        assert kwargs == {"strict": True}

    def test_anthropic_returns_empty(self):
        """Anthropic doesn't support strict mode."""
        kwargs = get_structured_output_kwargs("anthropic")
        assert kwargs == {}

    def test_google_genai_returns_empty(self):
        """Gemini doesn't support strict mode."""
        kwargs = get_structured_output_kwargs("google_genai")
        assert kwargs == {}

    def test_xai_returns_strict(self):
        """XAI (OpenAI-compatible) should return strict=True."""
        kwargs = get_structured_output_kwargs("xai")
        assert kwargs == {"strict": True}

    def test_deepseek_returns_strict(self):
        """DeepSeek (OpenAI-compatible) should return strict=True."""
        kwargs = get_structured_output_kwargs("deepseek")
        assert kwargs == {"strict": True}

    def test_ollama_returns_empty(self):
        """Ollama should return empty dict."""
        kwargs = get_structured_output_kwargs("ollama")
        assert kwargs == {}

    def test_none_provider_returns_empty(self):
        """None provider should return empty dict."""
        kwargs = get_structured_output_kwargs(None)
        assert kwargs == {}

    def test_unknown_provider_returns_empty(self):
        """Unknown provider should return empty dict (safe default)."""
        kwargs = get_structured_output_kwargs("unknown_provider")
        assert kwargs == {}

    def test_returns_copy_not_reference(self):
        """Should return a copy to prevent mutation of registry."""
        kwargs1 = get_structured_output_kwargs("openai")
        kwargs2 = get_structured_output_kwargs("openai")
        kwargs1["modified"] = True
        assert "modified" not in kwargs2


# =============================================================================
# Tests for supports_usage_in_stream()
# =============================================================================


class TestSupportsUsageInStream:
    """Tests for supports_usage_in_stream() function."""

    def test_openai_supports_usage(self):
        """OpenAI supports usage_metadata in streaming chunks."""
        assert supports_usage_in_stream("openai") is True

    def test_anthropic_no_usage(self):
        """Anthropic doesn't provide usage in streaming chunks."""
        assert supports_usage_in_stream("anthropic") is False

    def test_google_genai_no_usage(self):
        """Google GenAI doesn't provide usage in streaming chunks."""
        assert supports_usage_in_stream("google_genai") is False

    def test_xai_supports_usage(self):
        """XAI supports usage_metadata in streaming chunks."""
        assert supports_usage_in_stream("xai") is True

    def test_deepseek_supports_usage(self):
        """DeepSeek supports usage_metadata in streaming chunks."""
        assert supports_usage_in_stream("deepseek") is True

    def test_ollama_no_usage(self):
        """Ollama doesn't provide usage in streaming chunks."""
        assert supports_usage_in_stream("ollama") is False

    def test_none_provider_returns_false(self):
        """None provider should return False."""
        assert supports_usage_in_stream(None) is False

    def test_unknown_provider_returns_false(self):
        """Unknown provider should return False (safe default)."""
        assert supports_usage_in_stream("unknown_provider") is False


# =============================================================================
# Tests for is_openai_compatible()
# =============================================================================


class TestIsOpenAICompatible:
    """Tests for is_openai_compatible() function."""

    def test_openai_is_compatible(self):
        """OpenAI is OpenAI-compatible."""
        assert is_openai_compatible("openai") is True

    def test_anthropic_not_compatible(self):
        """Anthropic is not OpenAI-compatible."""
        assert is_openai_compatible("anthropic") is False

    def test_google_genai_not_compatible(self):
        """Google GenAI is not OpenAI-compatible."""
        assert is_openai_compatible("google_genai") is False

    def test_xai_is_compatible(self):
        """XAI uses OpenAI-compatible API."""
        assert is_openai_compatible("xai") is True

    def test_deepseek_is_compatible(self):
        """DeepSeek uses OpenAI-compatible API."""
        assert is_openai_compatible("deepseek") is True

    def test_ollama_not_compatible(self):
        """Ollama is not OpenAI-compatible."""
        assert is_openai_compatible("ollama") is False

    def test_none_provider_returns_false(self):
        """None provider should return False."""
        assert is_openai_compatible(None) is False


# =============================================================================
# Tests for get_provider_for_model()
# =============================================================================


class TestGetProviderForModel:
    """Tests for get_provider_for_model() function."""

    # OpenAI models
    def test_gpt_4o_returns_openai(self):
        """GPT-4o should resolve to OpenAI."""
        assert get_provider_for_model("gpt-4o") == "openai"

    def test_gpt_4o_mini_returns_openai(self):
        """GPT-4o-mini should resolve to OpenAI."""
        assert get_provider_for_model("gpt-4o-mini") == "openai"

    def test_gpt_5_returns_openai(self):
        """GPT-5 should resolve to OpenAI."""
        # Note: May use registry or prefix heuristic
        provider = get_provider_for_model("gpt-5")
        assert provider == "openai"

    def test_o3_mini_returns_openai(self):
        """o3-mini should resolve to OpenAI."""
        provider = get_provider_for_model("o3-mini")
        assert provider == "openai"

    # Anthropic models
    def test_claude_sonnet_returns_anthropic(self):
        """Claude Sonnet should resolve to Anthropic."""
        assert get_provider_for_model("claude-sonnet-4-20250514") == "anthropic"

    def test_claude_haiku_returns_anthropic(self):
        """Claude Haiku should resolve to Anthropic."""
        assert get_provider_for_model("claude-haiku-3-5-20241022") == "anthropic"

    def test_claude_opus_returns_anthropic(self):
        """Claude Opus should resolve to Anthropic."""
        assert get_provider_for_model("claude-opus-4-5-20251101") == "anthropic"

    # Google models
    def test_gemini_flash_returns_google(self):
        """Gemini Flash should resolve to Google GenAI."""
        assert get_provider_for_model("gemini-2.5-flash") == "google_genai"

    def test_gemini_pro_returns_google(self):
        """Gemini Pro should resolve to Google GenAI."""
        provider = get_provider_for_model("gemini-3-pro")
        assert provider == "google_genai"

    def test_gemini_3_flash_preview_returns_google(self):
        """Gemini 3 Flash Preview should resolve to Google GenAI."""
        provider = get_provider_for_model("gemini-3-flash-preview")
        assert provider == "google_genai"

    # xAI models
    def test_grok_3_returns_xai(self):
        """Grok 3 should resolve to xAI."""
        assert get_provider_for_model("grok-3") == "xai"

    def test_grok_4_fast_returns_xai(self):
        """Grok 4.1 Fast should resolve to xAI."""
        provider = get_provider_for_model("grok-4.1-fast")
        assert provider == "xai"

    # DeepSeek models
    def test_deepseek_v3_returns_deepseek(self):
        """DeepSeek V3 should resolve to DeepSeek."""
        assert get_provider_for_model("deepseek-v3") == "deepseek"

    def test_deepseek_reasoner_returns_deepseek(self):
        """DeepSeek Reasoner should resolve to DeepSeek."""
        provider = get_provider_for_model("deepseek-reasoner")
        assert provider == "deepseek"

    # Unknown models
    def test_unknown_model_returns_none(self):
        """Unknown models should return None."""
        assert get_provider_for_model("unknown-model-xyz") is None

    def test_empty_string_returns_none(self):
        """Empty string should return None."""
        assert get_provider_for_model("") is None

    # Case sensitivity
    def test_case_insensitive_prefix_matching(self):
        """Prefix matching should be case-insensitive."""
        assert get_provider_for_model("GPT-4o") == "openai"
        assert get_provider_for_model("Claude-Sonnet") == "anthropic"
        assert get_provider_for_model("GEMINI-flash") == "google_genai"


# =============================================================================
# Tests for get_config_for_provider()
# =============================================================================


class TestGetConfigForProvider:
    """Tests for get_config_for_provider() function."""

    def test_returns_config_for_known_provider(self):
        """Should return ProviderConfig for known providers."""
        config = get_config_for_provider("openai")
        assert isinstance(config, ProviderConfig)
        assert config.supports_usage_in_stream is True

    def test_returns_default_for_unknown_provider(self):
        """Should return default ProviderConfig for unknown providers."""
        config = get_config_for_provider("unknown_provider")
        assert isinstance(config, ProviderConfig)
        assert config.streaming_kwargs == {}
        assert config.structured_output_kwargs == {}
        assert config.supports_usage_in_stream is False

    def test_returns_default_for_none(self):
        """Should return default ProviderConfig for None."""
        config = get_config_for_provider(None)
        assert isinstance(config, ProviderConfig)
        assert config.streaming_kwargs == {}


# =============================================================================
# Integration Tests
# =============================================================================


class TestProviderConfigIntegration:
    """Integration tests for provider config usage patterns."""

    def test_streaming_call_pattern_openai(self):
        """Test typical streaming call pattern for OpenAI."""
        provider = get_provider_for_model("gpt-4o-mini")
        kwargs = get_streaming_kwargs(provider)

        # Simulate: async for chunk in model.astream(messages, **kwargs)
        assert "stream_options" in kwargs
        assert kwargs["stream_options"]["include_usage"] is True

    def test_streaming_call_pattern_anthropic(self):
        """Test typical streaming call pattern for Anthropic (no special kwargs)."""
        provider = get_provider_for_model("claude-sonnet-4-20250514")
        kwargs = get_streaming_kwargs(provider)

        # Anthropic doesn't need stream_options
        assert kwargs == {}

    def test_structured_output_pattern_openai(self):
        """Test typical structured output pattern for OpenAI."""
        provider = get_provider_for_model("gpt-4o-mini")
        kwargs = get_structured_output_kwargs(provider)

        # Simulate: model.with_structured_output(schema, **kwargs)
        assert kwargs == {"strict": True}

    def test_structured_output_pattern_gemini(self):
        """Test typical structured output pattern for Gemini (no strict)."""
        provider = get_provider_for_model("gemini-2.5-flash")
        kwargs = get_structured_output_kwargs(provider)

        # Gemini doesn't support strict mode
        assert kwargs == {}

    def test_openai_compatible_providers_share_config(self):
        """Test that OpenAI-compatible providers have same config."""
        openai_streaming = get_streaming_kwargs("openai")
        xai_streaming = get_streaming_kwargs("xai")
        deepseek_streaming = get_streaming_kwargs("deepseek")

        assert openai_streaming == xai_streaming == deepseek_streaming

        openai_structured = get_structured_output_kwargs("openai")
        xai_structured = get_structured_output_kwargs("xai")
        deepseek_structured = get_structured_output_kwargs("deepseek")

        assert openai_structured == xai_structured == deepseek_structured
