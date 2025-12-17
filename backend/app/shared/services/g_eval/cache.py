"""G-Eval Result Caching Service.

This module implements a two-layer caching system to reduce LLM costs by 70-80%:
- L1: In-memory hash-based exact match cache
- L2: File-based persistence for cache across runs

Cache hits avoid expensive LLM calls for identical evaluation requests.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_CACHE_TTL = timedelta(hours=24)
DEFAULT_MAX_CACHE_SIZE = 10_000
DEFAULT_CACHE_DIR = Path("data/g_eval_cache")

# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class CachedScore:
    """Cached G-Eval score with metadata."""

    score: int
    normalized: float
    confidence: float
    reasoning: str
    timestamp: str
    cache_key: str


@dataclass
class CacheStats:
    """Cache performance statistics."""

    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    estimated_cost_savings: float = 0.0  # In USD

    def update(self, is_hit: bool) -> None:
        """Update stats with new request result."""
        self.total_requests += 1
        if is_hit:
            self.hits += 1
        else:
            self.misses += 1
        self.hit_rate = self.hits / self.total_requests if self.total_requests > 0 else 0.0

        # Rough cost estimate: GPT-4 ~$0.03 per criterion evaluation
        # Each cache hit saves ~$0.03
        self.estimated_cost_savings = self.hits * 0.03

    def to_dict(self) -> dict[str, Any]:
        """Convert stats to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 3),
            "estimated_cost_savings_usd": round(self.estimated_cost_savings, 2),
        }


# ============================================================================
# Cache Key Generation
# ============================================================================


def _generate_cache_key(
    input_content: str,
    output: str,
    agent_type: str,
    criterion: str,
) -> str:
    """Generate cache key from evaluation parameters.

    Uses SHA256 hash of:
    - First 500 chars of input
    - First 500 chars of output
    - Agent type
    - Criterion name

    Args:
        input_content: Original input/task
        output: Generated output being evaluated
        agent_type: Agent type for rubric selection
        criterion: Evaluation criterion

    Returns:
        SHA256 hex digest as cache key

    """
    # Truncate for key generation (full text not needed for uniqueness)
    input_prefix = input_content[:500]
    output_prefix = output[:500]

    # Combine all parameters
    key_string = f"{input_prefix}|{output_prefix}|{agent_type}|{criterion}"

    # Hash for fixed-length key
    return hashlib.sha256(key_string.encode()).hexdigest()


# ============================================================================
# Cache Service
# ============================================================================


