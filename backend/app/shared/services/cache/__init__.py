"""Caching services for LLM optimization.

This module provides Redis-based caching for:
- Semantic caching: LLM responses with vector similarity
- Exact caching: Deterministic operations (supervisor routing)
- Chat history: Tutor session messages with search
- Connection factory: Robust Redis clients with keepalive and retry

Usage:
    >>> from app.shared.services.cache import (
    ...     get_semantic_cache,
    ...     get_exact_cache,
    ...     get_chat_history,
    ...     create_redis_client,
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

__all__ = [
    "clear_all_caches",
    "create_redis_client",
    "get_chat_history",
    "get_exact_cache",
    "get_redis_url_for_langchain",
    "get_semantic_cache",
]
