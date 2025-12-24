"""Unit tests for GitHub Search tool.

Tests for GitHubSearch API client used by COMMUNITY_PULSE agent.
Issue #501: Tier 3 Research Agents implementation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.services.tools.github_search import (
    GITHUB_MAX_QUERY_LENGTH,
    GitHubSearch,
    IssueState,
)


@pytest.fixture
def mock_settings():
    """Mock settings with and without GitHub token."""
    with patch("app.shared.services.tools.github_search.settings") as mock:
        mock.GITHUB_TOKEN = None
        mock.REDIS_URL = "redis://localhost:6379/0"
        yield mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("app.shared.services.tools.github_search.create_redis_client") as mock:
        mock.return_value = MagicMock()
        yield mock


class TestGitHubSearchInit:
    """Tests for GitHubSearch initialization."""

    def test_init_without_token(self, mock_settings, mock_redis):
        """Test initialization without authentication token."""
        mock_settings.GITHUB_TOKEN = None
        search = GitHubSearch()
        assert search.api_token is None
        assert search.client is not None

    def test_init_with_token(self, mock_settings, mock_redis):
        """Test initialization with authentication token."""
        mock_settings.GITHUB_TOKEN = "test_token_12345"
        search = GitHubSearch()
        assert search.api_token == "test_token_12345"

    def test_init_creates_http_client(self, mock_settings, mock_redis):
        """Test initialization creates httpx AsyncClient."""
        search = GitHubSearch()
        assert search.client is not None
        # Client should have Accept header
        assert "application/vnd.github+json" in str(search.client.headers)


class TestIssueStateType:
    """Tests for IssueState type alias."""

    def test_issue_state_valid_values(self):
        """Test IssueState accepts valid literal values."""
        # IssueState is a Literal type, so we test by using the values directly
        valid_states: list[IssueState] = ["open", "closed", "all"]
        for state in valid_states:
            assert state in ("open", "closed", "all")


class TestSearchIssues:
    """Tests for search_issues method."""

    @pytest.mark.asyncio
    async def test_search_issues_basic(self, mock_settings, mock_redis):
        """Test basic issue search with mocked response."""
        mock_settings.GITHUB_TOKEN = "test_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total_count": 2,
            "incomplete_results": False,
            "items": [
                {
                    "number": 123,
                    "title": "Test issue 1",
                    "html_url": "https://github.com/org/repo/issues/123",
                    "state": "open",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                    "comments": 5,
                    "body": "Issue body text",
                },
                {
                    "number": 456,
                    "title": "Test issue 2",
                    "html_url": "https://github.com/org/repo/issues/456",
                    "state": "open",
                    "created_at": "2024-01-03T00:00:00Z",
                    "updated_at": "2024-01-04T00:00:00Z",
                    "comments": 10,
                    "body": "Another issue",
                },
            ],
        }

        search = GitHubSearch()
        # Mock the HTTP client
        search.client.get = AsyncMock(return_value=mock_response)
        # Disable cache for this test
        search.cache_enabled = False

        result = await search.search_issues("LangGraph memory")

        assert result["total_count"] == 2
        assert len(result["items"]) == 2
        assert result["items"][0]["number"] == 123

    @pytest.mark.asyncio
    async def test_search_issues_with_state_filter(self, mock_settings, mock_redis):
        """Test issue search with state filter."""
        mock_settings.GITHUB_TOKEN = "test_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_count": 0, "items": []}

        search = GitHubSearch()
        search.client.get = AsyncMock(return_value=mock_response)
        search.cache_enabled = False

        await search.search_issues("test query", state="closed")

        # Verify the call was made
        search.client.get.assert_called_once()
        # Check that the query includes the state filter
        call_args = search.client.get.call_args
        assert "is:closed" in call_args.kwargs.get("params", {}).get("q", "")

    @pytest.mark.asyncio
    async def test_search_issues_with_max_results(self, mock_settings, mock_redis):
        """Test issue search with custom max_results."""
        mock_settings.GITHUB_TOKEN = "test_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_count": 1, "items": []}

        search = GitHubSearch()
        search.client.get = AsyncMock(return_value=mock_response)
        search.cache_enabled = False

        await search.search_issues("bug", max_results=5)

        call_args = search.client.get.call_args
        assert call_args.kwargs.get("params", {}).get("per_page") == 5


class TestGetRepoStats:
    """Tests for get_repo_stats method."""

    @pytest.mark.asyncio
    async def test_get_repo_stats_success(self, mock_settings, mock_redis):
        """Test successful repository stats retrieval."""
        mock_settings.GITHUB_TOKEN = "test_token"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "full_name": "langchain-ai/langgraph",
            "description": "Build stateful agents with LangGraph",
            "stargazers_count": 5000,
            "forks_count": 800,
            "open_issues_count": 150,
            "watchers_count": 100,
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2024-12-01T00:00:00Z",
            "pushed_at": "2024-12-20T00:00:00Z",
            "language": "Python",
        }

        search = GitHubSearch()
        search.client.get = AsyncMock(return_value=mock_response)
        search.cache_enabled = False

        result = await search.get_repo_stats("langchain-ai", "langgraph")

        assert result["full_name"] == "langchain-ai/langgraph"
        assert result["stargazers_count"] == 5000
        assert result["language"] == "Python"

    @pytest.mark.asyncio
    async def test_get_repo_stats_not_found(self, mock_settings, mock_redis):
        """Test repository not found raises error."""
        from app.core.exceptions import GitHubSearchError

        mock_settings.GITHUB_TOKEN = "test_token"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}

        search = GitHubSearch()
        search.client.get = AsyncMock(return_value=mock_response)
        search.cache_enabled = False

        with pytest.raises(GitHubSearchError) as exc_info:
            await search.get_repo_stats("nonexistent", "repo")

        assert "not found" in str(exc_info.value).lower()


class TestQueryValidation:
    """Tests for query validation."""

    def test_query_truncation(self, mock_settings, mock_redis):
        """Test long queries are truncated."""
        mock_settings.GITHUB_TOKEN = "test_token"

        search = GitHubSearch()
        long_query = "a" * (GITHUB_MAX_QUERY_LENGTH + 50)

        validated = search._validate_query(long_query)
        assert len(validated) == GITHUB_MAX_QUERY_LENGTH

    def test_empty_query_raises_error(self, mock_settings, mock_redis):
        """Test empty query raises GitHubSearchError."""
        from app.core.exceptions import GitHubSearchError

        mock_settings.GITHUB_TOKEN = "test_token"

        search = GitHubSearch()

        with pytest.raises(GitHubSearchError):
            search._validate_query("")

    def test_whitespace_query_raises_error(self, mock_settings, mock_redis):
        """Test whitespace-only query raises GitHubSearchError."""
        from app.core.exceptions import GitHubSearchError

        mock_settings.GITHUB_TOKEN = "test_token"

        search = GitHubSearch()

        with pytest.raises(GitHubSearchError):
            search._validate_query("   ")


class TestCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_cache_key_consistency(self, mock_settings, mock_redis):
        """Test cache key is generated consistently."""
        mock_settings.GITHUB_TOKEN = "test_token"

        search = GitHubSearch()

        key1 = search._generate_cache_key("issues", "test query")
        key2 = search._generate_cache_key("issues", "test query")
        assert key1 == key2

    def test_cache_key_different_queries(self, mock_settings, mock_redis):
        """Test different queries produce different keys."""
        mock_settings.GITHUB_TOKEN = "test_token"

        search = GitHubSearch()

        key1 = search._generate_cache_key("issues", "query1")
        key2 = search._generate_cache_key("issues", "query2")
        assert key1 != key2

    def test_cache_key_different_endpoints(self, mock_settings, mock_redis):
        """Test different endpoints produce different keys."""
        mock_settings.GITHUB_TOKEN = "test_token"

        search = GitHubSearch()

        key1 = search._generate_cache_key("issues", "query")
        key2 = search._generate_cache_key("repos", "query")
        assert key1 != key2


class TestCaching:
    """Tests for caching functionality."""

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self, mock_settings, mock_redis):
        """Test cache hit returns cached result without HTTP request."""
        import json

        mock_settings.GITHUB_TOKEN = "test_token"

        cached_data = {"total_count": 5, "items": []}
        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = json.dumps(cached_data)
        mock_redis.return_value = mock_redis_client

        search = GitHubSearch()
        search.client.get = AsyncMock()  # Should not be called

        result = await search.search_issues("cached query")

        assert result == cached_data
        # HTTP client should not have been called due to cache hit
        search.client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_makes_http_request(self, mock_settings, mock_redis):
        """Test cache miss makes HTTP request and caches result."""
        mock_settings.GITHUB_TOKEN = "test_token"

        mock_redis_client = MagicMock()
        mock_redis_client.get.return_value = None  # Cache miss
        mock_redis.return_value = mock_redis_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"total_count": 1, "items": []}

        search = GitHubSearch()
        search.client.get = AsyncMock(return_value=mock_response)

        await search.search_issues("uncached query")

        # HTTP client should have been called
        search.client.get.assert_called_once()
        # Result should have been cached
        mock_redis_client.setex.assert_called_once()


class TestRateLimiting:
    """Tests for rate limit handling."""

    @pytest.mark.asyncio
    async def test_rate_limit_raises_error(self, mock_settings, mock_redis):
        """Test rate limit response raises GitHubSearchError."""
        from app.core.exceptions import GitHubSearchError

        mock_settings.GITHUB_TOKEN = "test_token"

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1704067200",
        }
        mock_response.text = "Rate limit exceeded"

        search = GitHubSearch()
        search.client.get = AsyncMock(return_value=mock_response)
        search.cache_enabled = False

        with pytest.raises(GitHubSearchError) as exc_info:
            await search.search_issues("test")

        assert "rate limit" in str(exc_info.value).lower()


class TestClientLifecycle:
    """Tests for client lifecycle management."""

    @pytest.mark.asyncio
    async def test_close_closes_resources(self, mock_settings, mock_redis):
        """Test close method closes HTTP client and Redis."""
        mock_settings.GITHUB_TOKEN = "test_token"

        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client

        search = GitHubSearch()
        search.client.aclose = AsyncMock()

        await search.close()

        search.client.aclose.assert_called_once()
        mock_redis_client.close.assert_called_once()
