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
    async def test_missing_variable_preserved(self, manager):
        """Test that missing variables are preserved (for JSON compatibility).

        Issue #586: Changed from KeyError to preservation. When prompts contain
        JSON examples like {"key": "value"}, we can't distinguish template vars
        from JSON keys. Missing variables are now left as-is instead of raising.
        """
        key = "prompt:test-prompt:production"
        manager.l1_cache.set(key, "Hello {name}, you are {age} years old.")

        result = await manager.get_prompt(
            name="test-prompt",
            variables={"name": "Alice"},  # Missing 'age' - now preserved
            label="production",
        )
        # {age} is preserved because it wasn't in the variables dict
        assert result == "Hello Alice, you are {age} years old."

    @pytest.mark.asyncio
    async def test_json_in_prompt_preserved(self, manager):
        """Test that JSON examples in prompts are not modified.

        Issue #586: Langfuse prompts often contain JSON examples like:
        {"immediate_actions": [...], "quick_wins": [...]}

        The old str.format() would interpret these as template variables
        and raise KeyError. The new regex-based substitution only replaces
        explicitly provided variables.
        """
        key = "prompt:json-prompt:production"
        json_prompt = '''Analyze the content and return JSON:
{
  "immediate_actions": ["action1", "action2"],
  "findings_count": {findings_count}
}

Content to analyze: {content}'''
        manager.l1_cache.set(key, json_prompt)

        result = await manager.get_prompt(
            name="json-prompt",
            variables={"content": "My article", "findings_count": 5},
            label="production",
        )
        # JSON structure should be preserved
        assert '"immediate_actions"' in result
        assert '"action1"' in result
        # Template variables should be substituted
        assert "My article" in result
        assert "5" in result  # findings_count substituted

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
        """Test full flow: L1 miss → L2 miss → Langfuse → cache population.

        This test verifies the cache flow works correctly regardless of whether
        Langfuse has content or falls back to hardcoded prompts. The key is that:
        1. First call should fetch from source (Langfuse or hardcoded)
        2. Second call should hit L1 cache (same result, faster)
        3. Result should always have content (never empty)
        """
        import os
        import socket

        def check_port(host: str, port: int) -> bool:
            """Check if a port is open."""
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()
                return result == 0
            except Exception:
                return False

        # Check Redis on multiple common ports (6380=dev, 6381=test, 6379=default)
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port_env = os.environ.get("REDIS_PORT")
        redis_ports_to_try = [int(redis_port_env)] if redis_port_env else [6380, 6381, 6379]
        redis_available = any(check_port(redis_host, port) for port in redis_ports_to_try)

        # Check Langfuse on multiple common ports (3000=dev, 3001=test)
        # LANGFUSE_HOST may be a URL like http://localhost:3001, so extract host/port
        from urllib.parse import urlparse

        langfuse_env = os.environ.get("LANGFUSE_HOST", "localhost")
        if langfuse_env.startswith("http"):
            parsed = urlparse(langfuse_env)
            langfuse_host = parsed.hostname or "localhost"
            # If port is in URL, use it; otherwise check common ports
            langfuse_ports_to_try = [parsed.port] if parsed.port else [3000, 3001]
        else:
            langfuse_host = langfuse_env
            langfuse_port_env = os.environ.get("LANGFUSE_PORT")
            langfuse_ports_to_try = [int(langfuse_port_env)] if langfuse_port_env else [3000, 3001]
        langfuse_available = any(check_port(langfuse_host, port) for port in langfuse_ports_to_try)

        if not redis_available or not langfuse_available:
            pytest.skip(
                f"Live services not available (Redis: {redis_available}, Langfuse: {langfuse_available})"
            )

        # Create manager with real connections
        manager = PromptManager(
            enable_langfuse=True,
            enable_redis=True,
        )

        # Test L1 miss → L2 miss → Source fetch → cache population
        prompt_name = "analysis-supervisor-routing"

        # First call - should fetch from source (Langfuse with content, or fallback to hardcoded)
        # The manager should return non-empty content regardless of Langfuse state
        # Note: Routing prompt requires agent_list variable
        test_variables = {"agent_list": "- test_agent_1\n- test_agent_2"}
        result1 = await manager.get_prompt(
            name=prompt_name,
            variables=test_variables,
            label="production",
        )
        # Verify we got content (from Langfuse or hardcoded fallback)
        assert result1 is not None, "First call should return a prompt"
        assert len(result1) > 0, "Prompt should have content (from Langfuse or hardcoded)"
        assert "agent" in result1.lower(), "Routing prompt should mention agents"

        # Second call - should hit L1 cache (same result, faster)
        result2 = await manager.get_prompt(
            name=prompt_name,
            variables=test_variables,
            label="production",
        )
        assert result2 == result1, "L1 cache should return same result"

        # Third call after clearing L1 - should hit L2 Redis cache (if Langfuse had content)
        # or return hardcoded again (if Langfuse was empty)
        manager.l1_cache.clear()
        result3 = await manager.get_prompt(
            name=prompt_name,
            variables=test_variables,
            label="production",
        )
        # Result should be same (from L2 cache or hardcoded)
        # Note: If Langfuse was empty, we don't cache hardcoded prompts, so result3 == result1
        # If Langfuse had content, result3 comes from L2 cache and should equal result1
        assert result3 == result1, "Result should be consistent across cache levels"

        # Verify metadata is available
        metadata = await manager.get_prompt_metadata(
            name=prompt_name,
            label="production",
        )
        assert metadata is not None
        assert metadata["prompt_name"] == prompt_name
        # Source should be either "langfuse" (if Langfuse had content) or "hardcoded" (fallback)
        assert metadata["prompt_source"] in ["langfuse", "hardcoded"]

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
