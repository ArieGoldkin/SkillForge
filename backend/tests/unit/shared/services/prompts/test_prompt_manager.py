"""Tests for Langfuse Prompt Management (Issue #379).

Tests multi-level caching, fallback behavior, and version tracking.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.shared.services.prompts.prompt_manager import (
    HARDCODED_PROMPTS,
    LRUCache,
    PromptManager,
)


class TestLRUCache:
    """Test LRU cache with TTL support."""

    def test_cache_hit(self):
        """Test cache hit returns value."""
        cache = LRUCache(max_size=10, ttl_seconds=300)
        cache.set("key1", "value1")

        result = cache.get("key1")

        assert result == "value1"

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = LRUCache(max_size=10, ttl_seconds=300)

        result = cache.get("nonexistent")

        assert result is None

    def test_cache_expiration(self):
        """Test expired items return None."""
        cache = LRUCache(max_size=10, ttl_seconds=1)
        cache.set("key1", "value1")

        # Mock time to simulate expiration
        future_time = datetime.now(UTC) + timedelta(seconds=2)
        with patch("app.shared.services.prompts.prompt_manager.datetime") as mock_dt:
            mock_dt.now.return_value = future_time

            result = cache.get("key1")

        assert result is None

    def test_cache_eviction(self):
        """Test LRU eviction when over capacity."""
        cache = LRUCache(max_size=3, ttl_seconds=300)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Add one more (should evict key1)
        cache.set("key4", "value4")

        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_move_to_end(self):
        """Test accessing item moves it to end (prevents eviction)."""
        cache = LRUCache(max_size=3, ttl_seconds=300)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 (moves to end)
        cache.get("key1")

        # Add key4 (should evict key2, not key1)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # Not evicted
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_cache_clear(self):
        """Test clearing cache removes all items."""
        cache = LRUCache(max_size=10, ttl_seconds=300)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestPromptManager:
    """Test PromptManager with multi-level caching."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        mock = MagicMock()
        mock.get.return_value = None
        mock.setex.return_value = True
        return mock

    @pytest.fixture
    def mock_langfuse(self):
        """Mock Langfuse client."""
        mock = MagicMock()
        mock.get_prompt.return_value = None
        return mock

    @pytest.fixture
    def manager(self, mock_redis, mock_langfuse):
        """Create PromptManager with mocked dependencies."""
        manager = PromptManager(
            l1_cache_size=10,
            l1_ttl_seconds=300,
            l2_ttl_seconds=900,
            enable_langfuse=True,
            enable_redis=True,
        )
        # Override lazy-loaded clients with mocks
        manager._redis_client = mock_redis
        manager._langfuse_client = mock_langfuse
        return manager

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self, manager):
        """Test L1 cache hit skips Redis and Langfuse."""
        # Pre-populate L1 cache
        key = "prompt:test-prompt:production"
        manager.l1_cache.set(key, "cached prompt content")

        result = await manager.get_prompt(
            name="test-prompt",
            variables={},
            label="production",
        )

        assert result == "cached prompt content"
        # Redis should not be called
        manager.redis_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_l2_cache_hit(self, manager, mock_redis):
        """Test L2 Redis cache hit populates L1."""
        mock_redis.get.return_value = b"redis cached prompt"

        result = await manager.get_prompt(
            name="test-prompt",
            variables={},
            label="production",
        )

        assert result == "redis cached prompt"

        # L1 should be populated
        l1_result = manager.l1_cache.get("prompt:test-prompt:production")
        assert l1_result == "redis cached prompt"

    @pytest.mark.asyncio
    async def test_langfuse_fetch(self, manager, mock_langfuse):
        """Test fetching from Langfuse populates both caches."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = "langfuse prompt content"
        mock_prompt.version = 42
        mock_prompt.config = {}
        mock_langfuse.get_prompt.return_value = mock_prompt

        result = await manager.get_prompt(
            name="test-prompt",
            variables={},
            label="production",
        )

        assert result == "langfuse prompt content"

        # Both caches should be populated
        l1_result = manager.l1_cache.get("prompt:test-prompt:production")
        assert l1_result == "langfuse prompt content"

        manager.redis_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_hardcoded_fallback(self, manager, mock_langfuse):
        """Test falling back to hardcoded prompts when Langfuse unavailable."""
        # Langfuse returns None (not found)
        mock_langfuse.get_prompt.return_value = None

        result = await manager.get_prompt(
            name="analysis-supervisor-routing",
            variables={"agent_list": "test agents"},
            label="production",
        )

        # Should use hardcoded prompt
        assert "Analyze content and select relevant agents" in result
        assert "test agents" in result

    @pytest.mark.asyncio
    async def test_prompt_not_found_error(self, manager, mock_langfuse):
        """Test error when prompt not found anywhere."""
        mock_langfuse.get_prompt.return_value = None

        with pytest.raises(ValueError, match="not found in Langfuse or hardcoded"):
            await manager.get_prompt(
                name="nonexistent-prompt",
                variables={},
                label="production",
            )

    @pytest.mark.asyncio
    async def test_variable_compilation(self, manager):
        """Test prompt variable substitution."""
        # Pre-populate cache with template
        key = "prompt:test-prompt:production"
        manager.l1_cache.set(key, "Hello {name}, you are {age} years old.")

        result = await manager.get_prompt(
            name="test-prompt",
            variables={"name": "Alice", "age": 30},
            label="production",
        )

        assert result == "Hello Alice, you are 30 years old."

    @pytest.mark.asyncio
    async def test_missing_variable_error(self, manager):
        """Test error when required variable is missing."""
        key = "prompt:test-prompt:production"
        manager.l1_cache.set(key, "Hello {name}, you are {age} years old.")

        with pytest.raises(KeyError):
            await manager.get_prompt(
                name="test-prompt",
                variables={"name": "Alice"},  # Missing 'age'
                label="production",
            )

    @pytest.mark.asyncio
    async def test_langfuse_disabled(self):
        """Test manager works with Langfuse disabled."""
        with patch(
            "app.shared.services.prompts.prompt_manager.get_langfuse_service",
            return_value=None,
        ):
            manager = PromptManager(
                enable_langfuse=False,
                enable_redis=False,
            )

            result = await manager.get_prompt(
                name="analysis-supervisor-routing",
                variables={"agent_list": "test"},
                label="production",
            )

            assert "Analyze content and select relevant agents" in result

    @pytest.mark.asyncio
    async def test_redis_disabled(self, mock_langfuse):
        """Test manager works with Redis disabled."""
        # Create a mock service that returns the mock_langfuse client
        mock_service = MagicMock()
        mock_service.sdk_client = mock_langfuse
        with patch(
            "app.shared.services.prompts.prompt_manager.get_langfuse_service",
            return_value=mock_service,
        ):
            manager = PromptManager(
                enable_langfuse=True,
                enable_redis=False,
            )

            # Pre-populate L1
            key = "prompt:test-prompt:production"
            manager.l1_cache.set(key, "test content")

            result = await manager.get_prompt(
                name="test-prompt",
                variables={},
                label="production",
            )

            assert result == "test content"

    @pytest.mark.asyncio
    async def test_get_prompt_metadata_langfuse(self, manager, mock_langfuse):
        """Test metadata retrieval from Langfuse."""
        mock_prompt = MagicMock()
        mock_prompt.prompt = "test prompt"
        mock_prompt.version = 42
        mock_prompt.config = {}
        mock_langfuse.get_prompt.return_value = mock_prompt

        metadata = await manager.get_prompt_metadata(
            name="test-prompt",
            label="production",
        )

        assert metadata["prompt_name"] == "test-prompt"
        assert metadata["prompt_version"] == 42
        assert metadata["prompt_label"] == "production"
        assert metadata["prompt_source"] == "langfuse"

    @pytest.mark.asyncio
    async def test_get_prompt_metadata_hardcoded(self, manager, mock_langfuse):
        """Test metadata retrieval for hardcoded prompts."""
        mock_langfuse.get_prompt.return_value = None

        metadata = await manager.get_prompt_metadata(
            name="analysis-supervisor-routing",
            label="production",
        )

        assert metadata["prompt_name"] == "analysis-supervisor-routing"
        assert metadata["prompt_version"] == "hardcoded"
        assert metadata["prompt_label"] == "production"
        assert metadata["prompt_source"] == "hardcoded"

    @pytest.mark.asyncio
    async def test_redis_connection_failure_graceful(self, manager):
        """Test graceful degradation when Redis connection fails."""
        # Simulate Redis connection failure
        manager._redis_client = None

        # Pre-populate L1 cache
        key = "prompt:test-prompt:production"
        manager.l1_cache.set(key, "test content")

        result = await manager.get_prompt(
            name="test-prompt",
            variables={},
            label="production",
        )

        # Should still work with L1 cache
        assert result == "test content"

    @pytest.mark.asyncio
    async def test_langfuse_fetch_failure_falls_back(self, manager, mock_langfuse):
        """Test falling back to hardcoded when Langfuse fetch fails."""
        # Simulate Langfuse API error
        mock_langfuse.get_prompt.side_effect = Exception("API error")

        result = await manager.get_prompt(
            name="analysis-supervisor-routing",
            variables={"agent_list": "test"},
            label="production",
        )

        # Should fallback to hardcoded
        assert "Analyze content and select relevant agents" in result

    def test_clear_caches(self, manager, mock_redis):
        """Test clearing all caches."""
        # Populate L1
        manager.l1_cache.set("key1", "value1")

        # Mock Redis scan_iter
        mock_redis.scan_iter.return_value = iter([b"prompt:key1:production"])

        manager.clear_caches()

        # L1 should be cleared
        assert manager.l1_cache.get("key1") is None

        # Redis delete should be called
        mock_redis.delete.assert_called()

    @pytest.mark.asyncio
    async def test_supervisor_prompt_compilation(self, manager):
        """Test supervisor prompt compiles correctly with agent list."""
        # Use hardcoded supervisor prompt
        result = await manager.get_prompt(
            name="analysis-supervisor-routing",
            variables={"agent_list": "- security_auditor\n- performance_analyst"},
            label="production",
        )

        # Should contain agent list
        assert "security_auditor" in result
        assert "performance_analyst" in result

        # Should contain guidelines
        assert "MINIMUM 3 AGENTS REQUIRED" in result
        assert "TUTORIAL ANALYSIS" in result

    def test_hardcoded_prompts_exist(self):
        """Test hardcoded prompts are defined."""
        assert "analysis-supervisor-routing" in HARDCODED_PROMPTS
        assert len(HARDCODED_PROMPTS["analysis-supervisor-routing"]) > 100


class TestPromptManagerIntegration:
    """Integration tests with real dependencies (when available)."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_cache_flow(self):
        """Test full flow: L1 miss → L2 miss → Langfuse → cache population."""
        # This test requires real Redis and Langfuse connections
        # Skip if not available in test environment
        pytest.skip("Requires live Redis and Langfuse - run in integration suite")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_offline_operation(self):
        """Test manager works completely offline with hardcoded prompts."""
        manager = PromptManager(
            enable_langfuse=False,
            enable_redis=False,
        )

        result = await manager.get_prompt(
            name="analysis-supervisor-routing",
            variables={"agent_list": "- security_auditor"},
            label="production",
        )

        assert "Analyze content and select relevant agents" in result
        assert "security_auditor" in result
