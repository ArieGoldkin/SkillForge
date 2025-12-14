"""API key configuration validation and startup diagnostics.

This module provides functions to validate API key configuration at startup
and log which providers are configured without exposing actual key values.

Issue #295: Add API key configuration validation and E2E workflow testing options
"""

from app.core.config import LLM_PROVIDER_API_FIELDS, settings
from app.core.logging import get_logger
from app.core.model_registry import MODEL_REGISTRY, get_model_info

logger = get_logger(__name__)


def get_configured_providers() -> dict[str, bool]:
    """Get configuration status for all known providers.

    Returns:
        Dict mapping provider names to whether their API key is configured.
        Does NOT expose actual key values.

    """
    configured = {}
    for provider, api_field in LLM_PROVIDER_API_FIELDS.items():
        api_key = getattr(settings, api_field, None)
        configured[provider] = bool(api_key)
    return configured


def get_available_models_for_configured_providers() -> list[str]:
    """Get list of models that can be used with configured API keys.

    Returns:
        List of model names that have their required API keys configured.

    """
    available = []
    for model_name, model_info in MODEL_REGISTRY.items():
        api_key = getattr(settings, model_info.api_key_field, None)
        if api_key:
            available.append(model_name)
    return available


def validate_llm_model_api_key() -> tuple[bool, str | None]:
    """Validate that the configured LLM_MODEL has its required API key.

    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is None.

    """
    model_name = settings.LLM_MODEL
    model_info = get_model_info(model_name)

    if model_info is None:
        # Model not in registry - try to infer provider from model name
        try:
            provider = settings.resolved_llm_provider()
            api_field = LLM_PROVIDER_API_FIELDS.get(provider)
            if api_field:
                api_key = getattr(settings, api_field, None)
                if not api_key:
                    return False, (
                        f"LLM_MODEL '{model_name}' requires {api_field} "
                        f"(provider: {provider}) but it is not configured"
                    )
        except ValueError:
            # Could not determine provider
            return False, (
                f"LLM_MODEL '{model_name}' is not in the model registry "
                "and provider could not be inferred. Set LLM_PROVIDER explicitly."
            )
    else:
        # Model found in registry - check its API key
        api_key = getattr(settings, model_info.api_key_field, None)
        if not api_key:
            return False, (
                f"LLM_MODEL '{model_name}' requires {model_info.api_key_field} "
                f"but it is not configured"
            )

    return True, None


def log_api_key_configuration() -> None:
    """Log API key configuration status at startup.

    Logs which providers are configured (without exposing key values)
    and validates that the selected LLM_MODEL has its required key.
    """
    configured_providers = get_configured_providers()
    available_models = get_available_models_for_configured_providers()

    # Build provider status for logging
    provider_status = {
        provider: "configured" if configured else "NOT SET"
        for provider, configured in configured_providers.items()
    }

    # Count configured vs total
    configured_count = sum(1 for c in configured_providers.values() if c)
    total_count = len(configured_providers)

    # Log overall status
    logger.info(
        "api_key_configuration",
        environment=settings.ENVIRONMENT,
        llm_model=settings.LLM_MODEL,
        configured_providers=configured_count,
        total_providers=total_count,
        provider_status=provider_status,
        available_model_count=len(available_models),
    )

    # Validate LLM_MODEL has its required key
    is_valid, error_message = validate_llm_model_api_key()

    if not is_valid:
        # In dev/e2e, log as warning; in production, this would have already failed
        if settings.is_development() or settings.is_e2e():
            logger.warning(
                "llm_model_api_key_missing",
                llm_model=settings.LLM_MODEL,
                error=error_message,
                hint=(
                    "The workflow will fail when trying to use this model. "
                    "Either configure the required API key or change LLM_MODEL."
                ),
            )
        else:
            # In staging/production, this is an error
            logger.error(
                "llm_model_api_key_missing",
                llm_model=settings.LLM_MODEL,
                error=error_message,
            )
    else:
        logger.info(
            "llm_model_api_key_valid",
            llm_model=settings.LLM_MODEL,
            message="LLM model has required API key configured",
        )

    # Log JINA_API_KEY status (used for content extraction)
    jina_configured = bool(settings.JINA_API_KEY)
    if not jina_configured:
        logger.warning(
            "jina_api_key_not_configured",
            hint="JINA_API_KEY is not set. URL content extraction may have limited functionality.",
        )

    # Log embedding requirements
    # Embeddings always require OPENAI_API_KEY currently
    openai_configured = configured_providers.get("openai", False)
    if not openai_configured:
        logger.warning(
            "embedding_api_key_missing",
            required_key="OPENAI_API_KEY",
            hint=(
                "OPENAI_API_KEY is required for embedding generation. "
                "The embedding service will fail without this key."
            ),
        )