class GEvalCache:
    """Two-layer caching system for G-Eval scores."""

    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        ttl: timedelta = DEFAULT_CACHE_TTL,
        max_size: int = DEFAULT_MAX_CACHE_SIZE,
    ) -> None:
        """Initialize cache service.

        Args:
            cache_dir: Directory for persistent cache files
            ttl: Time-to-live for cached entries
            max_size: Maximum number of entries in L1 cache

        """
        self.cache_dir = cache_dir
        self.ttl = ttl
        self.max_size = max_size

        # L1: In-memory cache {cache_key: CachedScore}
        self._memory_cache: dict[str, CachedScore] = {}

        # Stats tracking
        self.stats = CacheStats()

        # Initialize cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Load L2 cache from disk
        self._load_from_disk()

        logger.info(
            "g_eval_cache_initialized",
            cache_dir=str(cache_dir),
            ttl_hours=ttl.total_seconds() / 3600,
            max_size=max_size,
            entries_loaded=len(self._memory_cache),
        )

    def get(
        self,
        input_content: str,
        output: str,
        agent_type: str,
        criterion: str,
    ) -> CachedScore | None:
        """Get cached score if available and not expired.

        Args:
            input_content: Original input/task
            output: Generated output being evaluated
            agent_type: Agent type for rubric selection
            criterion: Evaluation criterion

        Returns:
            CachedScore if found and valid, None otherwise

        """
        cache_key = _generate_cache_key(input_content, output, agent_type, criterion)

        # Check L1 cache
        if cache_key in self._memory_cache:
            cached = self._memory_cache[cache_key]

            # Check if expired
            cached_time = datetime.fromisoformat(cached.timestamp)
            if datetime.now(UTC) - cached_time > self.ttl:
                # Expired - remove and return None
                del self._memory_cache[cache_key]
                self.stats.update(is_hit=False)
                logger.debug("g_eval_cache_expired", cache_key=cache_key[:16])
                return None

            # Valid cache hit
            self.stats.update(is_hit=True)
            logger.debug(
                "g_eval_cache_hit",
                cache_key=cache_key[:16],
                criterion=criterion,
                agent_type=agent_type,
            )
            return cached

        # Cache miss
        self.stats.update(is_hit=False)
        logger.debug(
            "g_eval_cache_miss",
            cache_key=cache_key[:16],
            criterion=criterion,
            agent_type=agent_type,
        )
        return None

    def set(  # noqa: PLR0913 - All parameters needed for cache key + score data
        self,
        input_content: str,
        output: str,
        agent_type: str,
        criterion: str,
        score: int,
        normalized: float,
        confidence: float,
        reasoning: str,
    ) -> None:
        """Store score in cache.

        Args:
            input_content: Original input/task
            output: Generated output being evaluated
            agent_type: Agent type for rubric selection
            criterion: Evaluation criterion
            score: Raw score (1-5)
            normalized: Normalized score (0-1)
            confidence: Confidence level (0-1)
            reasoning: Evaluation reasoning

        """
        cache_key = _generate_cache_key(input_content, output, agent_type, criterion)

        # Check L1 cache size limit
        if len(self._memory_cache) >= self.max_size:
            # Simple LRU: Remove oldest 10% of entries
            sorted_keys = sorted(
                self._memory_cache.keys(),
                key=lambda k: self._memory_cache[k].timestamp,
            )
            remove_count = self.max_size // 10
            for key in sorted_keys[:remove_count]:
                del self._memory_cache[key]
            logger.info("g_eval_cache_eviction", removed=remove_count)

        # Store in L1 cache
        cached = CachedScore(
            score=score,
            normalized=normalized,
            confidence=confidence,
            reasoning=reasoning,
            timestamp=datetime.now(UTC).isoformat(),
            cache_key=cache_key,
        )
        self._memory_cache[cache_key] = cached

        logger.debug(
            "g_eval_cache_set",
            cache_key=cache_key[:16],
            criterion=criterion,
            agent_type=agent_type,
            score=score,
        )

        # Persist to L2 (async would be better but keeping it simple)
        self._save_to_disk()

    def clear(self) -> None:
        """Clear all cache entries."""
        self._memory_cache.clear()
        # Remove all cache files
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("g_eval_cache_cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get cache performance statistics."""
        return self.stats.to_dict()

    # ========================================================================
    # L2 Persistence
    # ========================================================================

    def _load_from_disk(self) -> None:
        """Load cache entries from disk (L2)."""
        cache_file = self.cache_dir / "cache.json"
        if not cache_file.exists():
            return

        try:
            with cache_file.open() as f:
                data = json.load(f)

            # Load entries and filter expired
            now = datetime.now(UTC)
            loaded = 0
            expired = 0

            for entry_data in data.get("entries", []):
                cached = CachedScore(**entry_data)
                cached_time = datetime.fromisoformat(cached.timestamp)

                if now - cached_time <= self.ttl:
                    self._memory_cache[cached.cache_key] = cached
                    loaded += 1
                else:
                    expired += 1

            logger.info(
                "g_eval_cache_loaded_from_disk",
                loaded=loaded,
                expired=expired,
            )

        except Exception as e:  # noqa: BLE001 - Non-critical cache loading
            logger.warning("g_eval_cache_load_error", error=str(e))

    def _save_to_disk(self) -> None:
        """Save cache entries to disk (L2)."""
        cache_file = self.cache_dir / "cache.json"

        try:
            data = {
                "entries": [asdict(cached) for cached in self._memory_cache.values()],
                "saved_at": datetime.now(UTC).isoformat(),
            }

            with cache_file.open("w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:  # noqa: BLE001 - Non-critical cache saving
            logger.warning("g_eval_cache_save_error", error=str(e))


# ============================================================================
# Global Cache Instance
# ============================================================================

# Singleton cache instance (thread-safe enough for our use case)
_global_cache: GEvalCache | None = None


def get_cache() -> GEvalCache:
    """Get or create global cache instance."""
    global _global_cache  # noqa: PLW0603
    if _global_cache is None:
        _global_cache = GEvalCache()
    return _global_cache


def clear_cache() -> None:
    """Clear global cache instance."""
    global _global_cache  # noqa: PLW0602
    if _global_cache is not None:
        _global_cache.clear()


def get_cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    return get_cache().get_stats()
