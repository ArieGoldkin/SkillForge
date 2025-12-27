"""Unit tests for Tavily Search API service.

VCR-based tests for deterministic HTTP replay:
- Records real Tavily API responses during first run
- Replays responses from cassettes in subsequent runs
- No mocking needed for HTTP calls - VCR handles it
- API keys are automatically filtered from cassettes

To record new cassettes:
    VCR_RECORD_MODE=all pytest tests/unit/services/tools/test_tavily_search.py -k vcr -v

To verify cassettes work without network:
    pytest tests/unit/services/tools/test_tavily_search.py -v --vcr-record=none
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.exceptions import TavilySearchError
from app.shared.services.tools.tavily_search import TavilySearch


@pytest.fixture
def tavily_search():
    """Create a TavilySearch instance with mocked Redis.

    For VCR recording (VCR_RECORD_MODE=all), uses real API key from environment.
    For VCR replay or mock tests, uses a placeholder key.

    Redis is still mocked because we're testing the Tavily HTTP API,
    not the Redis integration (which has its own integration tests).
    """
    # Use real API key when recording VCR cassettes, placeholder otherwise
    vcr_mode = os.environ.get("VCR_RECORD_MODE", "none")
    if vcr_mode in ("all", "new_episodes"):
        # Recording mode - use real API key from settings
        from app.core.config import get_settings

        real_settings = get_settings()
        api_key = real_settings.TAVILY_API_KEY
        if not api_key:
            pytest.skip("TAVILY_API_KEY required for VCR recording")
    else:
        # Replay mode - use placeholder (VCR will intercept anyway)
        api_key = "test-tavily-key-placeholder"

    with (
        patch("app.shared.services.tools.tavily_search.settings") as mock_settings,
        patch("app.shared.services.tools.tavily_search.create_redis_client") as mock_redis,
    ):
        mock_settings.TAVILY_API_KEY = api_key
        mock_settings.REDIS_URL = "redis://localhost:6380"

        # Mock Redis client
        mock_redis_instance = MagicMock()
        mock_redis_instance.get.return_value = None  # No cache by default
        mock_redis.return_value = mock_redis_instance

        tavily = TavilySearch()
        tavily.redis_client = mock_redis_instance
        yield tavily


@pytest.fixture
def tavily_search_no_api_key():
    """Create a TavilySearch instance without API key."""
    with (
        patch("app.shared.services.tools.tavily_search.settings") as mock_settings,
        patch("app.shared.services.tools.tavily_search.create_redis_client") as mock_redis,
    ):
        mock_settings.TAVILY_API_KEY = None
        mock_settings.REDIS_URL = "redis://localhost:6380"

        # Mock Redis client
        mock_redis_instance = MagicMock()
        mock_redis.return_value = mock_redis_instance

        tavily = TavilySearch()
        tavily.redis_client = mock_redis_instance
        return tavily


@pytest.fixture
def tavily_search_no_cache():
    """Create a TavilySearch instance without Redis cache."""
    with (
        patch("app.shared.services.tools.tavily_search.settings") as mock_settings,
        patch("app.shared.services.tools.tavily_search.create_redis_client") as mock_redis,
    ):
        mock_settings.TAVILY_API_KEY = "test-tavily-key"
        mock_settings.REDIS_URL = "redis://localhost:6380"

        # Simulate Redis connection failure
        mock_redis.side_effect = ConnectionError("Redis unavailable")

        return TavilySearch()


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_success(tavily_search):
    """Test successful search returns expected results.

    VCR will record the Tavily API response on first run and replay it afterward.
    """
    result = await tavily_search.search("Python best practices 2025")

    assert result["query"] == "Python best practices 2025"
    assert "answer" in result
    assert "results" in result
    assert len(result["results"]) > 0
    assert "title" in result["results"][0]
    assert "url" in result["results"][0]
    assert "content" in result["results"][0]


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_basic_depth(tavily_search):
    """Test search with basic depth parameter.

    VCR will record the basic depth API response.
    """
    result = await tavily_search.search_basic("FastAPI async patterns")

    assert result["query"] == "FastAPI async patterns"
    assert "answer" in result
    assert "results" in result


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_advanced_depth(tavily_search):
    """Test search with advanced depth parameter.

    VCR will record the advanced depth API response.
    """
    result = await tavily_search.search_advanced("LangGraph workflow examples")

    assert result["query"] == "LangGraph workflow examples"
    assert "answer" in result
    assert "results" in result


@pytest.mark.asyncio
async def test_search_empty_query(tavily_search):
    """Test search with empty query raises TavilySearchError."""
    with pytest.raises(TavilySearchError, match="Search query cannot be empty"):
        await tavily_search.search("")


@pytest.mark.asyncio
async def test_search_whitespace_query(tavily_search):
    """Test search with whitespace query raises TavilySearchError."""
    with pytest.raises(TavilySearchError, match="Search query cannot be empty"):
        await tavily_search.search("   ")


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_query_truncation(tavily_search):
    """Test search truncates overly long queries.

    VCR will record the truncated query being sent to the API.
    """
    # Create a query longer than TAVILY_MAX_QUERY_LENGTH (400 chars)
    long_query = "Python programming best practices " * 20  # ~700 chars

    result = await tavily_search.search(long_query)

    # Verify query was truncated to 400 characters
    assert len(result["query"]) == 400


@pytest.mark.asyncio
async def test_search_no_api_key(tavily_search_no_api_key):
    """Test search without API key raises TavilySearchError."""
    with pytest.raises(TavilySearchError, match="TAVILY_API_KEY not configured"):
        await tavily_search_no_api_key.search("test query")


@pytest.mark.asyncio
async def test_search_rate_limited(tavily_search):
    """Test search with 429 rate limit error raises TavilySearchError."""
    # Mock rate limit response
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    tavily_search.client.post = AsyncMock(return_value=mock_response)

    with pytest.raises(TavilySearchError, match="rate limit exceeded"):
        await tavily_search.search("test query")


@pytest.mark.asyncio
async def test_search_server_error(tavily_search):
    """Test search with 500 server error raises TavilySearchError."""
    # Mock server error response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    tavily_search.client.post = AsyncMock(return_value=mock_response)

    with pytest.raises(TavilySearchError, match="server error"):
        await tavily_search.search("test query")


@pytest.mark.asyncio
async def test_search_http_error(tavily_search):
    """Test search with HTTP 4xx error raises TavilySearchError."""
    # Mock client error response
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    tavily_search.client.post = AsyncMock(return_value=mock_response)

    with pytest.raises(TavilySearchError, match="API error"):
        await tavily_search.search("test query")


@pytest.mark.asyncio
async def test_search_timeout(tavily_search):
    """Test search timeout raises TavilySearchError."""
    # Mock timeout exception
    tavily_search.client.post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

    with pytest.raises(TavilySearchError, match="timed out"):
        await tavily_search.search("test query")


@pytest.mark.asyncio
async def test_search_generic_exception(tavily_search):
    """Test search with generic exception raises TavilySearchError."""
    # Mock generic exception
    tavily_search.client.post = AsyncMock(side_effect=ValueError("Unexpected error"))

    with pytest.raises(TavilySearchError, match="search failed"):
        await tavily_search.search("test query")


@pytest.mark.asyncio
async def test_search_cache_hit(tavily_search):
    """Test search returns cached result when available."""
    import json

    # Mock cached result
    cached_result = {
        "query": "test query",
        "answer": "Cached answer",
        "results": [{"title": "Cached result", "url": "https://cached.com"}],
        "response_time": 0.5,
    }
    tavily_search.redis_client.get.return_value = json.dumps(cached_result)

    # Mock the HTTP client's post method
    tavily_search.client.post = AsyncMock()

    result = await tavily_search.search("test query")

    # Should return cached result without making API call
    assert result["answer"] == "Cached answer"
    assert result["results"][0]["title"] == "Cached result"
    tavily_search.client.post.assert_not_called()


@pytest.mark.asyncio
async def test_search_cache_miss_stores_result(tavily_search):
    """Test search caches result after API call."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "answer": "Fresh answer",
        "results": [],
        "response_time": 1.0,
    }
    tavily_search.client.post = AsyncMock(return_value=mock_response)

    await tavily_search.search("test query")

    # Verify result was cached
    assert tavily_search.redis_client.setex.called
    _cache_key, ttl, cached_data = tavily_search.redis_client.setex.call_args[0]
    assert ttl == 3600  # TAVILY_CACHE_TTL
    assert "Fresh answer" in cached_data


