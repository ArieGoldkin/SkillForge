"""Utilities for initializing chat models with multi-provider support.

This is the SINGLE source of truth for LLM model initialization in SkillForge.
Supports cloud providers (OpenAI, Anthropic, Google, etc.) and local Ollama.

Architecture (Issue #637 - Provider Configuration Registry):
- Init-time params: Handled here (api_key, temperature, max_tokens, etc.)
- Call-time params: Handled in provider_config.py (stream_options, strict mode)

The separation ensures parameters are applied at the correct lifecycle stage.
stream_options is only valid for OpenAI streaming calls, not ainvoke().

When OLLAMA_ENABLED=true, all LLM calls use local models:
- reasoning/g_eval → deepseek-r1:70b
- coding/supervisor → qwen2.5-coder:32b

Issue #606: Unified factory with Ollama support for 93% CI cost reduction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict, cast

from langchain.chat_models import init_chat_model
from langchain_anthropic import ChatAnthropic

from app.core.config import _infer_provider_from_model, _split_provider_from_model, settings
from app.core.logging import get_logger
from app.core.model_registry import MODEL_REGISTRY

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


# =============================================================================
# TypedDict Definitions for Type-Safe Model Initialization (Issue #602)
# =============================================================================


class StreamOptions(TypedDict):
    """Stream options for usage metadata extraction.

    NOTE: This TypedDict is kept for type checking but stream_options
    should NOT be passed at model init time. Use provider_config.py's
    get_streaming_kwargs() at astream() call time instead.

    See Issue #637 for architecture details.
    """

    include_usage: bool


class ModelInitKwargs(TypedDict, total=False):
    """Typed kwargs for init_chat_model - all fields optional.

    This provides type safety for the kwargs passed to LangChain's init_chat_model().
    Using TypedDict instead of dict[str, Any] allows mypy to verify field types.
    """

    model_provider: str
    api_key: str
    temperature: float
    max_tokens: int
    timeout: float
    max_retries: int
    base_url: str
    cache: Any  # Redis semantic cache - type varies


# Lazy import to avoid circular import at module load time
# CachedChatModel is only used when L1 caching is enabled
_CachedChatModel = None


def _get_cached_chat_model_class():
    """Lazily import CachedChatModel class.

    Returns:
        CachedChatModel class or None if import fails.

    """
    global _CachedChatModel  # noqa: PLW0603
    if _CachedChatModel is None:
        try:
            from app.core.cached_chat_model import CachedChatModel

            _CachedChatModel = CachedChatModel
            logger.debug("cached_chat_model_class_loaded")
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "cached_chat_model_import_failed",
                error=str(e),
                fallback="unwrapped_model",
            )
            return None
    return _CachedChatModel


logger = get_logger(__name__)

# Task-based model routing for cost optimization
# Maps specific task types to optimized models (cheaper/faster)
TASK_MODEL_MAP: dict[str, str] = {
    "supervisor": "claude-haiku-3-5-20241022",  # Fast classification
    # Dec 2025: Gemini 3 Flash (released Dec 17, 2025) - frontier quality
    "g_eval": "gemini-3-flash-preview",
    # "agent" and "synthesis" use the default model from settings
}

# Ollama task-to-model mapping for local inference (Issue #606)
# When OLLAMA_ENABLED=true, these models are used instead of cloud APIs
OLLAMA_TASK_MODEL_MAP: dict[str, str] = {
    "reasoning": "deepseek-r1:70b",  # Complex reasoning, synthesis, G-Eval
    "g_eval": "deepseek-r1:70b",  # Quality evaluation needs reasoning
    "coding": "qwen2.5-coder:32b",  # Code analysis, generation
    "supervisor": "qwen2.5-coder:32b",  # Fast classification
    "agent": "qwen2.5-coder:32b",  # Agent execution
    "synthesis": "deepseek-r1:70b",  # Document synthesis
    "default": "qwen2.5-coder:32b",  # General purpose
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


def _get_ollama_chat_model(task_type: str | None = None) -> BaseChatModel:
    """Get an Ollama ChatModel for local inference.

    This function returns a LangChain-compatible ChatOllama instance
    configured for the specified task type. Used when OLLAMA_ENABLED=true.

    Args:
        task_type: Task type for model selection (reasoning, coding, g_eval, etc.)

    Returns:
        ChatOllama instance configured for the task

    Issue #606: Unified Ollama support in model_factory for 93% CI cost reduction.

    """
    from langchain_ollama import ChatOllama

    # Select model based on task type
    model = OLLAMA_TASK_MODEL_MAP.get(
        task_type or "default",
        OLLAMA_TASK_MODEL_MAP["default"],
    )

    # Override with settings if available (for explicit model specification)
    if task_type in {"reasoning", "g_eval", "synthesis"}:
        model = settings.OLLAMA_MODEL_REASONING
    elif task_type in {"coding", "supervisor", "agent"}:
        model = settings.OLLAMA_MODEL_CODING

    llm = ChatOllama(
        model=model,
        base_url=settings.OLLAMA_HOST,
        temperature=0.0,
        num_ctx=settings.OLLAMA_NUM_CTX,
        keep_alive="5m",  # Keep model loaded for faster subsequent calls
        client_kwargs={"timeout": settings.OLLAMA_TIMEOUT},
    )

    logger.info(
        "ollama_chat_model_initialized",
        model=model,
        task_type=task_type,
        host=settings.OLLAMA_HOST,
        num_ctx=settings.OLLAMA_NUM_CTX,
    )

    return llm


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


# =============================================================================
# Helper Functions for get_chat_model (Issue #602 - God Function Refactor)
# =============================================================================


def _resolve_model_and_provider(
    config: dict[str, dict[str, object]] | None,
    task_type: str | None,
) -> tuple[str, str | None, str, dict[str, object]]:
    """Resolve model identifier, provider, and model name from config and task type.

    Handles task-based routing, registry lookup, and provider detection.

    Args:
        config: Optional runtime config dict with configurable.model override
        task_type: Optional task type for model routing

    Returns:
        Tuple of (model_identifier, provider, model_name, runtime_config)

    """
    runtime_config: dict[str, object] = config.get("configurable", {}) if config else {}
    runtime_model = runtime_config.get("model")

    # Task-based routing takes precedence
    routed_model: str | None = None
    if task_type and task_type in TASK_MODEL_MAP:
        routed_model = TASK_MODEL_MAP[task_type]
        logger.info(
            "model_routing_applied",
            task_type=task_type,
            routed_model=routed_model,
            default_model=settings.LLM_MODEL,
        )

    # Priority: task routing > runtime model > settings
    model_identifier_raw = routed_model or runtime_model or settings.LLM_MODEL
    model_identifier = str(model_identifier_raw).strip()

    # Resolve provider and model name
    provider: str | None = None
    model_name: str = ""

    if routed_model or runtime_model:
        # Check registry first, then parse
        resolved_model_id, registry_provider = _resolve_model_from_registry(model_identifier)

        if registry_provider:
            provider = registry_provider
            model_name = resolved_model_id
            model_identifier = resolved_model_id
        else:
            parsed_provider, model_name = _split_provider_from_model(model_identifier)
            provider = parsed_provider or _infer_provider_from_model(model_identifier)
    else:
        provider = settings.resolved_llm_provider()
        model_name = settings.resolved_llm_model_name()

    return model_identifier, provider, model_name, runtime_config


def _build_init_kwargs(
    provider: str | None,
    runtime_config: dict[str, object],
) -> tuple[ModelInitKwargs, dict[str, StreamOptions]]:
    """Build initialization kwargs for the chat model.

    Handles API key injection, model parameters, and provider-specific config.

    Args:
        provider: Provider name (openai, anthropic, google_genai, etc.)
        runtime_config: Runtime configuration overrides

    Returns:
        Tuple of (init_kwargs, model_kwargs)

    """
    init_kwargs: ModelInitKwargs = {}

    # Set provider
    if provider:
        init_kwargs["model_provider"] = provider

    # Inject API keys based on provider
    if provider == "openai" and settings.OPENAI_API_KEY:
        init_kwargs["api_key"] = settings.OPENAI_API_KEY
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        init_kwargs["api_key"] = settings.ANTHROPIC_API_KEY
    elif provider == "google_genai" and settings.GOOGLE_API_KEY:
        init_kwargs["api_key"] = settings.GOOGLE_API_KEY
    elif provider == "xai" and settings.XAI_API_KEY:
        init_kwargs["model_provider"] = "openai"  # xAI uses OpenAI-compatible API
        init_kwargs["api_key"] = settings.XAI_API_KEY
        init_kwargs["base_url"] = "https://api.x.ai/v1"
    elif provider == "deepseek" and settings.DEEPSEEK_API_KEY:
        init_kwargs["api_key"] = settings.DEEPSEEK_API_KEY

    # Extract model parameters (runtime overrides settings)
    temp_value = runtime_config.get("temperature") if runtime_config else None
    temperature: float | None = (
        cast("float", temp_value) if temp_value is not None else settings.LLM_TEMPERATURE
    )
    if temperature is not None:
        init_kwargs["temperature"] = temperature

    tokens_value = runtime_config.get("max_tokens") if runtime_config else None
    max_tokens: int | None = (
        cast("int", tokens_value) if tokens_value is not None else settings.LLM_MAX_TOKENS
    )
    if max_tokens is not None:
        init_kwargs["max_tokens"] = max_tokens

    timeout_value = runtime_config.get("timeout") if runtime_config else None
    timeout: float | None = (
        cast("float", timeout_value) if timeout_value is not None else settings.LLM_TIMEOUT
    )
    if timeout is not None:
        init_kwargs["timeout"] = timeout

    retries_value = runtime_config.get("max_retries") if runtime_config else None
    max_retries: int | None = (
        cast("int", retries_value) if retries_value is not None else settings.LLM_MAX_RETRIES
    )
    if max_retries is not None:
        init_kwargs["max_retries"] = max_retries

    # Issue #637: stream_options moved to provider_config.py for call-time injection.
    # stream_options is only valid for OpenAI streaming calls (astream), not ainvoke().
    # Use get_streaming_kwargs(provider) from provider_config.py at call sites.
    model_kwargs: dict[str, Any] = {}

    return init_kwargs, model_kwargs


def _create_anthropic_model(
    model_name: str,
    init_kwargs: ModelInitKwargs,
    task_type: str | None,
    redis_cache: Any | None,
) -> BaseChatModel:
    """Create a ChatAnthropic model with prompt caching support.

    Args:
        model_name: The Anthropic model identifier
        init_kwargs: Initialization kwargs (api_key, temperature, etc.)
        task_type: Task type for L1 cache keying
        redis_cache: Optional Redis semantic cache

    Returns:
        ChatAnthropic model, optionally wrapped with L1 cache

    """
    # Configure prompt cache TTL
    cache_enabled = False
    betas_list: list[str] | None = None
    if settings.ANTHROPIC_PROMPT_CACHE_TTL == "1h":
        betas_list = ["extended-cache-ttl-2025-04-11"]
        cache_enabled = True
        cache_ttl = "1h"
    else:
        cache_enabled = True
        cache_ttl = "5m"

    logger.info(
        "chat_model_initializing",
        configured_model=model_name,
        resolved_model=model_name,
        provider="anthropic",
        temperature=init_kwargs.get("temperature"),
        max_tokens=init_kwargs.get("max_tokens"),
        timeout=init_kwargs.get("timeout"),
        max_retries=init_kwargs.get("max_retries"),
        runtime_override=False,
        task_type=task_type,
        routed_model=None,
        prompt_cache_enabled=cache_enabled,
        prompt_cache_ttl=cache_ttl,
        redis_cache_enabled=redis_cache is not None,
    )

    # Build ChatAnthropic kwargs
    anthropic_kwargs: dict[str, Any] = {"model": model_name}
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
    if redis_cache is not None:
        anthropic_kwargs["cache"] = redis_cache

    base_model = ChatAnthropic(**anthropic_kwargs)
    return _wrap_with_l1_cache(base_model, task_type)


def _create_generic_model(  # noqa: PLR0913
    model_identifier: str,
    model_name: str,
    provider: str | None,
    init_kwargs: ModelInitKwargs,
    model_kwargs: dict[str, StreamOptions],
    task_type: str | None,
    redis_cache: Any | None,
    runtime_model_provided: bool,
    routed_model: str | None,
) -> BaseChatModel:
    """Create a generic chat model using init_chat_model.

    Args:
        model_identifier: Raw model identifier
        model_name: Provider-stripped model name
        provider: Provider name
        init_kwargs: Initialization kwargs
        model_kwargs: Model-specific kwargs (stream_options)
        task_type: Task type for L1 cache keying
        redis_cache: Optional Redis semantic cache
        runtime_model_provided: Whether runtime model override was provided
        routed_model: Routed model if task routing applied

    Returns:
        Chat model, optionally wrapped with L1 cache

    """
    # Strip provider prefix when needed
    if _should_strip_provider_prefix(provider):
        model_identifier_to_use = model_name
    else:
        model_identifier_to_use = model_identifier

    logger.info(
        "chat_model_initializing",
        configured_model=model_identifier,
        resolved_model=model_identifier_to_use,
        provider=provider or "auto",
        temperature=init_kwargs.get("temperature"),
        max_tokens=init_kwargs.get("max_tokens"),
        timeout=init_kwargs.get("timeout"),
        max_retries=init_kwargs.get("max_retries"),
        runtime_override=runtime_model_provided,
        task_type=task_type,
        routed_model=routed_model,
        redis_cache_enabled=redis_cache is not None,
    )

    # Add Redis cache if available
    if redis_cache is not None:
        init_kwargs["cache"] = redis_cache

    base_model = init_chat_model(
        model_identifier_to_use,
        model_kwargs=model_kwargs,
        **init_kwargs,
    )

    return _wrap_with_l1_cache(base_model, task_type)


def _wrap_with_l1_cache(base_model: BaseChatModel, task_type: str | None) -> BaseChatModel:
    """Wrap a chat model with L1 cache if enabled.

    Args:
        base_model: The base chat model to wrap
        task_type: Task type for cache keying

    Returns:
        Wrapped model if L1 cache enabled, otherwise base_model unchanged

    """
    if not settings.LLM_CACHE_ENABLED:
        return base_model

    cached_chat_model_class = _get_cached_chat_model_class()
    if cached_chat_model_class is None:
        return base_model

    agent_type = task_type or "default"
    logger.info(
        "llm_cache_wrapper_enabled",
        agent_type=agent_type,
        l1_cache_size=settings.LLM_CACHE_L1_SIZE,
    )
    return cached_chat_model_class(
        model=base_model,
        agent_type=agent_type,
        cache_enabled=True,
    )


# =============================================================================
# Main Entry Point
# =============================================================================


def get_chat_model(
    config: dict[str, dict[str, object]] | None = None,
    task_type: str | None = None,
) -> BaseChatModel:
    """Create a chat model instance using the configured provider/model.

    This is the SINGLE unified LLM factory for SkillForge.

    When OLLAMA_ENABLED=true, returns a local Ollama model for zero-cost inference.
    Otherwise, returns a cloud provider model (OpenAI, Anthropic, Google, etc.).

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

        Issue #606: When OLLAMA_ENABLED=true, uses local models for 93% CI cost reduction.

    """
    # OLLAMA PATH: Use local models when OLLAMA_ENABLED=true (Issue #606)
    if settings.OLLAMA_ENABLED:
        logger.info(
            "ollama_mode_active",
            task_type=task_type,
            ollama_host=settings.OLLAMA_HOST,
        )
        return _get_ollama_chat_model(task_type)

    # CLOUD PATH: Use cloud providers (OpenAI, Anthropic, Google, etc.)
    # Step 1: Resolve model and provider from config/task_type
    model_identifier, provider, model_name, runtime_config = _resolve_model_and_provider(
        config, task_type
    )

    # Step 2: Build initialization kwargs (API keys, params)
    init_kwargs, model_kwargs = _build_init_kwargs(provider, runtime_config)

    # Step 3: Get Redis semantic cache
    redis_cache = _get_redis_cache_for_model()

    # Determine routing info for logging
    runtime_model = runtime_config.get("model")
    routed_model = TASK_MODEL_MAP.get(task_type) if task_type else None

    # Step 4: Create model (Anthropic special-case or generic)
    if provider == "anthropic":
        return _create_anthropic_model(model_name, init_kwargs, task_type, redis_cache)

    return _create_generic_model(
        model_identifier,
        model_name,
        provider,
        init_kwargs,
        model_kwargs,
        task_type,
        redis_cache,
        runtime_model_provided=runtime_model is not None,
        routed_model=routed_model,
    )


# =============================================================================
# Re-exports from provider_config for convenience (Issue #637)
# =============================================================================

from app.core.provider_config import (  # noqa: E402
    get_provider_for_model,
    get_streaming_kwargs,
    get_structured_output_kwargs,
)

__all__ = [
    "OLLAMA_TASK_MODEL_MAP",
    "TASK_MODEL_MAP",
    "get_chat_model",
    "get_provider_for_model",
    "get_streaming_kwargs",
    "get_structured_output_kwargs",
]
