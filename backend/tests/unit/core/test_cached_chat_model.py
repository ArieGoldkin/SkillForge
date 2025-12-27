"""Tests for CachedChatModel wrapper.

Tests cover:
- L1 cache hits and misses
- Cache key generation (deterministic)
- Graceful degradation on errors
- LangChain compatibility (with_structured_output, with_fallbacks)
- Cache bypass for testing
- Sync and async methods
"""

from typing import Any
from unittest.mock import patch

import pytest
from langchain_core.language_models import FakeListChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import BaseModel

from app.core.cached_chat_model import CachedChatModel


class TestCachedChatModelBasics:
    """Test basic caching functionality."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model)

        assert cached.model == model
        assert cached.agent_type == "default"
        assert cached.cache_enabled is True
        # FakeListChatModel's _llm_type is "fake-list-chat-model"
        assert cached._llm_type == "cached_fake-list-chat-model"
        assert "cache_enabled" in cached._identifying_params

    def test_init_with_custom_params(self) -> None:
        """Test initialization with custom agent type."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(
            model=model,
            agent_type="tech_explainer",
            cache_enabled=False,
        )

        assert cached.agent_type == "tech_explainer"
        assert cached.cache_enabled is False

    def test_llm_type_delegation(self) -> None:
        """Test that _llm_type delegates to wrapped model."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model)

        # Should prefix with "cached_"
        assert cached._llm_type == f"cached_{model._llm_type}"

    def test_identifying_params_includes_cache_config(self) -> None:
        """Test that identifying params include cache configuration."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(
            model=model,
            agent_type="test_agent",
            cache_enabled=True,
        )

        params = cached._identifying_params
        assert params["cache_enabled"] is True
        assert params["agent_type"] == "test_agent"
        # Should also include wrapped model's params
        assert "responses" in params  # FakeListChatModel param


class TestCacheKeyGeneration:
    """Test cache key generation logic."""

    def test_cache_key_deterministic(self) -> None:
        """Test that same messages produce same cache key."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model, agent_type="test")

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Hello world"),
        ]

        key1 = cached._generate_cache_key(messages)
        key2 = cached._generate_cache_key(messages)

        assert key1 == key2
        assert key1.startswith("cached_model:test:")
        assert len(key1.split(":")[-1]) == 64  # SHA256 hex = 64 chars

    def test_cache_key_different_messages(self) -> None:
        """Test that different messages produce different keys."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model)

        messages1 = [HumanMessage(content="Hello")]
        messages2 = [HumanMessage(content="Goodbye")]

        key1 = cached._generate_cache_key(messages1)
        key2 = cached._generate_cache_key(messages2)

        assert key1 != key2

    def test_cache_key_different_agent_types(self) -> None:
        """Test that different agent types produce different keys."""
        model = FakeListChatModel(responses=["response"])
        messages = [HumanMessage(content="Hello")]

        cached1 = CachedChatModel(model=model, agent_type="agent1")
        cached2 = CachedChatModel(model=model, agent_type="agent2")

        key1 = cached1._generate_cache_key(messages)
        key2 = cached2._generate_cache_key(messages)

        assert key1 != key2
        assert "agent1" in key1
        assert "agent2" in key2

    def test_cache_key_message_order_matters(self) -> None:
        """Test that message order affects cache key."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model)

        messages1 = [
            HumanMessage(content="Hello"),
            AIMessage(content="Hi"),
        ]
        messages2 = [
            AIMessage(content="Hi"),
            HumanMessage(content="Hello"),
        ]

        key1 = cached._generate_cache_key(messages1)
        key2 = cached._generate_cache_key(messages2)

        assert key1 != key2


class TestL1Caching:
    """Test L1 (in-memory) cache behavior."""

    @pytest.mark.asyncio
    async def test_l1_cache_hit(self) -> None:
        """Test that second identical call hits L1 cache."""
        model = FakeListChatModel(responses=["First", "Second"])
        cached = CachedChatModel(model=model)

        messages = [HumanMessage(content="Hello")]

        # First call - cache miss
        result1 = await cached.ainvoke(messages)
        assert result1.content == "First"

        # Second call - should hit L1 cache (same response)
        result2 = await cached.ainvoke(messages)
        assert result2.content == "First"  # Cached, not "Second"

    @pytest.mark.asyncio
    async def test_l1_cache_miss_different_messages(self) -> None:
        """Test that different messages miss L1 cache."""
        model = FakeListChatModel(responses=["First", "Second"])
        cached = CachedChatModel(model=model)

        # First call
        result1 = await cached.ainvoke([HumanMessage(content="Hello")])
        assert result1.content == "First"

        # Different message - cache miss
        result2 = await cached.ainvoke([HumanMessage(content="Goodbye")])
        assert result2.content == "Second"

    @pytest.mark.asyncio
    async def test_l1_cache_disabled(self) -> None:
        """Test that caching can be disabled."""
        model = FakeListChatModel(responses=["First", "Second"])
        cached = CachedChatModel(model=model, cache_enabled=False)

        messages = [HumanMessage(content="Hello")]

        result1 = await cached.ainvoke(messages)
        assert result1.content == "First"

        # Second call - cache disabled, should get new response
        result2 = await cached.ainvoke(messages)
        assert result2.content == "Second"

    def test_l1_cache_storage_with_lru_eviction(self) -> None:
        """Test that L1 cache evicts old entries when full."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model)

        # Create a mock result
        mock_result = ChatResult(generations=[ChatGeneration(message=AIMessage(content="test"))])

        # Fill cache to capacity (100 entries)
        for i in range(100):
            key = f"cached_model:default:key_{i}"
            cached._store_l1_cache(key, mock_result)

        assert len(cached._l1_cache) == 100

        # Add one more - should evict oldest
        cached._store_l1_cache("cached_model:default:key_new", mock_result)
        assert len(cached._l1_cache) == 100
        assert "cached_model:default:key_new" in cached._l1_cache

    def test_clear_cache(self) -> None:
        """Test that clear_cache() clears L1 cache."""
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model)

        # Add to cache
        mock_result = ChatResult(generations=[ChatGeneration(message=AIMessage(content="test"))])
        cached._store_l1_cache("test_key", mock_result)
        assert len(cached._l1_cache) > 0

        # Clear cache
        cached.clear_cache()
        assert len(cached._l1_cache) == 0


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    @pytest.mark.asyncio
    async def test_llm_error_propagates(self) -> None:
        """Test that LLM errors are propagated (not caught)."""

        class ErrorModel(FakeListChatModel):
            async def _agenerate(self, *args: Any, **kwargs: Any) -> ChatResult:
                raise ValueError("LLM error")

        model = ErrorModel(responses=["response"])
        cached = CachedChatModel(model=model)

        with pytest.raises(ValueError, match="LLM error"):
            await cached.ainvoke([HumanMessage(content="Hello")])

    @pytest.mark.asyncio
    async def test_cache_error_does_not_block_llm_call(self) -> None:
        """Test that cache failures don't prevent LLM calls.

        This test verifies graceful degradation - cache errors are logged
        but don't prevent the LLM from being called and returning a result.
        """
        model = FakeListChatModel(responses=["Success"])
        cached = CachedChatModel(model=model)

        # Mock _check_l1_cache to raise error - should be caught and logged
        with patch.object(cached, "_check_l1_cache", side_effect=RuntimeError("Cache error")):
            # Should still get result from LLM (graceful degradation)
            result = await cached.ainvoke([HumanMessage(content="Hello")])
            assert result.content == "Success"


