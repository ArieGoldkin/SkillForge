"""Utilities for initializing chat models with multi-provider support."""

from __future__ import annotations

from typing import Any

from langchain.chat_models import init_chat_model

from app.core.config import _infer_provider_from_model, _split_provider_from_model, settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _should_strip_provider_prefix(provider: str | None) -> bool:
    """Return True when provider prefix should be removed from model identifier."""
    if provider is None:
        return False
    return provider in {"openai", "anthropic", "google_genai"}


def get_chat_model(config: dict[str, Any] | None = None):  # noqa: PLR0912
    """Create a chat model instance using the configured provider/model.

    Supports runtime configuration via config parameter for model switching.
    Configures temperature, max_tokens, and timeout from settings.

    Args:
        config: Optional runtime config dict. If provided, can override model:
            - config.get("configurable", {}).get("model") - override model at runtime
            - config.get("configurable", {}).get("temperature") - override temperature
            - config.get("configurable", {}).get("max_tokens") - override max_tokens
            - config.get("configurable", {}).get("timeout") - override timeout

    Returns:
        Configured chat model instance that can be further customized via config
        at invocation time for runtime model switching.

    """
    # Check for runtime model override in config
    runtime_config = config.get("configurable", {}) if config else {}
    runtime_model = runtime_config.get("model")

    # Use runtime model if provided, otherwise use settings
    model_identifier = (runtime_model or settings.LLM_MODEL).strip()

    # Re-resolve provider/model if runtime model was provided
    if runtime_model:
        # Parse the runtime model to get provider/model
        provider, model_name = _split_provider_from_model(model_identifier)
        if not provider:
            provider = _infer_provider_from_model(model_identifier)
    else:
        provider = settings.resolved_llm_provider()
        model_name = settings.resolved_llm_model_name()

    init_kwargs: dict[str, str | float | int] = {}

    # Only pass model_provider when we have a canonical provider name
    if provider:
        init_kwargs["model_provider"] = provider

    # Add API keys based on provider
    if provider == "openai" and settings.OPENAI_API_KEY:
        init_kwargs["api_key"] = settings.OPENAI_API_KEY
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        init_kwargs["api_key"] = settings.ANTHROPIC_API_KEY
    elif provider == "google_genai" and settings.GOOGLE_API_KEY:
        init_kwargs["api_key"] = settings.GOOGLE_API_KEY
    elif provider == "xai" and settings.XAI_API_KEY:
        init_kwargs["api_key"] = settings.XAI_API_KEY
    elif provider == "deepseek" and settings.DEEPSEEK_API_KEY:
        init_kwargs["api_key"] = settings.DEEPSEEK_API_KEY

    # Add model parameters (runtime config overrides settings)
    temperature = runtime_config.get("temperature") if runtime_config else None
    if temperature is None:
        temperature = settings.LLM_TEMPERATURE
    if temperature is not None:
        init_kwargs["temperature"] = temperature

    max_tokens = runtime_config.get("max_tokens") if runtime_config else None
    if max_tokens is None:
        max_tokens = settings.LLM_MAX_TOKENS
    if max_tokens is not None:
        init_kwargs["max_tokens"] = max_tokens

    timeout = runtime_config.get("timeout") if runtime_config else None
    if timeout is None:
        timeout = settings.LLM_TIMEOUT
    if timeout is not None:
        init_kwargs["timeout"] = timeout

    # Remove provider prefix when LangChain expects bare model names
    if _should_strip_provider_prefix(provider):
        model_identifier_to_use = model_name
    else:
        # For custom providers (e.g., perplexity/composer), pass the raw identifier
        model_identifier_to_use = model_identifier

    logger.info(
        "chat_model_initializing",
        configured_model=model_identifier,
        resolved_model=model_identifier_to_use,
        provider=provider or "auto",
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        runtime_override=runtime_model is not None,
    )

    # Create configurable model that can be switched at invocation time
    # If no runtime model was provided, the model is still configurable via config at invoke time
    # LangChain's init_chat_model has complex overloads that mypy can't resolve
    return init_chat_model(model_identifier_to_use, **init_kwargs)  # type: ignore[call-overload]
