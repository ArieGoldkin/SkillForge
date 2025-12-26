"""Utilities for initializing chat models with multi-provider support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic

from app.core.config import _infer_provider_from_model, _split_provider_from_model, settings
from app.core.logging import get_logger
from app.core.model_registry import MODEL_REGISTRY

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = get_logger(__name__)

# Task-based model routing for cost optimization
# Maps specific task types to optimized models (cheaper/faster)
TASK_MODEL_MAP: dict[str, str] = {
    "supervisor": "claude-haiku-3-5-20241022",  # Fast classification
    # Dec 2025: Gemini 3 Flash (released Dec 17, 2025) - frontier quality
    "g_eval": "gemini-3-flash-preview",
    # "agent" and "synthesis" use the default model from settings
}


def _get_redis_cache_for_model():
    """Get Redis semantic cache for LLM responses.

    Returns:
        RedisSemanticCache instance or None if Redis is unavailable.

    """
    try:
        from app.shared.services.cache import get_semantic_cache

        cache = get_semantic_cache()
        logger.debug("redis_cache_enabled_for_model")
        return cache
    except Exception as e:  # noqa: BLE001
        # Gracefully handle Redis connection failures
        logger.warning(
            "redis_cache_unavailable",
            error=str(e),
            fallback="no_cache",
        )
        return None


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


def get_chat_model(  # noqa: PLR0912, PLR0915
    config: dict[str, dict[str, object]] | None = None,
    task_type: str | None = None,
) -> BaseChatModel:
    """Create a chat model instance using the configured provider/model.

    Supports runtime configuration via config parameter for model switching.
    Supports task-based routing to use cheaper/faster models for specific tasks.
    Configures temperature, max_tokens, timeout, and max_retries from settings.
    Uses LangChain's built-in retry mechanism (max_retries) for automatic retry handling.

    Args:
        config: Optional runtime config dict. If provided, can override model:
            - config.get("configurable", {}).get("model") - override model at runtime
            - config.get("configurable", {}).get("temperature") - override temperature
            - config.get("configurable", {}).get("max_tokens") - override max_tokens
            - config.get("configurable", {}).get("timeout") - override timeout
            - config.get("configurable", {}).get("max_retries") - override max_retries
        task_type: Optional task type for model routing (e.g., "supervisor", "g_eval").
            If provided and in TASK_MODEL_MAP, uses the mapped model instead of default.
            Takes precedence over config["configurable"]["model"].

    Returns:
        Configured chat model instance that can be further customized via config
        at invocation time for runtime model switching.

    Note:
        LangChain's built-in retry (max_retries) handles retries automatically with
        proper async behavior. The timeout parameter applies to both streaming and
        non-streaming calls. Timeout is enforced at the model level by LangChain.

    """
    # Check for runtime model override in config
    runtime_config: dict[str, object] = config.get("configurable", {}) if config else {}
    runtime_model = runtime_config.get("model")

    # Task-based routing takes precedence over config, then runtime model, then settings
    routed_model: str | None = None
    if task_type and task_type in TASK_MODEL_MAP:
        routed_model = TASK_MODEL_MAP[task_type]
        logger.info(
            "model_routing_applied",
            task_type=task_type,
            routed_model=routed_model,
            default_model=settings.LLM_MODEL,
        )

    # Use routed model if task routing applied, otherwise runtime model, otherwise settings
    model_identifier_raw = routed_model or runtime_model or settings.LLM_MODEL
    model_identifier = str(model_identifier_raw).strip()

    # Re-resolve provider/model if routed or runtime model was provided
    provider: str | None = None
    model_name: str = ""
    if routed_model or runtime_model:
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

    # Enable streaming usage metadata (LangChain-Core 1.2.4+)
    # This allows usage_metadata extraction from streaming chunks
    # Move to model_kwargs to avoid LangChain's "not default parameter" warning
    if "model_kwargs" not in init_kwargs:
        init_kwargs["model_kwargs"] = {}  # type: ignore[assignment]
    init_kwargs["model_kwargs"]["stream_options"] = {"include_usage": True}  # type: ignore[typeddict-item]

    # Remove provider prefix when LangChain expects bare model names
    if _should_strip_provider_prefix(provider):
        model_identifier_to_use = model_name
    else:
        # For custom providers (e.g., perplexity/composer), pass the raw identifier
        model_identifier_to_use = model_identifier

    # Get Redis semantic cache for LLM response caching
    redis_cache = _get_redis_cache_for_model()

    # For Anthropic models, use ChatAnthropic directly to enable prompt caching
    if provider == "anthropic":
        # Add extended cache TTL beta header if configured for 1 hour
        cache_enabled = False
        betas_list: list[str] | None = None
        if settings.ANTHROPIC_PROMPT_CACHE_TTL == "1h":
            # Use extended cache TTL (1 hour) with beta header
            betas_list = ["extended-cache-ttl-2025-04-11"]
            cache_enabled = True
            cache_ttl = "1h"
        else:
            # Default is 5 minutes (no beta header needed)
            cache_enabled = True
            cache_ttl = "5m"

        logger.info(
            "chat_model_initializing",
            configured_model=model_identifier,
            resolved_model=model_identifier_to_use,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            runtime_override=runtime_model is not None,
            task_type=task_type,
            routed_model=routed_model,
            prompt_cache_enabled=cache_enabled,
            prompt_cache_ttl=cache_ttl,
            redis_cache_enabled=redis_cache is not None,
        )

        # Create ChatAnthropic instance directly
        # Note: We need to extract kwargs that ChatAnthropic accepts
        anthropic_kwargs = {
            "model": model_identifier_to_use,
        }
        if "api_key" in init_kwargs:
            anthropic_kwargs["api_key"] = init_kwargs["api_key"]
        if "temperature" in init_kwargs:
            anthropic_kwargs["temperature"] = init_kwargs["temperature"]
        if "max_tokens" in init_kwargs:
            anthropic_kwargs["max_tokens"] = init_kwargs["max_tokens"]
        if "timeout" in init_kwargs:
            anthropic_kwargs["timeout"] = init_kwargs["timeout"]
        if "max_retries" in init_kwargs:
            anthropic_kwargs["max_retries"] = init_kwargs["max_retries"]
        if betas_list:
            anthropic_kwargs["betas"] = betas_list
        # Add Redis semantic cache
        if redis_cache is not None:
            anthropic_kwargs["cache"] = redis_cache

        return ChatAnthropic(**anthropic_kwargs)  # type: ignore[arg-type,return-value]

    # For non-Anthropic models, use init_chat_model
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
        task_type=task_type,
        routed_model=routed_model,
        redis_cache_enabled=redis_cache is not None,
    )

    # Add Redis semantic cache if available
    if redis_cache is not None:
        init_kwargs["cache"] = redis_cache

    # Create configurable model that can be switched at invocation time
    # If no runtime model was provided, the model is still configurable via config at invoke time
    # LangChain's init_chat_model has complex overloads that mypy can't resolve
    return init_chat_model(model_identifier_to_use, **init_kwargs)  # type: ignore[call-overload,no-any-return]
