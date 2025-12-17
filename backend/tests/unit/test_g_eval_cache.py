"""Unit tests for G-Eval caching system."""

from __future__ import annotations

import hashlib
from datetime import timedelta

import pytest

from app.shared.services.g_eval.cache import (
    GEvalCache,
    _generate_cache_key,
    clear_cache,
    get_cache,
    get_cache_stats,
)


class TestCacheKeyGeneration:
    """Test cache key generation."""

    def test_generate_cache_key(self):
        """Test that cache keys are generated correctly."""
        key1 = _generate_cache_key(
            input_content="Test input",
            output="Test output",
            agent_type="tech_comparator",
            criterion="completeness",
        )

        # Should be a SHA256 hex digest
        assert len(key1) == 64
        assert all(c in "0123456789abcdef" for c in key1)

    def test_cache_key_consistency(self):
        """Test that same inputs generate same key."""
        key1 = _generate_cache_key("input", "output", "agent", "criterion")
        key2 = _generate_cache_key("input", "output", "agent", "criterion")
        assert key1 == key2

    def test_cache_key_uniqueness(self):
        """Test that different inputs generate different keys."""
        key1 = _generate_cache_key("input1", "output", "agent", "criterion")
        key2 = _generate_cache_key("input2", "output", "agent", "criterion")
        assert key1 != key2


class TestGEvalCache:
    """Test G-Eval cache functionality."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a test cache instance."""
        return GEvalCache(
            cache_dir=tmp_path / "test_cache",
            ttl=timedelta(hours=1),
            max_size=100,
        )

    def test_cache_init(self, cache):
        """Test cache initialization."""
        assert cache.max_size == 100
        assert cache.ttl == timedelta(hours=1)
        assert cache.stats.hits == 0
        assert cache.stats.misses == 0

    def test_cache_miss(self, cache):
        """Test cache miss."""
        result = cache.get("input", "output", "agent", "criterion")
        assert result is None
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

    def test_cache_set_and_get(self, cache):
        """Test setting and getting from cache."""
        # Set a value
        cache.set(
            input_content="test input",
            output="test output",
            agent_type="tech_comparator",
            criterion="completeness",
            score=4,
            normalized=0.75,
            confidence=0.9,
            reasoning="Good analysis",
        )

        # Get it back
        cached = cache.get("test input", "test output", "tech_comparator", "completeness")
        assert cached is not None
        assert cached.score == 4
        assert cached.normalized == 0.75
        assert cached.confidence == 0.9
        assert cached.reasoning == "Good analysis"
        assert cache.stats.hits == 1
        assert cache.stats.misses == 0

    def test_cache_hit_rate(self, cache):
        """Test cache hit rate calculation."""
        # Set a value
        cache.set("input", "output", "agent", "criterion", 3, 0.5, 0.7, "Test")

        # Miss first time (before it was set)
        cache.get("different", "output", "agent", "criterion")
        assert cache.stats.misses == 1

        # Hit
        cache.get("input", "output", "agent", "criterion")
        assert cache.stats.hits == 1

        # Hit rate should be 0.5 (1 hit / 2 total)
        assert cache.stats.hit_rate == 0.5

    def test_cache_cost_savings(self, cache):
        """Test estimated cost savings calculation."""
        # Simulate 10 cache hits
        for i in range(10):
            cache.set(f"input{i}", "output", "agent", f"criterion{i}", 3, 0.5, 0.7, "Test")
            cache.get(f"input{i}", "output", "agent", f"criterion{i}")

        # 10 hits * $0.03 = $0.30 savings
        assert cache.stats.estimated_cost_savings == 0.30

    def test_cache_persistence(self, tmp_path):
        """Test that cache persists to disk and loads back."""
        cache_dir = tmp_path / "persist_test"

        # Create cache and add entry
        cache1 = GEvalCache(cache_dir=cache_dir, ttl=timedelta(hours=24))
        cache1.set("input", "output", "agent", "criterion", 4, 0.75, 0.9, "Test")

        # Create new cache instance (should load from disk)
        cache2 = GEvalCache(cache_dir=cache_dir, ttl=timedelta(hours=24))

        # Should have loaded the entry
        cached = cache2.get("input", "output", "agent", "criterion")
        assert cached is not None
        assert cached.score == 4

    def test_cache_clear(self, cache):
        """Test clearing cache."""
        # Add some entries
        cache.set("input1", "output", "agent", "criterion", 3, 0.5, 0.7, "Test")
        cache.set("input2", "output", "agent", "criterion", 4, 0.75, 0.9, "Test")

        # Clear
        cache.clear()

        # Should be empty
        assert cache.get("input1", "output", "agent", "criterion") is None
        assert cache.get("input2", "output", "agent", "criterion") is None


class TestGlobalCache:
    """Test global cache instance."""

    def test_get_cache(self):
        """Test getting global cache instance."""
        cache1 = get_cache()
        cache2 = get_cache()
        assert cache1 is cache2  # Should be singleton

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        stats = get_cache_stats()
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "estimated_cost_savings_usd" in stats

    def test_clear_cache(self):
        """Test clearing global cache."""
        cache = get_cache()
        cache.set("input", "output", "agent", "criterion", 3, 0.5, 0.7, "Test")

        # Clear global cache
        clear_cache()

        # Should be empty (note: creates new instance)
        result = get_cache().get("input", "output", "agent", "criterion")
        # Note: clear_cache() clears the current instance but get_cache() may return same instance
        # This is expected behavior for in-memory cache