@pytest.mark.asyncio
async def test_search_without_cache(tavily_search_no_cache):
    """Test search works without Redis cache."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "answer": "Answer without cache",
        "results": [],
        "response_time": 1.0,
    }
    tavily_search_no_cache.client.post = AsyncMock(return_value=mock_response)

    result = await tavily_search_no_cache.search("test query")

    # Should work without cache
    assert result["answer"] == "Answer without cache"
    assert tavily_search_no_cache.cache_enabled is False


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_custom_max_results(tavily_search):
    """Test search with custom max_results parameter.

    VCR will record the API response with 10 results.
    """
    result = await tavily_search.search("TypeScript best practices", max_results=10)

    assert result["query"] == "TypeScript best practices"
    assert "results" in result
    # API may return fewer results than requested
    assert len(result["results"]) <= 10


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_include_raw_content(tavily_search):
    """Test search with include_raw_content parameter.

    VCR will record the API response with raw content included.
    """
    result = await tavily_search.search("React Server Components", include_raw_content=True)

    assert result["query"] == "React Server Components"
    assert "results" in result


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_include_images(tavily_search):
    """Test search with include_images parameter.

    VCR will record the API response with images included.
    """
    result = await tavily_search.search("Next.js 15 features", include_images=True)

    assert result["query"] == "Next.js 15 features"
    assert "results" in result


@pytest.mark.asyncio
@pytest.mark.vcr()
async def test_search_no_answer(tavily_search):
    """Test search with include_answer=False.

    VCR will record the API response without the answer field.
    """
    result = await tavily_search.search("PostgreSQL indexing", include_answer=False)

    assert result["query"] == "PostgreSQL indexing"
    # When include_answer=False, API returns null which becomes None in Python
    assert result["answer"] is None


@pytest.mark.asyncio
async def test_search_tavily_error_re_raised(tavily_search):
    """Test that TavilySearchError is re-raised without modification."""
    from app.core.exceptions import ExtractionErrorCode

    # Mock HTTP client to raise TavilySearchError
    original_error = TavilySearchError("Original error", error_code=ExtractionErrorCode.TIMEOUT)
    tavily_search.client.post = AsyncMock(side_effect=original_error)

    with pytest.raises(TavilySearchError, match="Original error") as exc_info:
        await tavily_search.search("test query")

    # Verify it's the same error instance (not wrapped)
    assert exc_info.value is original_error


@pytest.mark.asyncio
async def test_close_client(tavily_search):
    """Test closing the HTTP client and Redis connection."""
    tavily_search.client.aclose = AsyncMock()
    tavily_search.redis_client.close = MagicMock()

    await tavily_search.close()

    tavily_search.client.aclose.assert_called_once()
    tavily_search.redis_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_cache_key_generation(tavily_search):
    """Test cache key includes query and search depth."""
    # Two different queries should have different cache keys
    cache_key_1 = tavily_search._generate_cache_key("query 1", "basic")
    cache_key_2 = tavily_search._generate_cache_key("query 2", "basic")
    assert cache_key_1 != cache_key_2

    # Same query with different depth should have different cache keys
    cache_key_basic = tavily_search._generate_cache_key("test query", "basic")
    cache_key_advanced = tavily_search._generate_cache_key("test query", "advanced")
    assert cache_key_basic != cache_key_advanced


@pytest.mark.asyncio
async def test_cache_error_handling(tavily_search):
    """Test search continues when cache operations fail."""
    # Mock cache get to raise exception
    tavily_search.redis_client.get.side_effect = ConnectionError("Cache unavailable")

    # Mock successful API response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "answer": "Answer",
        "results": [],
        "response_time": 1.0,
    }
    tavily_search.client.post = AsyncMock(return_value=mock_response)

    # Should still succeed despite cache failure
    result = await tavily_search.search("test query")
    assert result["answer"] == "Answer"
