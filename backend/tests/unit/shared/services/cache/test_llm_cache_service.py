"""Tests for LLMCacheService two-tier caching.

Tests cover:
- Initialization with default and custom parameters
- Cache key generation (deterministic, collision-free)
- L1 cache hits and misses
- L2 cache hits and misses (with mocked Redis)
- Statistics tracking (l1_hits, l1_misses, l2_hits, l2_misses)
- Singleton pattern via get_llm_cache()
- clear() and reset_stats() methods
- Error handling (cache failures never raise exceptions)
- Graceful degradation when L2 unavailable
"""

from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain_core.outputs import Generation

from app.shared.services.cache.llm_cache_service import (
    LLMCacheService,
    clear_llm_cache,
    get_llm_cache,
)


class TestLLMCacheServiceInitialization:
    """Test LLM cache service initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        cache = LLMCacheService()

        assert cache._l1_size == 1000  # Default L1 size
        assert cache._l1_ttl == 300  # Default 5 minutes
        assert cache._l2_ttl == 86400  # Default 24 hours
        assert cache._similarity_threshold == 0.92  # Default threshold
        assert cache._l2_cache is None  # L2 lazy initialization
        assert len(cache._l1_cache) == 0  # Empty cache

    def test_init_with_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        cache = LLMCacheService(
            l1_size=500,
            l1_ttl=600,
            l2_ttl=43200,
            similarity_threshold=0.95,
        )

        assert cache._l1_size == 500
        assert cache._l1_ttl == 600
        assert cache._l2_ttl == 43200
        assert cache._similarity_threshold == 0.95

    def test_init_stats_reset(self) -> None:
        """Test that statistics are initialized to zero."""
        cache = LLMCacheService()

        stats = cache.get_stats()
        assert stats["l1_hits"] == 0
        assert stats["l1_misses"] == 0
        assert stats["l2_hits"] == 0
        assert stats["l2_misses"] == 0
        assert stats["l1_size"] == 0
        assert stats["l1_max_size"] == 1000


class TestCacheKeyGeneration:
    """Test cache key generation logic."""

    def test_cache_key_deterministic(self) -> None:
        """Test that same inputs produce same cache key."""
        cache = LLMCacheService()

        agent_type = "tech_comparator"
        content = "Document content here"
        prompt = "Analysis prompt here"

        key1 = cache._generate_cache_key(agent_type, content, prompt)
        key2 = cache._generate_cache_key(agent_type, content, prompt)

        assert key1 == key2
        assert len(key1) == 64  # SHA256 hex = 64 chars

    def test_cache_key_different_agent_types(self) -> None:
        """Test that different agent types produce different keys."""
        cache = LLMCacheService()

        content = "Same content"
        prompt = "Same prompt"

        key1 = cache._generate_cache_key("tech_comparator", content, prompt)
        key2 = cache._generate_cache_key("security_auditor", content, prompt)

        assert key1 != key2

    def test_cache_key_different_content(self) -> None:
        """Test that different content produces different keys."""
        cache = LLMCacheService()

        agent_type = "tech_comparator"
        prompt = "Same prompt"

        key1 = cache._generate_cache_key(agent_type, "Content A", prompt)
        key2 = cache._generate_cache_key(agent_type, "Content B", prompt)

        assert key1 != key2

    def test_cache_key_different_prompts(self) -> None:
        """Test that different prompts produce different keys."""
        cache = LLMCacheService()

        agent_type = "tech_comparator"
        content = "Same content"

        key1 = cache._generate_cache_key(agent_type, content, "Prompt A")
        key2 = cache._generate_cache_key(agent_type, content, "Prompt B")

        assert key1 != key2

    def test_cache_key_collision_resistance(self) -> None:
        """Test that similar inputs produce different keys.

        Note: The current separator (||) doesn't prevent ALL collisions
        (e.g., agent_type="a||b" + content="c" is same as agent_type="a" + content="b||c").
        However, in practice agent_type is controlled and won't contain separators.

        This test verifies that subtle differences in inputs produce different keys.
        """
        cache = LLMCacheService()

        # Test different whitespace
        key1 = cache._generate_cache_key("agent", "content", "prompt")
        key2 = cache._generate_cache_key("agent", "content ", "prompt")  # Extra space
        assert key1 != key2

        # Test case sensitivity
        key3 = cache._generate_cache_key("Agent", "content", "prompt")
        assert key1 != key3

        # Test similar but different content
        key4 = cache._generate_cache_key("agent", "content1", "prompt")
        key5 = cache._generate_cache_key("agent", "content2", "prompt")
        assert key4 != key5


class TestL1CacheBehavior:
    """Test L1 (in-memory) cache behavior."""

    @pytest.mark.asyncio
    async def test_l1_cache_miss(self) -> None:
        """Test L1 cache miss when key not present."""
        cache = LLMCacheService()

        result = await cache.get("tech_comparator", "content", "prompt")

        assert result is None
        stats = cache.get_stats()
        assert stats["l1_misses"] == 1
        assert stats["l1_hits"] == 0

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self) -> None:
        """Test L1 cache hit after set."""
        cache = LLMCacheService()

        agent_type = "tech_comparator"
        content = "Document content"
        prompt = "Analysis prompt"
        response = "LLM response here"

        # Set cache
        await cache.set(agent_type, content, prompt, response)

        # Get from cache - should hit L1
        result = await cache.get(agent_type, content, prompt)

        assert result is not None
        assert result.response == response
        assert result.cache_level == "l1"
        assert result.similarity_score is None  # L1 is exact match

        stats = cache.get_stats()
        assert stats["l1_hits"] == 1
        assert stats["l1_misses"] == 0

    @pytest.mark.asyncio
    async def test_l1_cache_multiple_keys(self) -> None:
        """Test L1 cache with multiple different keys."""
        cache = LLMCacheService()

        # Set multiple cache entries
        await cache.set("agent1", "content1", "prompt1", "response1")
        await cache.set("agent2", "content2", "prompt2", "response2")
        await cache.set("agent3", "content3", "prompt3", "response3")

        # Verify all are cached
        result1 = await cache.get("agent1", "content1", "prompt1")
        result2 = await cache.get("agent2", "content2", "prompt2")
        result3 = await cache.get("agent3", "content3", "prompt3")

        assert result1.response == "response1"
        assert result2.response == "response2"
        assert result3.response == "response3"

        stats = cache.get_stats()
        assert stats["l1_hits"] == 3
        assert stats["l1_size"] == 3

    @pytest.mark.asyncio
    async def test_l1_cache_ttl_expiration(self) -> None:
        """Test that L1 cache respects TTL (time-to-live).

        Note: This test uses a very short TTL (1 second) for testing.
        In production, L1 TTL is 300 seconds (5 minutes).
        """
        cache = LLMCacheService(l1_ttl=1)  # 1 second TTL

        agent_type = "tech_comparator"
        content = "content"
        prompt = "prompt"

        # Set cache
        await cache.set(agent_type, content, prompt, "response")

        # Immediate get - should hit
        result = await cache.get(agent_type, content, prompt)
        assert result is not None
        assert result.cache_level == "l1"

        # Wait for TTL expiration
        import asyncio

        await asyncio.sleep(1.5)  # Wait 1.5 seconds

        # Get again - should miss (TTL expired)
        result = await cache.get(agent_type, content, prompt)
        # L1 miss, will try L2 (which will also miss in this test)
        assert result is None

        stats = cache.get_stats()
        assert stats["l1_hits"] == 1
        assert stats["l1_misses"] == 1

    @pytest.mark.asyncio
    async def test_l1_cache_lru_eviction(self) -> None:
        """Test that L1 cache evicts old entries when full."""
        # Create cache with small size for testing
        cache = LLMCacheService(l1_size=3)

        # Fill cache to capacity
        await cache.set("agent", "content1", "prompt", "response1")
        await cache.set("agent", "content2", "prompt", "response2")
        await cache.set("agent", "content3", "prompt", "response3")

        stats = cache.get_stats()
        assert stats["l1_size"] == 3

        # Add one more - should evict oldest (LRU)
        await cache.set("agent", "content4", "prompt", "response4")

        stats = cache.get_stats()
        assert stats["l1_size"] == 3  # Still at max size

        # Verify newest entry exists
        result = await cache.get("agent", "content4", "prompt")
        assert result is not None
        assert result.response == "response4"


class TestL2CacheBehavior:
    """Test L2 (Redis semantic) cache behavior with mocked Redis."""

    @pytest.mark.asyncio
    async def test_l2_cache_hit(self) -> None:
        """Test L2 cache hit when L1 misses."""
        cache = LLMCacheService()

        agent_type = "tech_comparator"
        content = "Document content"
        prompt = "Analysis prompt"
        response = "LLM response from L2"

        # Mock L2 cache
        mock_l2 = MagicMock()
        mock_generation = Mock(spec=Generation)
        mock_generation.text = response
        mock_l2.lookup.return_value = [mock_generation]

        with patch.object(cache, "_get_l2_cache", return_value=mock_l2):
            # Get from cache - L1 miss, L2 hit
            result = await cache.get(agent_type, content, prompt)

        assert result is not None
        assert result.response == response
        assert result.cache_level == "l2"
        assert result.similarity_score == 0.92  # Default threshold

        stats = cache.get_stats()
        assert stats["l1_misses"] == 1
        assert stats["l2_hits"] == 1
        assert stats["l2_misses"] == 0

        # Verify L2 lookup was called with correct prompt format
        mock_l2.lookup.assert_called_once()
        call_args = mock_l2.lookup.call_args
        assert "[CACHE_KEY:" in call_args[0][0]  # First positional arg
        assert call_args[1]["llm_string"] == agent_type  # Keyword arg

    @pytest.mark.asyncio
    async def test_l2_cache_miss(self) -> None:
        """Test L2 cache miss (both L1 and L2 miss)."""
        cache = LLMCacheService()

        # Mock L2 cache - return None (miss)
        mock_l2 = MagicMock()
        mock_l2.lookup.return_value = None

        with patch.object(cache, "_get_l2_cache", return_value=mock_l2):
            result = await cache.get("tech_comparator", "content", "prompt")

        assert result is None

        stats = cache.get_stats()
        assert stats["l1_misses"] == 1
        assert stats["l2_misses"] == 1
        assert stats["l2_hits"] == 0

    @pytest.mark.asyncio
    async def test_l2_cache_write(self) -> None:
        """Test writing to L2 cache on set()."""
        cache = LLMCacheService()

        agent_type = "tech_comparator"
        content = "content"
        prompt = "prompt"
        response = "response"

        # Mock L2 cache
        mock_l2 = MagicMock()

        with patch.object(cache, "_get_l2_cache", return_value=mock_l2):
            await cache.set(agent_type, content, prompt, response)

        # Verify L2 update was called
        mock_l2.update.assert_called_once()
        call_args = mock_l2.update.call_args
        assert "[CACHE_KEY:" in call_args[0][0]  # Cache prompt
        assert call_args[1]["llm_string"] == agent_type
        assert call_args[1]["return_val"] == [response]

    @pytest.mark.asyncio
    async def test_l2_cache_unavailable_on_get(self) -> None:
        """Test graceful degradation when L2 cache unavailable on get."""
        cache = LLMCacheService()

        # Mock _get_l2_cache to return None (unavailable)
        with patch.object(cache, "_get_l2_cache", return_value=None):
            result = await cache.get("tech_comparator", "content", "prompt")

        assert result is None

        stats = cache.get_stats()
        assert stats["l1_misses"] == 1
        assert stats["l2_misses"] == 1  # Counted as miss

    @pytest.mark.asyncio
    async def test_l2_cache_unavailable_on_set(self) -> None:
        """Test graceful degradation when L2 cache unavailable on set."""
        cache = LLMCacheService()

        # Mock _get_l2_cache to return None (unavailable)
        with patch.object(cache, "_get_l2_cache", return_value=None):
            # Should not raise exception
            await cache.set("tech_comparator", "content", "prompt", "response")

        # L1 should still be set
        result = await cache.get("tech_comparator", "content", "prompt")
        assert result is not None
        assert result.cache_level == "l1"

    @pytest.mark.asyncio
    async def test_l2_hit_populates_l1(self) -> None:
        """Test that L2 hit populates L1 cache for future requests."""
        cache = LLMCacheService()

        agent_type = "tech_comparator"
        content = "content"
        prompt = "prompt"
        response = "L2 response"

        # Mock L2 cache
        mock_l2 = MagicMock()
        mock_generation = Mock(spec=Generation)
        mock_generation.text = response
        mock_l2.lookup.return_value = [mock_generation]

        with patch.object(cache, "_get_l2_cache", return_value=mock_l2):
            # First get - L2 hit
            result1 = await cache.get(agent_type, content, prompt)
            assert result1.cache_level == "l2"

        # Second get - should hit L1 (no L2 mock needed)
        result2 = await cache.get(agent_type, content, prompt)
        assert result2 is not None
        assert result2.cache_level == "l1"
        assert result2.response == response

        stats = cache.get_stats()
        assert stats["l1_hits"] == 1  # Second call
        assert stats["l2_hits"] == 1  # First call
        assert stats["l1_misses"] == 1  # First call


class TestStatisticsTracking:
    """Test cache statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_tracking_l1_hits_misses(self) -> None:
        """Test that L1 hits and misses are tracked correctly."""
        cache = LLMCacheService()

        # Set cache
        await cache.set("agent", "content", "prompt", "response")

        # Hit
        await cache.get("agent", "content", "prompt")

        # Miss
        await cache.get("agent", "different_content", "prompt")

        stats = cache.get_stats()
        assert stats["l1_hits"] == 1
        assert stats["l1_misses"] == 1

    @pytest.mark.asyncio
    async def test_stats_tracking_l2_hits_misses(self) -> None:
        """Test that L2 hits and misses are tracked correctly."""
        cache = LLMCacheService()

        # Mock L2 cache - first lookup hits, second misses
        mock_l2 = MagicMock()
        mock_generation = Mock(spec=Generation)
        mock_generation.text = "response"
        mock_l2.lookup.side_effect = [[mock_generation], None]  # Hit, then miss

        with patch.object(cache, "_get_l2_cache", return_value=mock_l2):
            # L2 hit
            result1 = await cache.get("agent", "content1", "prompt")
            assert result1 is not None

            # L2 miss
            result2 = await cache.get("agent", "content2", "prompt")
            assert result2 is None

        stats = cache.get_stats()
        assert stats["l2_hits"] == 1
        assert stats["l2_misses"] == 1

    def test_reset_stats(self) -> None:
        """Test that reset_stats() clears all statistics."""
        cache = LLMCacheService()

        # Set some stats
        cache._stats.l1_hits = 10
        cache._stats.l1_misses = 5
        cache._stats.l2_hits = 3
        cache._stats.l2_misses = 2

        # Reset
        cache.reset_stats()

        stats = cache.get_stats()
        assert stats["l1_hits"] == 0
        assert stats["l1_misses"] == 0
        assert stats["l2_hits"] == 0
        assert stats["l2_misses"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_includes_cache_size(self) -> None:
        """Test that get_stats() includes current L1 cache size."""
        cache = LLMCacheService()

        # Add some entries
        await cache.set("agent", "content1", "prompt", "response1")
        await cache.set("agent", "content2", "prompt", "response2")

        stats = cache.get_stats()
        assert stats["l1_size"] == 2
        assert stats["l1_max_size"] == 1000


class TestCacheClearMethods:
    """Test cache clearing methods."""

    @pytest.mark.asyncio
    async def test_clear_l1_cache(self) -> None:
        """Test that clear() clears L1 cache."""
        cache = LLMCacheService()

        # Add entries
        await cache.set("agent", "content1", "prompt", "response1")
        await cache.set("agent", "content2", "prompt", "response2")

        assert len(cache._l1_cache) == 2

        # Clear
        cache.clear()

        assert len(cache._l1_cache) == 0

        # Verify cache miss after clear
        result = await cache.get("agent", "content1", "prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_preserves_stats(self) -> None:
        """Test that clear() does not reset statistics."""
        cache = LLMCacheService()

        # Generate some stats
        await cache.set("agent", "content", "prompt", "response")
        await cache.get("agent", "content", "prompt")  # Hit

        cache.clear()

        stats = cache.get_stats()
        assert stats["l1_hits"] == 1  # Stats preserved
        assert stats["l1_size"] == 0  # Cache cleared


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_l1_get_error_does_not_raise(self) -> None:
        """Test that L1 cache errors during get don't raise exceptions."""
        cache = LLMCacheService()

        # Mock L1 cache to raise error
        with patch.object(cache._l1_cache, "__contains__", side_effect=RuntimeError("L1 error")):
            # Should not raise - gracefully degrades
            result = await cache.get("agent", "content", "prompt")

        # Should return None (cache miss)
        assert result is None

    @pytest.mark.asyncio
    async def test_l1_set_error_does_not_raise(self) -> None:
        """Test that L1 cache errors during set don't raise exceptions."""
        cache = LLMCacheService()

        # Mock L1 cache to raise error on write
        with patch.object(
            cache._l1_cache, "__setitem__", side_effect=RuntimeError("L1 write error")
        ):
            # Should not raise - gracefully degrades
            await cache.set("agent", "content", "prompt", "response")

        # Should complete without exception

    @pytest.mark.asyncio
    async def test_l2_get_error_does_not_raise(self) -> None:
        """Test that L2 cache errors during get don't raise exceptions."""
        cache = LLMCacheService()

        # Mock L2 cache to raise error
        mock_l2 = MagicMock()
        mock_l2.lookup.side_effect = RuntimeError("L2 lookup error")

        with patch.object(cache, "_get_l2_cache", return_value=mock_l2):
            # Should not raise - gracefully degrades
            result = await cache.get("agent", "content", "prompt")

        assert result is None

        stats = cache.get_stats()
        assert stats["l2_misses"] == 1  # Error counted as miss

    @pytest.mark.asyncio
    async def test_l2_set_error_does_not_raise(self) -> None:
        """Test that L2 cache errors during set don't raise exceptions."""
        cache = LLMCacheService()

        # Mock L2 cache to raise error on update
        mock_l2 = MagicMock()
        mock_l2.update.side_effect = RuntimeError("L2 write error")

        with patch.object(cache, "_get_l2_cache", return_value=mock_l2):
            # Should not raise - gracefully degrades
            await cache.set("agent", "content", "prompt", "response")

        # L1 should still be set
        result = await cache.get("agent", "content", "prompt")
        assert result is not None
        assert result.cache_level == "l1"

    @pytest.mark.asyncio
    async def test_l2_init_error_graceful_degradation(self) -> None:
        """Test that L2 initialization errors are handled gracefully."""
        cache = LLMCacheService()

        # Mock get_semantic_cache to raise error
        with patch(
            "app.shared.services.cache.llm_cache_service.get_semantic_cache",
            side_effect=RuntimeError("Redis connection failed"),
        ):
            # Should not raise - L2 remains None
            l2 = cache._get_l2_cache()

        assert l2 is None

        # Cache should still work with L1 only
        await cache.set("agent", "content", "prompt", "response")
        result = await cache.get("agent", "content", "prompt")
        assert result is not None
        assert result.cache_level == "l1"

    @pytest.mark.asyncio
    async def test_l1_write_error_during_l2_hit_backfill(self) -> None:
        """Test that L1 write errors during L2 hit backfill don't prevent L2 hit."""
        cache = LLMCacheService()

        # Mock L2 cache to return hit
        mock_l2 = MagicMock()
        mock_generation = Mock(spec=Generation)
        mock_generation.text = "L2 response"
        mock_l2.lookup.return_value = [mock_generation]

        # Mock L1 cache to raise error on backfill write
        with (
            patch.object(cache, "_get_l2_cache", return_value=mock_l2),
            patch.object(
                cache._l1_cache, "__setitem__", side_effect=RuntimeError("L1 write error")
            ),
        ):
            # Should still return L2 hit despite L1 write failure
            result = await cache.get("agent", "content", "prompt")

        assert result is not None
        assert result.cache_level == "l2"
        assert result.response == "L2 response"

    def test_clear_error_does_not_raise(self) -> None:
        """Test that clear() errors don't raise exceptions."""
        cache = LLMCacheService()

        # Mock L1 cache to raise error on clear
        with patch.object(cache._l1_cache, "clear", side_effect=RuntimeError("Clear error")):
            # Should not raise - gracefully degrades
            cache.clear()


class TestSingletonPattern:
    """Test singleton pattern via get_llm_cache()."""

    def test_get_llm_cache_singleton(self) -> None:
        """Test that get_llm_cache() returns the same instance."""
        # Clear singleton first
        clear_llm_cache()

        cache1 = get_llm_cache()
        cache2 = get_llm_cache()

        assert cache1 is cache2

    def test_clear_llm_cache_resets_singleton(self) -> None:
        """Test that clear_llm_cache() resets the singleton."""
        cache1 = get_llm_cache()

        clear_llm_cache()

        cache2 = get_llm_cache()

        assert cache1 is not cache2

    @pytest.mark.asyncio
    async def test_singleton_shares_state(self) -> None:
        """Test that singleton instances share cache state."""
        clear_llm_cache()

        cache1 = get_llm_cache()
        cache2 = get_llm_cache()

        # Set via cache1
        await cache1.set("agent", "content", "prompt", "response")

        # Get via cache2 - should hit
        result = await cache2.get("agent", "content", "prompt")

        assert result is not None
        assert result.response == "response"

    def test_clear_llm_cache_clears_l1(self) -> None:
        """Test that clear_llm_cache() clears L1 cache before resetting singleton."""
        clear_llm_cache()

        cache = get_llm_cache()

        # Manually add to L1 cache
        cache._l1_cache["test_key"] = "test_value"
        assert len(cache._l1_cache) > 0

        # Clear singleton
        clear_llm_cache()

        # Get new instance - should have empty cache
        new_cache = get_llm_cache()
        assert len(new_cache._l1_cache) == 0

    @patch("app.shared.services.cache.llm_cache_service.settings")
    def test_singleton_reads_settings(self, mock_settings: Any) -> None:
        """Test that singleton reads configuration from settings."""
        clear_llm_cache()

        # Mock settings
        mock_settings.LLM_CACHE_L1_SIZE = 500
        mock_settings.LLM_CACHE_L1_TTL = 600
        mock_settings.LLM_CACHE_L2_TTL = 43200
        mock_settings.LLM_CACHE_SIMILARITY_THRESHOLD = 0.95

        cache = get_llm_cache()

        assert cache._l1_size == 500
        assert cache._l1_ttl == 600
        assert cache._l2_ttl == 43200
        assert cache._similarity_threshold == 0.95

    @patch("app.shared.services.cache.llm_cache_service.settings")
    def test_singleton_uses_defaults_when_settings_missing(self, mock_settings: Any) -> None:
        """Test that singleton uses defaults when settings attributes missing."""
        clear_llm_cache()

        # Mock settings without cache attributes
        delattr(mock_settings, "LLM_CACHE_L1_SIZE")
        delattr(mock_settings, "LLM_CACHE_L1_TTL")
        delattr(mock_settings, "LLM_CACHE_L2_TTL")
        delattr(mock_settings, "LLM_CACHE_SIMILARITY_THRESHOLD")

        cache = get_llm_cache()

        # Should use defaults
        assert cache._l1_size == 1000
        assert cache._l1_ttl == 300
        assert cache._l2_ttl == 86400
        assert cache._similarity_threshold == 0.92
