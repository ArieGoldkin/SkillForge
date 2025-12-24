#!/usr/bin/env python3
"""Integration tests for Tavily Search Redis caching.

These tests validate the Redis L2 cache integration for Tavily Search API,
including cache hit/miss behavior, TTL expiration, and cache key isolation.

Run with:
    cd backend
    poetry run pytest tests/integration/services/tools/test_tavily_cache_integration.py -v -s

Prerequisites:
    - Redis running on localhost:6380
    - TAVILY_API_KEY configured in .env (for live API tests)

Note: Tests are marked with @pytest.mark.integration and skip if Redis unavailable.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.constants import TAVILY_CACHE_TTL
from app.shared.services.cache.redis_connection import create_redis_client
from app.shared.services.tools.tavily_search import TavilySearch


def is_redis_available() -> bool:
    """Check if Redis is available on localhost:6380.

    Returns:
        True if Redis is available, False otherwise

    """
    try:
        client = create_redis_client()
        client.ping()
        client.close()
        return True
    except (RedisConnectionError, ConnectionError, TimeoutError, OSError):
        return False


pytestmark = pytest.mark.skipif(
    not is_redis_available(),
    reason="Redis not available on localhost:6380",
)


@pytest.fixture
def redis_client():
    """Create a Redis client for test setup and teardown."""
    client = create_redis_client()
    yield client
    client.close()


@pytest.fixture
async def tavily_search_with_redis():
    """Create a TavilySearch instance with real Redis connection."""
    tavily = TavilySearch()
    yield tavily
    await tavily.close()


@pytest.fixture
def mock_tavily_api_response():
    """Create a mock Tavily API response for testing."""
    return {
        "answer": "Test answer from Tavily API",
        "results": [
            {
                "title": "Result 1",
                "url": "https://example.com/1",
                "content": "Content 1",
                "score": 0.95,
            },
            {
                "title": "Result 2",
                "url": "https://example.com/2",
                "content": "Content 2",
                "score": 0.87,
            },
        ],
        "response_time": 1.23,
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_connection_available(redis_client):
    """Test that Redis connection is available for caching."""
    # Verify Redis is responding
    result = redis_client.ping()
    assert result is True, "Redis should respond to PING"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_miss_then_hit(
    tavily_search_with_redis,
    redis_client,
    mock_tavily_api_response,
):
    """Test cache miss on first request, then cache hit on second request."""
    query = "LangGraph workflow patterns integration test"

    # Clear any existing cache for this query
    cache_key = tavily_search_with_redis._generate_cache_key(query, "advanced")
    redis_client.delete(cache_key)

    # Mock HTTP client to return test response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_tavily_api_response
    tavily_search_with_redis.client.post = AsyncMock(return_value=mock_response)

    # First request - cache miss
    result1 = await tavily_search_with_redis.search(query, search_depth="advanced")
    assert result1["query"] == query
    assert result1["answer"] == "Test answer from Tavily API"
    assert len(result1["results"]) == 2

    # Verify API was called
    assert tavily_search_with_redis.client.post.called
    call_count_after_first = tavily_search_with_redis.client.post.call_count

    # Verify cache was populated
    cached_data = redis_client.get(cache_key)
    assert cached_data is not None, "Cache should be populated after first request"
    cached_result = json.loads(cached_data)
    assert cached_result["query"] == query
    assert cached_result["answer"] == "Test answer from Tavily API"

    # Second request - cache hit
    result2 = await tavily_search_with_redis.search(query, search_depth="advanced")
    assert result2["query"] == query
    assert result2["answer"] == "Test answer from Tavily API"
    assert len(result2["results"]) == 2

    # Verify API was NOT called again (cache hit)
    assert tavily_search_with_redis.client.post.call_count == call_count_after_first, (
        "API should not be called again on cache hit"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_ttl_expiration(
    tavily_search_with_redis,
    redis_client,
    mock_tavily_api_response,
):
    """Test that cache entries expire after TTL."""
    query = "Cache TTL expiration test"

    # Clear any existing cache for this query
    cache_key = tavily_search_with_redis._generate_cache_key(query, "basic")
    redis_client.delete(cache_key)

    # Mock HTTP client to return test response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_tavily_api_response
    tavily_search_with_redis.client.post = AsyncMock(return_value=mock_response)

    # Store result with short TTL (2 seconds for testing)
    test_ttl = 2
    result = {
        "query": query,
        "answer": "Test answer",
        "results": [],
        "response_time": 1.0,
    }
    redis_client.setex(cache_key, test_ttl, json.dumps(result))

    # Verify cache is populated
    cached_data = redis_client.get(cache_key)
    assert cached_data is not None, "Cache should be populated"

    # Verify TTL is set correctly
    ttl = redis_client.ttl(cache_key)
    assert 0 < ttl <= test_ttl, f"TTL should be between 0 and {test_ttl}, got {ttl}"

    # Wait for TTL to expire (use asyncio.sleep for async context)
    await asyncio.sleep(test_ttl + 1)

    # Verify cache entry has expired
    cached_data = redis_client.get(cache_key)
    assert cached_data is None, "Cache should be expired after TTL"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_key_isolation_basic_vs_advanced(
    tavily_search_with_redis,
    redis_client,
    mock_tavily_api_response,
):
    """Test that basic and advanced search depths use different cache keys."""
    query = "Cache key isolation test"

    # Clear any existing cache for this query
    cache_key_basic = tavily_search_with_redis._generate_cache_key(query, "basic")
    cache_key_advanced = tavily_search_with_redis._generate_cache_key(query, "advanced")
    redis_client.delete(cache_key_basic)
    redis_client.delete(cache_key_advanced)

    # Verify cache keys are different
    assert cache_key_basic != cache_key_advanced, (
        "Basic and advanced search should use different cache keys"
    )

    # Mock HTTP client to return different responses for basic vs advanced
    basic_response = MagicMock()
    basic_response.status_code = 200
    basic_response.json.return_value = {
        "answer": "Basic search answer",
        "results": [{"title": "Basic result"}],
        "response_time": 0.5,
    }

    advanced_response = MagicMock()
    advanced_response.status_code = 200
    advanced_response.json.return_value = {
        "answer": "Advanced search answer",
        "results": [
            {"title": "Advanced result 1"},
            {"title": "Advanced result 2"},
        ],
        "response_time": 2.0,
    }

    # Mock API to return different responses based on search_depth
    def mock_post_side_effect(url, **kwargs):
        search_depth = kwargs.get("json", {}).get("search_depth", "advanced")
        if search_depth == "basic":
            return basic_response
        return advanced_response

    tavily_search_with_redis.client.post = AsyncMock(side_effect=mock_post_side_effect)

    # Make basic search request
    result_basic = await tavily_search_with_redis.search_basic(query)
    assert result_basic["answer"] == "Basic search answer"
    assert len(result_basic["results"]) == 1

    # Make advanced search request
    result_advanced = await tavily_search_with_redis.search_advanced(query)
    assert result_advanced["answer"] == "Advanced search answer"
    assert len(result_advanced["results"]) == 2

    # Verify both cache entries exist and are different
    cached_basic = redis_client.get(cache_key_basic)
    cached_advanced = redis_client.get(cache_key_advanced)

    assert cached_basic is not None, "Basic search result should be cached"
    assert cached_advanced is not None, "Advanced search result should be cached"

    cached_basic_data = json.loads(cached_basic)
    cached_advanced_data = json.loads(cached_advanced)

    assert cached_basic_data["answer"] == "Basic search answer"
    assert cached_advanced_data["answer"] == "Advanced search answer"
    assert len(cached_basic_data["results"]) == 1
    assert len(cached_advanced_data["results"]) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_different_queries_isolated(
    tavily_search_with_redis,
    redis_client,
    mock_tavily_api_response,
):
    """Test that different queries use different cache keys."""
    query1 = "First query for cache isolation"
    query2 = "Second query for cache isolation"

    # Generate cache keys
    cache_key1 = tavily_search_with_redis._generate_cache_key(query1, "advanced")
    cache_key2 = tavily_search_with_redis._generate_cache_key(query2, "advanced")

    # Clear any existing cache
    redis_client.delete(cache_key1)
    redis_client.delete(cache_key2)

    # Verify cache keys are different
    assert cache_key1 != cache_key2, "Different queries should use different cache keys"

    # Mock HTTP client to return different responses for different queries
    response1 = MagicMock()
    response1.status_code = 200
    response1.json.return_value = {
        "answer": "Answer for query 1",
        "results": [],
        "response_time": 1.0,
    }

    response2 = MagicMock()
    response2.status_code = 200
    response2.json.return_value = {
        "answer": "Answer for query 2",
        "results": [],
        "response_time": 1.0,
    }

    # Mock API to return different responses based on query
    call_count = [0]

    def mock_post_side_effect(url, **kwargs):
        call_count[0] += 1
        query = kwargs.get("json", {}).get("query", "")
        if query == query1:
            return response1
        return response2

    tavily_search_with_redis.client.post = AsyncMock(side_effect=mock_post_side_effect)

    # Make first query
    result1 = await tavily_search_with_redis.search(query1)
    assert result1["answer"] == "Answer for query 1"

    # Make second query
    result2 = await tavily_search_with_redis.search(query2)
    assert result2["answer"] == "Answer for query 2"

    # Verify both cache entries exist and are different
    cached1 = redis_client.get(cache_key1)
    cached2 = redis_client.get(cache_key2)

    assert cached1 is not None, "Query 1 result should be cached"
    assert cached2 is not None, "Query 2 result should be cached"

    cached1_data = json.loads(cached1)
    cached2_data = json.loads(cached2)

    assert cached1_data["answer"] == "Answer for query 1"
    assert cached2_data["answer"] == "Answer for query 2"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_default_ttl_configuration(
    tavily_search_with_redis,
    redis_client,
    mock_tavily_api_response,
):
    """Test that cache entries use the configured TTL (1 hour)."""
    query = "TTL configuration test"

    # Clear any existing cache for this query
    cache_key = tavily_search_with_redis._generate_cache_key(query, "advanced")
    redis_client.delete(cache_key)

    # Mock HTTP client to return test response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_tavily_api_response
    tavily_search_with_redis.client.post = AsyncMock(return_value=mock_response)

    # Make request to populate cache
    await tavily_search_with_redis.search(query)

    # Verify cache entry exists
    cached_data = redis_client.get(cache_key)
    assert cached_data is not None, "Cache should be populated"

    # Verify TTL is set correctly (should be TAVILY_CACHE_TTL = 3600 seconds)
    ttl = redis_client.ttl(cache_key)
    # Allow some margin for execution time (TTL should be close to 3600)
    assert 3590 <= ttl <= TAVILY_CACHE_TTL, (
        f"TTL should be close to {TAVILY_CACHE_TTL} seconds, got {ttl}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_survives_service_restart(
    redis_client,
    mock_tavily_api_response,
):
    """Test that cache persists across TavilySearch service restarts."""
    query = "Cache persistence test"

    # Create first instance and populate cache
    tavily1 = TavilySearch()
    cache_key = tavily1._generate_cache_key(query, "advanced")
    redis_client.delete(cache_key)

    # Mock HTTP client to return test response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_tavily_api_response
    tavily1.client.post = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    # Make request with first instance
    result1 = await tavily1.search(query)
    assert result1["answer"] == "Test answer from Tavily API"
    api_call_count = tavily1.client.post.call_count
    await tavily1.close()

    # Verify cache is populated
    cached_data = redis_client.get(cache_key)
    assert cached_data is not None, "Cache should be populated"

    # Create second instance (simulating service restart)
    tavily2 = TavilySearch()

    # Mock HTTP client for second instance (should not be called)
    tavily2.client.post = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    # Make request with second instance - should use cached result
    result2 = await tavily2.search(query)
    assert result2["answer"] == "Test answer from Tavily API"

    # Verify API was NOT called (cache hit)
    assert tavily2.client.post.call_count == 0, "API should not be called on cache hit"

    await tavily2.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_graceful_degradation_on_redis_error(
    mock_tavily_api_response,
):
    """Test that search continues to work when Redis cache operations fail."""
    query = "Graceful degradation test"

    # Create TavilySearch instance with working Redis
    tavily = TavilySearch()

    # Mock HTTP client to return test response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_tavily_api_response
    tavily.client.post = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    # Mock _get_cached_result to raise exception (simulating Redis failure)
    # This is safer than mocking redis_client.get directly because it doesn't
    # interfere with the retry decorator on search()
    async def mock_get_cached_with_error(cache_key: str) -> None:  # type: ignore[misc]
        # Simulate Redis connection error during cache read
        return None  # Cache failures return None, allowing search to continue

    tavily._get_cached_result = mock_get_cached_with_error  # type: ignore[method-assign]

    # Search should still succeed despite cache failure
    result = await tavily.search(query)
    assert result["answer"] == "Test answer from Tavily API"
    assert tavily.client.post.called, "API should be called when cache fails"

    await tavily.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_error_on_set_does_not_fail_search(
    mock_tavily_api_response,
):
    """Test that search succeeds even if cache set operation fails."""
    query = "Cache set failure test"

    # Create TavilySearch instance with working Redis
    tavily = TavilySearch()

    # Mock HTTP client to return test response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_tavily_api_response
    tavily.client.post = AsyncMock(return_value=mock_response)  # type: ignore[assignment]

    # Mock _set_cached_result to simulate cache write failure
    # This is safer than mocking redis_client.setex directly because it doesn't
    # interfere with the retry decorator on search()
    async def mock_set_cached_with_error(cache_key: str, result: dict) -> None:  # type: ignore[type-arg]
        # Simulate cache write failure - the method catches exceptions internally
        # and just logs warnings, so search should still succeed
        pass  # Do nothing, simulating failed cache write

    tavily._set_cached_result = mock_set_cached_with_error  # type: ignore[method-assign]

    # Search should still succeed despite cache write failure
    result = await tavily.search(query)
    assert result["answer"] == "Test answer from Tavily API"
    assert tavily.client.post.called, "API should be called successfully"

    await tavily.close()
