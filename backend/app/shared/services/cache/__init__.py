"""Caching services for LLM optimization.

This module provides Redis-based caching for:
- Semantic caching: LLM responses with vector similarity
- Exact caching: Deterministic operations (supervisor routing)
- Chat history: Tutor session messages with search
- Connection factory: Robust Redis clients with keepalive and retry
- Two-tier LLM caching: L1 (in-memory) + L2 (Redis semantic) for 70-95% cost reduction

Usage:
    >>> from app.shared.services.cache import (
    ...     get_semantic_cache,
    ...     get_exact_cache,
    ...     get_chat_history,
    ...     create_redis_client,
    ...     get_llm_cache,
    ... )
"""

from app.shared.services.cache.redis_connection import (
    create_redis_client,
    get_redis_url_for_langchain,
)
from app.shared.services.cache.redis_service import (
    clear_all_caches,
    get_chat_history,
    get_exact_cache,
    get_semantic_cache,
)

# Lazy import to avoid circular dependency
# llm_cache_service imports get_semantic_cache from this module
__all__ = [
    "CacheResult",
    "clear_all_caches",
    "clear_llm_cache",
    "create_redis_client",
    "get_chat_history",
    "get_exact_cache",
    "get_llm_cache",
    "get_redis_url_for_langchain",
    "get_semantic_cache",
]


def __getattr__(name: str):
    """Lazy import for llm_cache_service to break circular dependency."""
    if name == "get_llm_cache":
        from app.shared.services.cache.llm_cache_service import get_llm_cache

        return get_llm_cache
    if name == "clear_llm_cache":
        from app.shared.services.cache.llm_cache_service import clear_llm_cache

        return clear_llm_cache
    if name == "CacheResult":
        from app.shared.services.cache.llm_cache_service import CacheResult

        return CacheResult
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
