"""GitHub Search API service for repository and community insights.

This module provides a production-ready wrapper for GitHub's Search API,
used by Tier 3 research agents (community_pulse) for analyzing repository
activity, issues, discussions, and community sentiment.

Features:
- Async HTTP requests with httpx
- Redis caching with 30-minute TTL (GitHub data updates frequently)
- Exponential backoff retry with tenacity
- Comprehensive error handling and logging
- Query validation and rate limit awareness
- Support for both authenticated (higher limits) and unauthenticated access

GitHub API Documentation: https://docs.github.com/en/rest/search
Rate Limits:
- Unauthenticated: 10 requests/minute
- Authenticated: 30 requests/minute

Example:
    >>> from app.shared.services.tools.github_search import GitHubSearch
    >>> github = GitHubSearch()
    >>> issues = await github.search_issues("repo:facebook/react is:open")
    >>> discussions = await github.search_discussions("langchain")
    >>> stars = await github.get_repo_stats("langchain-ai/langgraph")

"""

import hashlib
import os
from typing import Any, Literal

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.constants import (
    HTTP_ERROR_THRESHOLD,
    HTTP_NOT_FOUND,
    HTTP_RATE_LIMITED,
    HTTP_SERVER_ERROR_THRESHOLD,
    MAX_ERROR_MESSAGE_LENGTH_LONG,
    MAX_RETRY_ATTEMPTS,
)
from app.core.exceptions import (
    ExternalServiceError,
    ExtractionErrorCode,
    GitHubSearchError,
)
from app.core.tracing import traced_tool, update_current_observation
from app.shared.services.cache.redis_connection import create_redis_client

logger = structlog.get_logger(__name__)

# GitHub API constants
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_SEARCH_ISSUES_URL = f"{GITHUB_API_BASE_URL}/search/issues"
GITHUB_REPOS_URL = f"{GITHUB_API_BASE_URL}/repos"
GITHUB_DEFAULT_MAX_RESULTS = 10
GITHUB_MAX_QUERY_LENGTH = 256
GITHUB_TIMEOUT = 10.0  # GitHub API is typically fast
GITHUB_CACHE_TTL = 1800  # Cache for 30 minutes (GitHub data updates frequently)

# Retry configuration for GitHub API
RETRY_MIN_WAIT_GITHUB = 1.0  # Minimum wait between retries (seconds)
RETRY_MAX_WAIT_GITHUB = 10.0  # Maximum wait between retries (seconds)
RETRY_MIN_WAIT_GITHUB_TEST = 0.2  # Faster retries in tests
RETRY_MAX_WAIT_GITHUB_TEST = 2.0  # Shorter max wait in tests
RETRY_MULTIPLIER_GITHUB = 2  # Exponential backoff multiplier

# Type alias for issue state
IssueState = Literal["open", "closed", "all"]


