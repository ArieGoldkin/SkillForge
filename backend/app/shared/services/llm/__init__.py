"""LLM service providers for SkillForge.

This module provides LLM provider abstractions for both cloud and local inference.

Providers:
    - OllamaProvider: Local LLM inference via Ollama (Issue #606)

Factory:
    - get_llm_provider: Auto-selects cloud/local based on OLLAMA_ENABLED
    - get_embedding_provider: Auto-selects embedding service

Utilities:
    - TokenCounter: Count tokens and estimate API costs
    - MessageUtils: Extract text, reasoning, and metadata from messages

Usage:
    ```python
    from app.shared.services.llm import get_llm_provider, get_embedding_provider

    # Automatically uses Ollama if OLLAMA_ENABLED=true
    llm = get_llm_provider(task_type="reasoning")
    embedder = get_embedding_provider()

    # Token counting and cost estimation
    from app.shared.services.llm import TokenCounter

    count = TokenCounter.count_messages(messages, model="gpt-4o")
    cost = TokenCounter.estimate_cost(1000, 500, "claude-3-5-sonnet")

    # Message content extraction
    from app.shared.services.llm import MessageUtils

    text = MessageUtils.extract_text(ai_message)
    reasoning = MessageUtils.extract_reasoning(ai_message)
    ```
"""

from app.shared.services.llm.factory import (
    get_available_ollama_models,
    get_embedding_provider,
    get_llm_provider,
    is_ollama_available,
)
from app.shared.services.llm.message_utils import MessageUtils
from app.shared.services.llm.ollama_provider import OllamaProvider, get_ollama_llm
from app.shared.services.llm.token_counter import TokenCounter

__all__ = [
    "MessageUtils",
    "OllamaProvider",
    "TokenCounter",
    "get_available_ollama_models",
    "get_embedding_provider",
    "get_llm_provider",
    "get_ollama_llm",
    "is_ollama_available",
]
