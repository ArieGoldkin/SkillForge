"""Caching services for LLM optimization.

This module provides Redis-based caching for:
- Semantic caching: LLM responses with vector similarity
- Exact caching: Deterministic operations (supervisor routing)
- Chat history: Tutor session messages with search

Usage:
    >>> from app.shared.services.cache import (
    ...     get_semantic_cache,
    ...     get_exact_cache,
    ...     get_chat_history,
    ... )
"""

from app.shared.services.cache.redis_service import (
    clear_all_caches,
    get_chat_history,
    get_exact_cache,
    get_semantic_cache,
)

__all__ = [
    "clear_all_caches",
    "get_chat_history",
    "get_exact_cache",
    "get_semantic_cache",
]
