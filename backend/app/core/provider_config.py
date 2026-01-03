"""Provider-specific configuration for multi-provider LLM support.

This module centralizes provider-specific parameters that vary between
cloud providers (OpenAI, Anthropic, Google, xAI, DeepSeek) and local Ollama.

Architecture:
- Init-time params: Handled in model_factory.py (api_key, temperature, etc.)
- Call-time params: Handled here (stream_options, strict mode, etc.)

The separation ensures parameters are applied at the correct lifecycle stage:
- stream_options: Only for OpenAI streaming calls (not ainvoke)
- strict: Only for OpenAI structured output (not Gemini/Anthropic)

Example:
    >>> from app.core.provider_config import get_streaming_kwargs
    >>> kwargs = get_streaming_kwargs("openai")
    >>> async for chunk in model.astream(messages, **kwargs):
    ...     process(chunk)

Issue #637: Provider Configuration Registry for 2025/2026 best practices.

"""

import copy
from dataclasses import dataclass, field
from typing import Any, Final

from app.core.model_registry import MODEL_REGISTRY, Provider


@dataclass(frozen=True)
class ProviderConfig:
    """Immutable provider-specific configuration.

    Attributes:
        streaming_kwargs: Kwargs for astream() calls (e.g., stream_options)
        structured_output_kwargs: Kwargs for with_structured_output() (e.g., strict)
        supports_usage_in_stream: Whether provider returns usage_metadata in chunks
        openai_compatible: Whether provider uses OpenAI-compatible API patterns

    """

    streaming_kwargs: dict[str, Any] = field(default_factory=dict)
    structured_output_kwargs: dict[str, Any] = field(default_factory=dict)
    supports_usage_in_stream: bool = False
    openai_compatible: bool = False


# =============================================================================
# Shared Configuration Constants
# =============================================================================

# OpenAI-style streaming kwargs (reused by compatible providers)
_OPENAI_STREAMING_KWARGS: Final[dict[str, Any]] = {"stream_options": {"include_usage": True}}

_OPENAI_STRUCTURED_KWARGS: Final[dict[str, Any]] = {"strict": True}


# =============================================================================
# Provider Registry (Single Source of Truth)
# =============================================================================

PROVIDER_REGISTRY: Final[dict[Provider, ProviderConfig]] = {
    "openai": ProviderConfig(
        streaming_kwargs=_OPENAI_STREAMING_KWARGS,
        structured_output_kwargs=_OPENAI_STRUCTURED_KWARGS,
        supports_usage_in_stream=True,
        openai_compatible=True,
    ),
    "anthropic": ProviderConfig(
        # Anthropic: No streaming kwargs, usage from response_metadata
        streaming_kwargs={},
        structured_output_kwargs={},
        supports_usage_in_stream=False,
        openai_compatible=False,
    ),
    "google_genai": ProviderConfig(
        # Gemini: Different structured output chain, no strict mode
        streaming_kwargs={},
        structured_output_kwargs={},
        supports_usage_in_stream=False,
        openai_compatible=False,
    ),
    "xai": ProviderConfig(
        # xAI (Grok): OpenAI-compatible API
        streaming_kwargs=_OPENAI_STREAMING_KWARGS,
        structured_output_kwargs=_OPENAI_STRUCTURED_KWARGS,
        supports_usage_in_stream=True,
        openai_compatible=True,
    ),
    "deepseek": ProviderConfig(
        # DeepSeek: OpenAI-compatible API
        streaming_kwargs=_OPENAI_STREAMING_KWARGS,
        structured_output_kwargs=_OPENAI_STRUCTURED_KWARGS,
        supports_usage_in_stream=True,
        openai_compatible=True,
    ),
    "ollama": ProviderConfig(
        # Ollama: Local inference, no special streaming params
        streaming_kwargs={},
        structured_output_kwargs={},
        supports_usage_in_stream=False,
        openai_compatible=False,
    ),
}


# =============================================================================
# Public API Functions
# =============================================================================


