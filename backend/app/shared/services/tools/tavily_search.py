"""Tavily Search API service for web search capabilities.

This module provides a production-ready wrapper for the Tavily Search API,
used by Tier 2 validation agents (fact_validator, alternatives_finder) for
web search capabilities.

Features:
- Async HTTP requests with httpx
- Redis caching with 1-hour TTL (stable search results)
- Exponential backoff retry with tenacity
- Comprehensive error handling and logging
- Query validation and sanitization
- Rate limit awareness

Tavily API Documentation: https://docs.tavily.com/
Pricing: $0.01 per search request

Example:
    >>> from app.shared.services.tools.tavily_search import TavilySearch
    >>> tavily = TavilySearch()
    >>> results = await tavily.search("LangGraph workflow patterns")
    >>> print(results["answer"])  # AI-generated answer
    >>> for result in results["results"]:
    ...     print(result["title"], result["url"])

"""

import hashlib
import os
from typing import Literal

import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.constants import (
    HTTP_ERROR_THRESHOLD,
    HTTP_RATE_LIMITED,
    HTTP_SERVER_ERROR_THRESHOLD,
    MAX_ERROR_MESSAGE_LENGTH_LONG,
    MAX_RETRY_ATTEMPTS,
    RETRY_MAX_WAIT_TAVILY,
    RETRY_MAX_WAIT_TAVILY_TEST,
    RETRY_MIN_WAIT_TAVILY,
    RETRY_MIN_WAIT_TAVILY_TEST,
    RETRY_MULTIPLIER_TAVILY,
    TAVILY_API_URL,
    TAVILY_CACHE_TTL,
    TAVILY_DEFAULT_MAX_RESULTS,
    TAVILY_MAX_QUERY_LENGTH,
    TAVILY_SEARCH_DEPTH_ADVANCED,
    TAVILY_SEARCH_DEPTH_BASIC,
    TAVILY_TIMEOUT,
)
from app.core.exceptions import ExtractionErrorCode, TavilySearchError
from app.core.types import TavilySearchResult
from app.shared.services.cache.redis_connection import create_redis_client

logger = structlog.get_logger(__name__)

# Type alias for search depth
SearchDepth = Literal["basic", "advanced"]


