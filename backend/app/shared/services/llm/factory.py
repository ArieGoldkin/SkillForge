"""Provider factory for LLM and embedding services.

IMPORTANT: This module delegates LLM creation to app.core.model_factory.
The unified factory (model_factory.py) is the SINGLE source of truth for all
LLM initialization, including Ollama support.

This module exists for backward compatibility and for embedding services
which are not yet unified.

Usage:
    ```python
    from app.shared.services.llm.factory import get_llm_provider, get_embedding_provider

    # Automatically uses Ollama if OLLAMA_ENABLED=true, else cloud API
    llm = get_llm_provider(task_type="reasoning")
    embedding_service = get_embedding_provider()
    ```

Issue #606: CI Cost Reduction via Local Models
Issue #602: Unified factory - delegates to model_factory.py
"""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING, Literal

import httpx

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService
    from app.shared.services.embeddings.service import EmbeddingService

logger = get_logger(__name__)

TaskType = Literal["reasoning", "coding", "general"]


def get_llm_provider(
    task_type: TaskType = "reasoning",
    model: str | None = None,  # noqa: ARG001 - kept for backward compat
) -> BaseChatModel:
    """Get the appropriate LLM provider based on settings.

    DELEGATES to app.core.model_factory.get_chat_model() which is the
    SINGLE source of truth for all LLM initialization.

    When OLLAMA_ENABLED=true, returns a local Ollama model.
    Otherwise, returns the cloud-based ChatModel.

    Args:
        task_type: Type of task - affects model selection
            - "reasoning": DeepSeek R1 70B (local) or Gemini 3 Flash (cloud)
            - "coding": Qwen 2.5 Coder 32B (local) or Claude Sonnet (cloud)
            - "general": Default reasoning model
        model: Override model identifier (currently unused - for future use)

    Returns:
        LLM provider instance (ChatOllama or ChatModel)

    Example:
        >>> llm = get_llm_provider(task_type="coding")
        >>> response = await llm.ainvoke("Analyze this code")

        Issue #602: Now delegates to model_factory.py for unified LLM handling.

    """
    # Delegate to the unified factory
    from app.core.model_factory import get_chat_model

    logger.debug(
        "llm_provider_delegating_to_model_factory",
        task_type=task_type,
        ollama_enabled=settings.OLLAMA_ENABLED,
    )

    return get_chat_model(task_type=task_type)


def get_embedding_provider() -> EmbeddingService | OllamaEmbeddingService:
    """Get the appropriate embedding service based on settings.

    When OLLAMA_ENABLED=true, returns OllamaEmbeddingService for local inference.
    Otherwise, returns the cloud-based EmbeddingService (OpenAI).

    Returns:
        Embedding service instance

    Example:
        >>> embedder = get_embedding_provider()
        >>> embedding = await embedder.generate_embedding("Hello world")

    """
    if settings.OLLAMA_ENABLED:
        from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

        service = OllamaEmbeddingService()
        logger.info(
            "embedding_provider_selected",
            provider="ollama",
            model=service.model,
            dimensions=service.expected_dimensions,
        )
        return service

    # Cloud provider (existing OpenAI-based service)
    from app.shared.services.embeddings.service import EmbeddingService

    service = EmbeddingService()
    logger.info(
        "embedding_provider_selected",
        provider="openai",
        model=service.model,
        dimensions=service.expected_dimensions,
    )
    return service


def is_ollama_available() -> bool:
    """Check if Ollama server is running and accessible.

    Returns:
        True if Ollama is enabled and server is responding

    """
    if not settings.OLLAMA_ENABLED:
        return False

    try:
        response = httpx.get(
            f"{settings.OLLAMA_HOST}/api/tags",
            timeout=5.0,
        )
        return response.status_code == HTTPStatus.OK
    except httpx.HTTPError:
        return False


def get_available_ollama_models() -> list[str]:
    """Get list of models available on the Ollama server.

    Returns:
        List of model names, or empty list if Ollama unavailable

    """
    if not settings.OLLAMA_ENABLED:
        return []

    try:
        response = httpx.get(
            f"{settings.OLLAMA_HOST}/api/tags",
            timeout=5.0,
        )
        if response.status_code != HTTPStatus.OK:
            return []
        data = response.json()
        return [m.get("name", "") for m in data.get("models", [])]
    except httpx.HTTPError:
        return []
