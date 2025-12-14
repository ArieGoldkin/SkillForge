"""Utilities for initializing chat models with multi-provider support."""

from __future__ import annotations

from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import _infer_provider_from_model, _split_provider_from_model, settings
from app.core.logging import get_logger
from app.core.model_registry import MODEL_REGISTRY

logger = get_logger(__name__)


def _resolve_model_from_registry(model_key: str) -> tuple[str, str | None]:
    """Resolve a model registry key to its actual API model_id and provider.

    The MODEL_REGISTRY uses human-friendly keys (e.g., "claude-haiku-3-5-20241022")
    that may differ from actual API model IDs (e.g., "claude-3-5-haiku-20241022").

    Args:
        model_key: Either a registry key or a raw model identifier

    Returns:
        Tuple of (resolved_model_id, provider_or_none)
        If model_key is in registry, returns the model_id and provider from registry.
        If not in registry, returns the original model_key and None.

    """
    if model_key in MODEL_REGISTRY:
        info = MODEL_REGISTRY[model_key]
        logger.debug(
            "model_registry_resolved",
            registry_key=model_key,
            api_model_id=info.model_id,
            provider=info.provider,
        )
        return info.model_id, info.provider
    return model_key, None


def _should_strip_provider_prefix(provider: str | None) -> bool:
    """Return True when provider prefix should be removed from model identifier."""
    if provider is None:
        return False
    return provider in {"openai", "anthropic", "google_genai"}


def get_chat_model(config: dict[str, dict[str, object]] | None = None) -> BaseChatModel:  # noqa: PLR0912, PLR0915
    """Create a chat model instance using the configured provider/model.

    Supports runtime configuration via config parameter for model switching.
    Configures temperature, max_tokens, timeout, and max_retries from settings.
    Uses LangChain's built-in retry mechanism (max_retries) for automatic retry handling.

    Args:
        config: Optional runtime config dict. If provided, can override model:
            - config.get("configurable", {}).get("model") - override model at runtime
            - config.get("configurable", {}).get("temperature") - override temperature
            - config.get("configurable", {}).get("max_tokens") - override max_tokens
            - config.get("configurable", {}).get("timeout") - override timeout
            - config.get("configurable", {}).get("max_retries") - override max_retries

    Returns:
        Configured chat model instance that can be further customized via config
        at invocation time for runtime model switching.

    Note:
        LangChain's built-in retry (max_retries) handles retries automatically with
        proper async behavior. The timeout parameter applies to both streaming and
        non-streaming calls. Timeout is enforced at the model level by LangChain.

    """
    # Check for runtime model override in config
    runtime_config: dict[str, object] = config.get("configurable", {}) if config else {}  # type: ignore[union-attr]
    runtime_model = runtime_config.get("model")

    # Use runtime model if provided, otherwise use settings
    model_identifier_raw = runtime_model or settings.LLM_MODEL
    model_identifier = str(model_identifier_raw).strip()

    # Re-resolve provider/model if runtime model was provided
    provider: str | None = None
    model_name: str = ""
    if runtime_model:
        # First, check if this is a registry key that needs resolution
        # Registry keys may differ from actual API model IDs
        # (e.g., "claude-haiku-3-5-20241022" -> "claude-3-5-haiku-20241022")
        resolved_model_id, registry_provider = _resolve_model_from_registry(model_identifier)

        if registry_provider:
            # Model was found in registry - use registry values
            provider = registry_provider
            model_name = resolved_model_id
            model_identifier = resolved_model_id  # Update for logging
        else:
            # Not in registry - parse the runtime model to get provider/model
            parsed_provider, model_name = _split_provider_from_model(model_identifier)
            provider = parsed_provider or _infer_provider_from_model(model_identifier)
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
        # xAI uses OpenAI-compatible API, so we need to:
        # 1. Override provider to "openai" for LangChain routing
        # 2. Set base_url to xAI's endpoint
        init_kwargs["model_provider"] = "openai"
        init_kwargs["api_key"] = settings.XAI_API_KEY
        init_kwargs["base_url"] = "https://api.x.ai/v1"
    elif provider == "deepseek" and settings.DEEPSEEK_API_KEY:
        init_kwargs["api_key"] = settings.DEEPSEEK_API_KEY

    # Add model parameters (runtime config overrides settings)
    temperature = runtime_config.get("temperature") if runtime_config else None
    if temperature is None:
        temperature = settings.LLM_TEMPERATURE
    if temperature is not None:
        init_kwargs["temperature"] = temperature  # type: ignore[assignment]

    max_tokens = runtime_config.get("max_tokens") if runtime_config else None
    if max_tokens is None:
        max_tokens = settings.LLM_MAX_TOKENS
    if max_tokens is not None:
        init_kwargs["max_tokens"] = max_tokens  # type: ignore[assignment]

    timeout = runtime_config.get("timeout") if runtime_config else None
    if timeout is None:
        timeout = settings.LLM_TIMEOUT
    if timeout is not None:
        init_kwargs["timeout"] = timeout  # type: ignore[assignment]

    # Add LangChain's built-in retry configuration
    max_retries = runtime_config.get("max_retries") if runtime_config else None
    if max_retries is None:
        max_retries = settings.LLM_MAX_RETRIES
    if max_retries is not None:
        init_kwargs["max_retries"] = max_retries  # type: ignore[assignment]

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
        max_retries=max_retries,
        runtime_override=runtime_model is not None,
    )

    # Create configurable model that can be switched at invocation time
    # If no runtime model was provided, the model is still configurable via config at invoke time
    # LangChain's init_chat_model has complex overloads that mypy can't resolve
    return init_chat_model(model_identifier_to_use, **init_kwargs)  # type: ignore[call-overload,no-any-return]