class TavilySearch:
    """Tavily Search API client for web search capabilities.

    Provides async web search with caching, retries, and error handling.
    Used by Tier 2 validation agents for fact checking and finding alternatives.
    """

    def __init__(self) -> None:
        """Initialize Tavily Search client with API key and HTTP client."""
        self.api_key = settings.TAVILY_API_KEY
        if not self.api_key:
            logger.warning(
                "tavily_api_key_missing",
                message=(
                    "TAVILY_API_KEY not configured. Tavily Search will fail. "
                    "Set TAVILY_API_KEY in environment or .env file."
                ),
            )

        self.client = httpx.AsyncClient(timeout=TAVILY_TIMEOUT)

        # Initialize Redis cache client
        try:
            self.redis_client = create_redis_client()
            self.cache_enabled = True
            logger.info(
                "tavily_cache_initialized",
                cache_ttl=TAVILY_CACHE_TTL,
                redis_url=settings.REDIS_URL.split("@")[-1],  # Hide credentials
            )
        except (ConnectionError, TimeoutError, ValueError) as e:
            self.redis_client = None
            self.cache_enabled = False
            logger.warning(
                "tavily_cache_initialization_failed",
                error=str(e),
                message="Proceeding without cache (Redis unavailable)",
            )

    def _generate_cache_key(self, query: str, search_depth: SearchDepth) -> str:
        """Generate cache key for search query.

        Args:
            query: Search query
            search_depth: Search depth (basic or advanced)

        Returns:
            Cache key as hex digest

        """
        # Include search depth in cache key to differentiate basic vs advanced
        cache_input = f"tavily:{search_depth}:{query}"
        return f"tavily:search:{hashlib.sha256(cache_input.encode()).hexdigest()}"

    async def _get_cached_result(self, cache_key: str) -> TavilySearchResult | None:
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
                    "tavily_cache_hit",
                    cache_key=cache_key[:16] + "...",
                )
                return json.loads(cached)  # type: ignore[no-any-return]
        except (ConnectionError, TimeoutError, ValueError, TypeError) as e:
            logger.warning(
                "tavily_cache_get_failed",
                cache_key=cache_key[:16] + "...",
                error=str(e),
            )

        return None

    async def _set_cached_result(self, cache_key: str, result: TavilySearchResult) -> None:
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
                TAVILY_CACHE_TTL,
                json.dumps(result),
            )
            logger.debug(
                "tavily_cache_set",
                cache_key=cache_key[:16] + "...",
                ttl=TAVILY_CACHE_TTL,
            )
        except (ConnectionError, TimeoutError, ValueError, TypeError) as e:
            logger.warning(
                "tavily_cache_set_failed",
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
            TavilySearchError: If query is invalid

        """
        # Strip whitespace
        query = query.strip()

        # Check if query is empty
        if not query:
            msg = "Search query cannot be empty"
            raise TavilySearchError(msg, error_code=ExtractionErrorCode.UNKNOWN)

        # Check query length
        if len(query) > TAVILY_MAX_QUERY_LENGTH:
            logger.warning(
                "tavily_query_truncated",
                original_length=len(query),
                max_length=TAVILY_MAX_QUERY_LENGTH,
            )
            query = query[:TAVILY_MAX_QUERY_LENGTH]

        return query

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER_TAVILY,
            min=(
                RETRY_MIN_WAIT_TAVILY_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MIN_WAIT_TAVILY
            ),
            max=(
                RETRY_MAX_WAIT_TAVILY_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MAX_WAIT_TAVILY
            ),
        ),
        reraise=True,
    )
    async def search(  # noqa: PLR0913 - Search API requires multiple parameters
        self,
        query: str,
        *,
        search_depth: SearchDepth = "advanced",
        max_results: int = TAVILY_DEFAULT_MAX_RESULTS,
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_images: bool = False,
    ) -> TavilySearchResult:
        """Execute web search using Tavily API.

        Args:
            query: Search query
            search_depth: Search depth - "basic" (faster) or "advanced" (comprehensive)
            max_results: Maximum number of results to return
            include_answer: Include AI-generated answer summary
            include_raw_content: Include raw HTML content from sources
            include_images: Include image results

        Returns:
            Dictionary with search results:
            {
                "query": str,
                "answer": str,  # AI-generated answer (if include_answer=True)
                "results": [
                    {
                        "title": str,
                        "url": str,
                        "content": str,
                        "score": float,
                    },
                    ...
                ],
                "response_time": float,
            }

        Raises:
            TavilySearchError: If search fails or API returns an error

        """
        # Validate query
        validated_query = self._validate_query(query)

        # Generate cache key
        cache_key = self._generate_cache_key(validated_query, search_depth)

        # Check cache
        cached_result = await self._get_cached_result(cache_key)
        if cached_result:
            return cached_result

        # Validate API key
        if not self.api_key:
            msg = "TAVILY_API_KEY not configured. Set it in environment or .env file."
            raise TavilySearchError(msg, error_code=ExtractionErrorCode.UNKNOWN)

        # Build request payload
        payload = {
            "api_key": self.api_key,
            "query": validated_query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
        }

        try:
            logger.info(
                "tavily_search_request",
                query=validated_query[:100],  # Truncate for logging
                search_depth=search_depth,
                max_results=max_results,
            )

            # Make request to Tavily API
            response = await self.client.post(
                TAVILY_API_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            # Handle rate limiting
            if response.status_code == HTTP_RATE_LIMITED:
                error_msg = f"Tavily API rate limit exceeded for query: {validated_query}"
                logger.error(
                    "tavily_rate_limited",
                    query=validated_query[:100],
                    status_code=HTTP_RATE_LIMITED,
                )
                raise TavilySearchError(error_msg, error_code=ExtractionErrorCode.NETWORK_ERROR)

            # Handle server errors
            if response.status_code >= HTTP_SERVER_ERROR_THRESHOLD:
                response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
                error_msg = (
                    f"Tavily API server error (HTTP {response.status_code}): {response_preview}"
                )
                logger.error(
                    "tavily_server_error",
                    query=validated_query[:100],
                    status_code=response.status_code,
                    response_preview=response_preview,
                )
                raise TavilySearchError(error_msg, error_code=ExtractionErrorCode.HTTP_5XX)

            # Handle other HTTP errors
            if response.status_code >= HTTP_ERROR_THRESHOLD:
                response_preview = response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]
                error_msg = f"Tavily API error (HTTP {response.status_code}): {response_preview}"
                logger.error(
                    "tavily_http_error",
                    query=validated_query[:100],
                    status_code=response.status_code,
                    response_preview=response_preview,
                )
                raise TavilySearchError(error_msg, error_code=ExtractionErrorCode.HTTP_5XX)

            # Parse response
            result_data = response.json()

            # Build normalized result
            result: TavilySearchResult = {
                "query": validated_query,
                "answer": result_data.get("answer", ""),
                "results": result_data.get("results", []),
                "response_time": result_data.get("response_time", 0.0),
            }

            logger.info(
                "tavily_search_success",
                query=validated_query[:100],
                num_results=len(result.get("results", [])),  # type: ignore[arg-type]
                has_answer=bool(result.get("answer")),
                response_time=result.get("response_time"),
            )

            # Cache result
            await self._set_cached_result(cache_key, result)

            return result

        except httpx.TimeoutException as e:
            error_msg = f"Tavily API request timed out after {TAVILY_TIMEOUT}s: {validated_query}"
            logger.exception(
                "tavily_timeout",
                query=validated_query[:100],
                timeout=TAVILY_TIMEOUT,
                error=str(e),
            )
            raise TavilySearchError(error_msg, error_code=ExtractionErrorCode.TIMEOUT) from e

        except TavilySearchError:
            # Re-raise TavilySearchError without modification
            raise

        except Exception as e:
            error_msg = (
                f"Tavily search failed for query '{validated_query}': {type(e).__name__}: {e!s}"
            )
            logger.exception(
                "tavily_search_failed",
                query=validated_query[:100],
                error=str(e),
                error_type=type(e).__name__,
            )
            raise TavilySearchError(error_msg, error_code=ExtractionErrorCode.UNKNOWN) from e

    async def search_basic(self, query: str, **kwargs) -> TavilySearchResult:
        """Execute basic web search (faster, less comprehensive).

        Args:
            query: Search query
            **kwargs: Additional search parameters

        Returns:
            Search results dictionary

        """
        return await self.search(query, search_depth=TAVILY_SEARCH_DEPTH_BASIC, **kwargs)

    async def search_advanced(self, query: str, **kwargs) -> TavilySearchResult:
        """Execute advanced web search (slower, more comprehensive).

        Args:
            query: Search query
            **kwargs: Additional search parameters

        Returns:
            Search results dictionary

        """
        return await self.search(query, search_depth=TAVILY_SEARCH_DEPTH_ADVANCED, **kwargs)

    async def close(self) -> None:
        """Close HTTP client and Redis connection."""
        await self.client.aclose()

        if self.redis_client:
            self.redis_client.close()

        logger.debug("tavily_client_closed")