def get_streaming_kwargs(provider: str | None) -> dict[str, Any]:
    """Get provider-specific kwargs for astream() calls.

    Args:
        provider: Provider name (openai, anthropic, google_genai, xai, deepseek, ollama)

    Returns:
        Dict of kwargs to pass to astream(). Empty dict for unknown providers.

    Example:
        >>> kwargs = get_streaming_kwargs("openai")
        >>> async for chunk in model.astream(messages, **kwargs):
        ...     process(chunk)

    """
    if provider is None:
        return {}
    config = PROVIDER_REGISTRY.get(provider, ProviderConfig())  # type: ignore[arg-type]
    return copy.deepcopy(config.streaming_kwargs)  # Deep copy for nested dicts


def get_structured_output_kwargs(provider: str | None) -> dict[str, Any]:
    """Get provider-specific kwargs for with_structured_output() calls.

    Args:
        provider: Provider name (openai, anthropic, google_genai, xai, deepseek, ollama)

    Returns:
        Dict of kwargs to pass to with_structured_output(). Empty for unknown providers.

    Note:
        - strict=True is OpenAI-specific (JSON mode with guaranteed schema compliance)
        - Gemini and Anthropic ignore this parameter silently
        - Providing strict=True to non-OpenAI providers can cause unexpected behavior

    Example:
        >>> kwargs = get_structured_output_kwargs("openai")
        >>> model.with_structured_output(schema, **kwargs)

    """
    if provider is None:
        return {}
    config = PROVIDER_REGISTRY.get(provider, ProviderConfig())  # type: ignore[arg-type]
    return copy.deepcopy(config.structured_output_kwargs)  # Deep copy for safety


def supports_usage_in_stream(provider: str | None) -> bool:
    """Check if provider returns usage_metadata in streaming chunks.

    Args:
        provider: Provider name

    Returns:
        True if provider includes token usage in streaming chunks, False otherwise.

    Note:
        - OpenAI, xAI, DeepSeek: Return usage in final chunk with stream_options
        - Anthropic: Usage only available in response_metadata after completion
        - Gemini: Usage available via response_metadata

    """
    if provider is None:
        return False
    config = PROVIDER_REGISTRY.get(provider, ProviderConfig())  # type: ignore[arg-type]
    return config.supports_usage_in_stream


def is_openai_compatible(provider: str | None) -> bool:
    """Check if provider uses OpenAI-compatible API patterns.

    Args:
        provider: Provider name

    Returns:
        True if provider uses OpenAI-compatible API (xAI, DeepSeek), False otherwise.

    """
    if provider is None:
        return False
    config = PROVIDER_REGISTRY.get(provider, ProviderConfig())  # type: ignore[arg-type]
    return config.openai_compatible


_PREFIX_TO_PROVIDER: Final[tuple[tuple[tuple[str, ...], str], ...]] = (
    (("gpt-", "o1", "o3"), "openai"),
    (("claude",), "anthropic"),
    (("gemini",), "google_genai"),
    (("grok",), "xai"),
    (("deepseek",), "deepseek"),
)


def get_provider_for_model(model_name: str) -> str | None:
    """Resolve provider from model name using registry lookup.

    Args:
        model_name: Model identifier (e.g., 'gpt-4o-mini', 'claude-sonnet-4-20250514')

    Returns:
        Provider name or None if unknown.

    Note:
        Uses MODEL_REGISTRY for exact matches, then falls back to prefix heuristics.

    Example:
        >>> get_provider_for_model("gpt-4o-mini")
        'openai'
        >>> get_provider_for_model("claude-sonnet-4-20250514")
        'anthropic'

    """
    # Check MODEL_REGISTRY first (exact match)
    if model_name in MODEL_REGISTRY:
        return MODEL_REGISTRY[model_name].provider

    # Fallback: Infer from model name prefix (case-insensitive)
    model_lower = model_name.lower()
    for prefixes, provider in _PREFIX_TO_PROVIDER:
        if model_lower.startswith(prefixes):
            return provider

    return None


def get_config_for_provider(provider: str | None) -> ProviderConfig:
    """Get full ProviderConfig for a provider.

    Args:
        provider: Provider name

    Returns:
        ProviderConfig instance (default empty config for unknown providers).

    """
    if provider is None:
        return ProviderConfig()
    return PROVIDER_REGISTRY.get(provider, ProviderConfig())  # type: ignore[arg-type]
