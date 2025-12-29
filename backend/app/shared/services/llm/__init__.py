"""LLM service providers for SkillForge.

This module provides LLM provider abstractions for both cloud and local inference.

Providers:
    - OllamaProvider: Local LLM inference via Ollama (Issue #606)

Factory:
    - get_llm_provider: Auto-selects cloud/local based on OLLAMA_ENABLED
    - get_embedding_provider: Auto-selects embedding service

Usage:
    ```python
    from app.shared.services.llm import get_llm_provider, get_embedding_provider

    # Automatically uses Ollama if OLLAMA_ENABLED=true
    llm = get_llm_provider(task_type="reasoning")
    embedder = get_embedding_provider()
    ```
"""

from app.shared.services.llm.factory import (
    get_available_ollama_models,
    get_embedding_provider,
    get_llm_provider,
    is_ollama_available,
)
from app.shared.services.llm.ollama_provider import OllamaProvider, get_ollama_llm

__all__ = [
    "OllamaProvider",
    "get_available_ollama_models",
    "get_embedding_provider",
    "get_llm_provider",
    "get_ollama_llm",
    "is_ollama_available",
]