class GitHubSearch:
    """GitHub Search API client for repository and community analysis.

    Provides async GitHub search with caching, retries, and error handling.
    Used by Tier 3 research agents for community sentiment analysis.
    """

    def __init__(self) -> None:
        """Initialize GitHub Search client with optional API token and HTTP client."""
        # GitHub token is optional - provides higher rate limits if available
        self.api_token = settings.GITHUB_TOKEN if hasattr(settings, "GITHUB_TOKEN") else None
        if not self.api_token:
            logger.info(
                "github_token_not_configured",
                message=(
                    "GITHUB_TOKEN not set. Using unauthenticated access with lower rate limits "
                    "(10 req/min vs 30 req/min authenticated)."
                ),
            )

        # Build headers with authentication if token available
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        self.client = httpx.AsyncClient(timeout=GITHUB_TIMEOUT, headers=headers)

        # Initialize Redis cache client
        try:
            self.redis_client = create_redis_client()
            self.cache_enabled = True
            logger.info(
                "github_cache_initialized",
                cache_ttl=GITHUB_CACHE_TTL,
                redis_url=settings.REDIS_URL.split("@")[-1],  # Hide credentials
            )
        except (ConnectionError, TimeoutError, ValueError) as e:
            self.redis_client = None
            self.cache_enabled = False
            logger.warning(
                "github_cache_initialization_failed",
                error=str(e),
                message="Proceeding without cache (Redis unavailable)",
            )

    def _generate_cache_key(self, endpoint: str, query: str) -> str:
        """Generate cache key for GitHub query.

        Args:
            endpoint: API endpoint (issues, repos, etc.)
            query: Search query or repo identifier

        Returns:
            Cache key as hex digest

        """
        cache_input = f"github:{endpoint}:{query}"
        return f"github:search:{hashlib.sha256(cache_input.encode()).hexdigest()}"

    async def _get_cached_result(self, cache_key: str) -> dict[str, Any] | None:
        """Retrieve cached search result from Redis.

        Args:
            cache_key: Cache key

        Returns:
            Cached search result or None if not found

        """
        if not self.cache_enabled or not self.redis_client:
            return None

        try:
            import json

            cached = self.redis_client.get(cache_key)
            if cached:
                logger.info(
                    "github_cache_hit",
                    cache_key=cache_key[:16] + "...",
                )
                return json.loads(cached)  # type: ignore[no-any-return]
        except (ConnectionError, TimeoutError, ValueError, TypeError) as e:
            logger.warning(
                "github_cache_get_failed",
                cache_key=cache_key[:16] + "...",
                error=str(e),
            )

        return None

    async def _set_cached_result(self, cache_key: str, result: dict[str, Any]) -> None:
        """Store search result in Redis cache.

        Args:
            cache_key: Cache key
            result: Search result to cache

        """
        if not self.cache_enabled or not self.redis_client:
            return

        try:
            import json

            self.redis_client.setex(
                cache_key,
                GITHUB_CACHE_TTL,
                json.dumps(result),
            )
            logger.debug(
                "github_cache_set",
                cache_key=cache_key[:16] + "...",
                ttl=GITHUB_CACHE_TTL,
            )
        except (ConnectionError, TimeoutError, ValueError, TypeError) as e:
            logger.warning(
                "github_cache_set_failed",
                cache_key=cache_key[:16] + "...",
                error=str(e),
            )

    def _validate_query(self, query: str) -> str:
        """Validate and sanitize search query.

        Args:
            query: Raw search query

        Returns:
            Sanitized query

        Raises:
            GitHubSearchError: If query is invalid

        """
        # Strip whitespace
        query = query.strip()

        # Check if query is empty
        if not query:
            msg = "Search query cannot be empty"
            raise GitHubSearchError(msg, error_code=ExtractionErrorCode.UNKNOWN)

        # Check query length
        if len(query) > GITHUB_MAX_QUERY_LENGTH:
            logger.warning(
                "github_query_truncated",
                original_length=len(query),
                max_length=GITHUB_MAX_QUERY_LENGTH,
            )
            query = query[:GITHUB_MAX_QUERY_LENGTH]

        return query

    @traced_tool("github_search_issues", tags=["external_api", "search", "tier3"])
    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER_GITHUB,
            min=(
                RETRY_MIN_WAIT_GITHUB_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MIN_WAIT_GITHUB
            ),
            max=(
                RETRY_MAX_WAIT_GITHUB_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MAX_WAIT_GITHUB
            ),
        ),
        reraise=True,
    )
    async def search_issues(
        self,
        query: str,
        *,
        state: IssueState = "open",
        max_results: int = GITHUB_DEFAULT_MAX_RESULTS,
        sort: str = "created",
        order: str = "desc",
    ) -> dict[str, Any]:
        """Search GitHub issues and pull requests.

        Args:
            query: Search query (supports GitHub search syntax)
            state: Issue state filter - "open", "closed", or "all"
            max_results: Maximum number of results to return
            sort: Sort field - "created", "updated", "comments"
            order: Sort order - "asc" or "desc"

        Returns:
            Dictionary with search results:
            {
                "total_count": int,
                "incomplete_results": bool,
                "items": [
                    {
                        "id": int,
                        "number": int,
                        "title": str,
                        "state": str,
                        "created_at": str,
                        "updated_at": str,
                        "comments": int,
                        "html_url": str,
                        "body": str,
                        ...
                    },
                    ...
                ],
            }

        Raises:
            GitHubSearchError: If search fails or API returns an error

        """
        # Validate query
        validated_query = self._validate_query(query)

        # Add state filter to query if not already present
        if f"is:{state}" not in validated_query and state != "all":
            validated_query = f"{validated_query} is:{state}"

        # Generate cache key
        cache_key = self._generate_cache_key(f"issues:{state}:{sort}:{order}", validated_query)

        # Check cache
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            update_current_observation(
                metadata={
                    "cache_hit": True,
                    "query": validated_query[:100],
                    "state": state,
                }
            )
            return cached_result

        # Build request params
        params = {
            "q": validated_query,
            "per_page": min(max_results, 100),  # GitHub max is 100
            "sort": sort,
            "order": order,
        }

        try:
            logger.info(
                "github_search_issues_request",
                query=validated_query[:100],
                state=state,
                max_results=max_results,
            )

            # Make request to GitHub API
            response = await self.client.get(
                GITHUB_SEARCH_ISSUES_URL,
                params=params,
            )

            # Handle rate limiting
            if response.status_code == HTTP_RATE_LIMITED:
                error_msg = f"GitHub API rate limit exceeded for query: {validated_query}"
                logger.error(
                    "github_rate_limited",
                    query=validated_query[:100],
                    status_code=HTTP_RATE_LIMITED,
                    remaining=response.headers.get("X-RateLimit-Remaining"),
                    reset=response.headers.get("X-RateLimit-Reset"),
                )
                raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.NETWORK_ERROR)

            # Handle server errors
            if response.status_code >= HTTP_SERVER_ERROR_THRESHOLD:
                response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
                error_msg = (
                    f"GitHub API server error (HTTP {response.status_code}): {response_preview}"
                )
                logger.error(
                    "github_server_error",
                    query=validated_query[:100],
                    status_code=response.status_code,
                    response_preview=response_preview,
                )
                raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.HTTP_5XX)

            # Handle other HTTP errors
            if response.status_code >= HTTP_ERROR_THRESHOLD:
                response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
                error_msg = f"GitHub API error (HTTP {response.status_code}): {response_preview}"
                logger.error(
                    "github_http_error",
                    query=validated_query[:100],
                    status_code=response.status_code,
                    response_preview=response_preview,
                )
                raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.HTTP_5XX)

            # Parse response
            result = response.json()

            logger.info(
                "github_search_issues_success",
                query=validated_query[:100],
                total_count=result.get("total_count", 0),
                returned_items=len(result.get("items", [])),
            )

            # Update Langfuse observation
            update_current_observation(
                metadata={
                    "cache_hit": False,
                    "query": validated_query[:100],
                    "state": state,
                    "total_count": result.get("total_count", 0),
                    "returned_items": len(result.get("items", [])),
                }
            )

            # Cache result
            await self._set_cached_result(cache_key, result)

            return result

        except httpx.TimeoutException as e:
            error_msg = f"GitHub API request timed out after {GITHUB_TIMEOUT}s: {validated_query}"
            logger.exception(
                "github_timeout",
                query=validated_query[:100],
                timeout=GITHUB_TIMEOUT,
                error=str(e),
            )
            raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.TIMEOUT) from e

        except GitHubSearchError:
            # Re-raise GitHubSearchError without modification
            raise

        except Exception as e:
            error_msg = (
                f"GitHub search failed for query '{validated_query}': {type(e).__name__}: {e!s}"
            )
            logger.exception(
                "github_search_failed",
                query=validated_query[:100],
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ExternalServiceError(
                service_name="github",
                message=f"GitHub API call failed: {e}",
            ) from e

    @traced_tool("github_get_repo_stats", tags=["external_api", "github", "tier3"])
    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER_GITHUB,
            min=(
                RETRY_MIN_WAIT_GITHUB_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MIN_WAIT_GITHUB
            ),
            max=(
                RETRY_MAX_WAIT_GITHUB_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MAX_WAIT_GITHUB
            ),
        ),
        reraise=True,
    )
    async def get_repo_stats(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository statistics (stars, forks, issues, etc.).

        Args:
            owner: Repository owner (username or organization)
            repo: Repository name

        Returns:
            Dictionary with repository statistics:
            {
                "id": int,
                "name": str,
                "full_name": str,
                "stargazers_count": int,
                "forks_count": int,
                "open_issues_count": int,
                "watchers_count": int,
                "created_at": str,
                "updated_at": str,
                "pushed_at": str,
                "language": str,
                "html_url": str,
                ...
            }

        Raises:
            GitHubSearchError: If request fails or API returns an error

        """
        repo_identifier = f"{owner}/{repo}"

        # Generate cache key
        cache_key = self._generate_cache_key("repos", repo_identifier)

        # Check cache
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            update_current_observation(
                metadata={
                    "cache_hit": True,
                    "repo": repo_identifier,
                }
            )
            return cached_result

        try:
            logger.info(
                "github_get_repo_stats_request",
                repo=repo_identifier,
            )

            # Make request to GitHub API
            response = await self.client.get(f"{GITHUB_REPOS_URL}/{owner}/{repo}")

            # Handle rate limiting
            if response.status_code == HTTP_RATE_LIMITED:
                error_msg = f"GitHub API rate limit exceeded for repo: {repo_identifier}"
                logger.error(
                    "github_rate_limited",
                    repo=repo_identifier,
                    status_code=HTTP_RATE_LIMITED,
                    remaining=response.headers.get("X-RateLimit-Remaining"),
                    reset=response.headers.get("X-RateLimit-Reset"),
                )
                raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.NETWORK_ERROR)

            # Handle not found
            if response.status_code == HTTP_NOT_FOUND:
                error_msg = f"GitHub repository not found: {repo_identifier}"
                logger.warning(
                    "github_repo_not_found",
                    repo=repo_identifier,
                    status_code=404,
                )
                raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.UNKNOWN)

            # Handle other errors
            if response.status_code >= HTTP_ERROR_THRESHOLD:
                response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
                error_msg = f"GitHub API error (HTTP {response.status_code}): {response_preview}"
                logger.error(
                    "github_http_error",
                    repo=repo_identifier,
                    status_code=response.status_code,
                    response_preview=response_preview,
                )
                raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.HTTP_5XX)

            # Parse response
            result = response.json()

            logger.info(
                "github_get_repo_stats_success",
                repo=repo_identifier,
                stars=result.get("stargazers_count", 0),
                forks=result.get("forks_count", 0),
                open_issues=result.get("open_issues_count", 0),
            )

            # Update Langfuse observation
            update_current_observation(
                metadata={
                    "cache_hit": False,
                    "repo": repo_identifier,
                    "stars": result.get("stargazers_count", 0),
                    "forks": result.get("forks_count", 0),
                    "open_issues": result.get("open_issues_count", 0),
                }
            )

            # Cache result
            await self._set_cached_result(cache_key, result)

            return result

        except httpx.TimeoutException as e:
            error_msg = f"GitHub API request timed out after {GITHUB_TIMEOUT}s: {repo_identifier}"
            logger.exception(
                "github_timeout",
                repo=repo_identifier,
                timeout=GITHUB_TIMEOUT,
                error=str(e),
            )
            raise GitHubSearchError(error_msg, error_code=ExtractionErrorCode.TIMEOUT) from e

        except GitHubSearchError:
            # Re-raise GitHubSearchError without modification
            raise

        except Exception as e:
            error_msg = (
                f"GitHub repo stats failed for '{repo_identifier}': {type(e).__name__}: {e!s}"
            )
            logger.exception(
                "github_repo_stats_failed",
                repo=repo_identifier,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ExternalServiceError(
                service_name="github",
                message=f"GitHub API call failed: {e}",
            ) from e

    async def close(self) -> None:
        """Close HTTP client and Redis connection."""
        await self.client.aclose()

        if self.redis_client:
            self.redis_client.close()

        logger.debug("github_client_closed")