class TestLangChainCompatibility:
    """Test compatibility with LangChain features."""

    @pytest.mark.asyncio
    async def test_with_structured_output(self) -> None:
        """Test that with_structured_output() works with caching.

        Note: FakeListChatModel doesn't implement with_structured_output,
        so we test that the method exists and is callable (delegates to wrapped model).
        """
        model = FakeListChatModel(responses=["response"])
        cached = CachedChatModel(model=model)

        # Verify the method exists and is callable
        assert hasattr(cached, "with_structured_output")
        assert callable(cached.with_structured_output)

        # FakeListChatModel raises NotImplementedError for with_structured_output
        # This is expected behavior - the wrapper correctly delegates to the base model
        with pytest.raises(NotImplementedError):
            cached.with_structured_output(BaseModel)

    @pytest.mark.asyncio
    async def test_with_fallbacks(self) -> None:
        """Test that with_fallbacks() works with caching."""

        class ErrorModel(FakeListChatModel):
            async def _agenerate(self, *args: Any, **kwargs: Any) -> ChatResult:
                raise ValueError("Primary failed")

        # Primary model that fails
        primary = ErrorModel(responses=["primary"])
        cached_primary = CachedChatModel(model=primary)

        # Fallback model that succeeds
        fallback = FakeListChatModel(responses=["fallback"])
        cached_fallback = CachedChatModel(model=fallback)

        # Apply fallback
        with_fallback = cached_primary.with_fallbacks([cached_fallback])

        # Should use fallback
        result = await with_fallback.ainvoke([HumanMessage(content="Test")])
        assert result.content == "fallback"

    @pytest.mark.asyncio
    async def test_batch_invocation(self) -> None:
        """Test that batch() works with caching."""
        model = FakeListChatModel(responses=["First", "Second", "Third"])
        cached = CachedChatModel(model=model)

        messages_batch = [
            [HumanMessage(content="Hello")],
            [HumanMessage(content="Goodbye")],
        ]

        results = await cached.abatch(messages_batch)
        assert len(results) == 2
        assert results[0].content == "First"
        assert results[1].content == "Second"

    @pytest.mark.asyncio
    async def test_streaming_not_cached(self) -> None:
        """Test that streaming calls work but aren't cached.

        Note: Streaming is typically not cached because we can't cache
        partial chunks. The wrapper should still allow streaming to pass through.
        """
        model = FakeListChatModel(responses=["Streamed response"])
        cached = CachedChatModel(model=model)

        # Collect streamed chunks (using list comprehension as suggested by PERF401)
        chunks = [chunk async for chunk in cached.astream([HumanMessage(content="Hello")])]

        # Should have received chunks (FakeListChatModel returns full message)
        assert len(chunks) > 0
        # Concatenate chunk contents
        full_content = "".join(chunk.content for chunk in chunks if chunk.content)
        assert "Streamed response" in full_content


class TestSyncMethods:
    """Test synchronous methods for compatibility."""

    def test_sync_generate_delegates(self) -> None:
        """Test that sync _generate() delegates to wrapped model."""
        model = FakeListChatModel(responses=["Sync response"])
        cached = CachedChatModel(model=model)

        messages = [HumanMessage(content="Hello")]
        result = cached._generate(messages)

        assert len(result.generations) > 0
        assert result.generations[0].message.content == "Sync response"

    def test_sync_invoke(self) -> None:
        """Test that sync invoke() works (delegates to wrapped model)."""
        model = FakeListChatModel(responses=["Sync response"])
        cached = CachedChatModel(model=model)

        result = cached.invoke([HumanMessage(content="Hello")])
        assert result.content == "Sync response"
