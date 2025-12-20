"""Langfuse-First Architecture: Secure API Client with Circuit Breaker.

Issue #428: This module provides a resilient Langfuse client that serves as
the single interface for all Langfuse API operations. It implements:

1. Circuit Breaker Pattern: Prevents cascade failures when Langfuse is unavailable
2. Retry with Exponential Backoff: Handles transient failures gracefully
3. Secure Proxy: Frontend never sees API keys (all requests proxied through backend)
4. Audit Logging: All operations logged for debugging and compliance
5. Graceful Degradation: Returns safe defaults when Langfuse is down

Security Architecture:
    Frontend (React)          Backend (FastAPI)           Langfuse
         |                          |                        |
         |  HTTP (no API keys)      |                        |
         +------------------------->|                        |
         |                          |  Langfuse SDK          |
         |                          |  (keys in env only)    |
         |                          +----------------------->|
         |                          |<-----------------------+
         |<-------------------------+                        |

Benefits:
- Frontend NEVER sees Langfuse API keys
- All requests go through backend proxy
- Circuit breaker prevents cascade failures
- Audit logging for all operations
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Re-export for backward compatibility
__all__ = [
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitState",
    "LangfuseClient",
    "LangfuseClientError",
    "LangfuseUnavailableError",
    "close_langfuse_client",
    "get_langfuse_api_client",
]


class LangfuseClientError(Exception):
    """Base exception for Langfuse client errors."""


class LangfuseUnavailableError(LangfuseClientError):
    """Raised when Langfuse is unavailable after retries."""


class LangfuseClient:
    """Secure Langfuse API client with circuit breaker and retry logic.

    This client provides:
    1. Secure proxy (API keys never exposed to frontend)
    2. Circuit breaker for resilience
    3. Retry with exponential backoff
    4. Audit logging for all operations
    5. Graceful degradation when Langfuse is unavailable

    Example:
        >>> client = LangfuseClient.from_env()
        >>> prompt = await client.get_prompt("security-auditor")
        >>> await client.create_score(trace_id="xxx", name="relevance", value=0.9)

    """

    def __init__(  # noqa: PLR0913 - Required params for secure API client
        self,
        public_key: str,
        secret_key: str,
        host: str = "http://localhost:3000",
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
        circuit_breaker_config: CircuitBreakerConfig | None = None,
    ) -> None:
        """Initialize Langfuse client.

        Args:
            public_key: Langfuse public API key
            secret_key: Langfuse secret API key
            host: Langfuse server URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts for transient failures
            circuit_breaker_config: Optional circuit breaker configuration

        """
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize circuit breaker
        self._circuit_breaker = CircuitBreaker(
            name="langfuse-api",
            config=circuit_breaker_config or CircuitBreakerConfig(),
        )

        # HTTP client with auth
        self._http_client: httpx.AsyncClient | None = None

        logger.info(
            "langfuse_client_initialized",
            host=self.host,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    @classmethod
    def from_env(cls) -> LangfuseClient | None:
        """Create client from environment variables.

        Required environment variables:
        - LANGFUSE_PUBLIC_KEY
        - LANGFUSE_SECRET_KEY
        - LANGFUSE_HOST (optional, defaults to http://localhost:3000)

        Returns:
            LangfuseClient instance or None if not configured

        """
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"

        if not langfuse_enabled:
            logger.debug("langfuse_disabled", message="LANGFUSE_ENABLED is not true")
            return None

        if not public_key or not secret_key:
            logger.warning(
                "langfuse_credentials_missing",
                public_key_set=bool(public_key),
                secret_key_set=bool(secret_key),
            )
            return None

        return cls(
            public_key=public_key,
            secret_key=secret_key,
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
            timeout=float(os.getenv("LANGFUSE_TIMEOUT", "30")),
            max_retries=int(os.getenv("LANGFUSE_MAX_RETRIES", "3")),
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                auth=(self.public_key, self.secret_key),
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Content-Type": "application/json",
                    "X-Langfuse-SDK-Name": "skillforge-langfuse-client",
                    "X-Langfuse-SDK-Version": "1.0.0",
                },
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client connections."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    @property
    def circuit_state(self) -> CircuitState:
        """Current circuit breaker state."""
        return self._circuit_breaker.state

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry and circuit breaker.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json: Request body as JSON
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            LangfuseUnavailableError: If all retries fail
            CircuitBreakerOpenError: If circuit breaker is open

        """

        @retry(
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
            reraise=True,
        )
        async def _make_request() -> dict[str, Any]:
            client = await self._get_http_client()
            url = f"{self.host}{endpoint}"

            start_time = time.monotonic()

            response = await client.request(
                method=method,
                url=url,
                json=json,
                params=params,
            )

            elapsed_ms = (time.monotonic() - start_time) * 1000

            logger.debug(
                "langfuse_api_request",
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                elapsed_ms=round(elapsed_ms, 2),
            )

            response.raise_for_status()
            return response.json() if response.content else {}

        try:
            return await self._circuit_breaker.call(_make_request)
        except CircuitBreakerOpenError:
            logger.warning(
                "langfuse_circuit_open",
                endpoint=endpoint,
                message="Circuit breaker is open, failing fast",
            )
            raise
        except RetryError as e:
            logger.exception(
                "langfuse_request_failed",
                method=method,
                endpoint=endpoint,
                retries=self.max_retries,
            )
            msg = f"Langfuse unavailable after {self.max_retries} retries"
            raise LangfuseUnavailableError(msg) from e
        except httpx.HTTPStatusError as e:
            logger.exception(
                "langfuse_http_error",
                method=method,
                endpoint=endpoint,
                status_code=e.response.status_code,
            )
            msg = f"Langfuse API error: {e.response.status_code}"
            raise LangfuseClientError(msg) from e

    # =========================================================================
    # Prompt Management API
    # =========================================================================

    async def get_prompt(
        self,
        name: str,
        *,
        version: int | None = None,
        label: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch a prompt from Langfuse.

        Args:
            name: Prompt name
            version: Specific version number (optional)
            label: Label like "production" or "staging" (optional)

        Returns:
            Prompt data or None if not found

        """
        params: dict[str, Any] = {"name": name}
        if version is not None:
            params["version"] = version
        if label:
            params["label"] = label

        try:
            result = await self._request("GET", "/api/public/v2/prompts", params=params)

            logger.info(
                "langfuse_prompt_fetched",
                prompt_name=name,
                version=version,
                label=label,
            )

            return result
        except LangfuseClientError:
            logger.warning(
                "langfuse_prompt_not_found",
                prompt_name=name,
                version=version,
                label=label,
            )
            return None

    async def list_prompts(
        self,
        *,
        limit: int = 50,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """List all prompts in Langfuse.

        Args:
            limit: Maximum prompts per page
            page: Page number

        Returns:
            List of prompt metadata

        """
        try:
            result = await self._request(
                "GET",
                "/api/public/v2/prompts",
                params={"limit": limit, "page": page},
            )
            return result.get("data", [])
        except LangfuseClientError:
            return []

    # =========================================================================
    # Annotation Queue API
    # =========================================================================

    async def add_to_annotation_queue(
        self,
        queue_id: str,
        trace_id: str,
        *,
        object_type: str = "TRACE",
    ) -> bool:
        """Add an item to a Langfuse annotation queue.

        Args:
            queue_id: Annotation queue ID
            trace_id: Trace or observation ID to add
            object_type: Type of object (TRACE, OBSERVATION, SESSION)

        Returns:
            True if successfully added

        """
        try:
            await self._request(
                "POST",
                f"/api/public/annotation-queues/{queue_id}/items",
                json={
                    "objectId": trace_id,
                    "objectType": object_type,
                },
            )

            logger.info(
                "langfuse_queue_item_added",
                queue_id=queue_id,
                trace_id=trace_id,
                object_type=object_type,
            )

            return True
        except LangfuseClientError:
            return False

    async def get_annotation_queue(
        self,
        queue_id: str,
        *,
        limit: int = 50,
        page: int = 1,
    ) -> dict[str, Any]:
        """Get annotation queue items.

        Args:
            queue_id: Annotation queue ID
            limit: Maximum items per page
            page: Page number

        Returns:
            Queue data with items

        """
        try:
            return await self._request(
                "GET",
                f"/api/public/annotation-queues/{queue_id}/items",
                params={"limit": limit, "page": page},
            )
        except LangfuseClientError:
            return {"items": [], "total": 0}

    # =========================================================================
    # Score API
    # =========================================================================

    async def create_score(  # noqa: PLR0913 - Langfuse API requires these params
        self,
        *,
        trace_id: str,
        name: str,
        value: float,
        observation_id: str | None = None,
        comment: str | None = None,
        data_type: str = "NUMERIC",
    ) -> bool:
        """Create a score in Langfuse.

        Args:
            trace_id: Trace ID to attach score to
            name: Score name (e.g., "relevance", "depth")
            value: Numeric score value
            observation_id: Optional observation ID
            comment: Optional comment
            data_type: Score data type (NUMERIC, CATEGORICAL, BOOLEAN)

        Returns:
            True if score created successfully

        """
        payload: dict[str, Any] = {
            "traceId": trace_id,
            "name": name,
            "value": value,
            "dataType": data_type,
        }

        if observation_id:
            payload["observationId"] = observation_id
        if comment:
            payload["comment"] = comment

        try:
            await self._request("POST", "/api/public/scores", json=payload)

            logger.debug(
                "langfuse_score_created",
                trace_id=trace_id,
                name=name,
                value=value,
            )

            return True
        except LangfuseClientError:
            return False

    # =========================================================================
    # Dataset API
    # =========================================================================

    async def get_dataset(self, dataset_name: str) -> dict[str, Any] | None:
        """Fetch a dataset from Langfuse.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dataset data or None if not found

        """
        try:
            result = await self._request(
                "GET",
                f"/api/public/v2/datasets/{dataset_name}",
            )
            return result
        except LangfuseClientError:
            return None

    async def get_dataset_items(
        self,
        dataset_name: str,
        *,
        limit: int = 50,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Get items from a dataset.

        Args:
            dataset_name: Name of the dataset
            limit: Maximum items per page
            page: Page number

        Returns:
            List of dataset items

        """
        try:
            result = await self._request(
                "GET",
                f"/api/public/v2/datasets/{dataset_name}/items",
                params={"limit": limit, "page": page},
            )
            return result.get("data", [])
        except LangfuseClientError:
            return []

    # =========================================================================
    # Experiments: Use Langfuse SDK directly (not REST API)
    # =========================================================================
    #
    # IMPORTANT: Langfuse does NOT have REST API endpoints for experiments.
    # The /api/public/v2/experiments endpoints were fabricated and never worked.
    #
    # For running experiments on datasets, use the Langfuse Python SDK directly:
    #
    #   from langfuse import Langfuse
    #
    #   langfuse = Langfuse()
    #   dataset = langfuse.get_dataset("my-dataset")
    #
    #   for item in dataset.items:
    #       with item.run(run_name="my-experiment") as observation:
    #           # Your evaluation logic here
    #           result = evaluate(item.input)
    #           observation.score(name="accuracy", value=0.9)
    #
    # See: scripts/run_langfuse_experiment_v2.py for a working example
    # Docs: https://langfuse.com/docs/datasets/python-decorator


# Module-level singleton
_langfuse_client: LangfuseClient | None = None


def get_langfuse_api_client() -> LangfuseClient | None:
    """Get or create Langfuse API client singleton.

    Returns:
        LangfuseClient instance or None if not configured

    """
    global _langfuse_client  # noqa: PLW0603

    if _langfuse_client is None:
        _langfuse_client = LangfuseClient.from_env()

    return _langfuse_client


async def close_langfuse_client() -> None:
    """Close the singleton Langfuse client."""
    global _langfuse_client  # noqa: PLW0603

    if _langfuse_client is not None:
        await _langfuse_client.close()
        _langfuse_client = None
