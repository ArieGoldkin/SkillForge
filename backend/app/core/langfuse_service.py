"""Unified Langfuse Service - Single Source of Truth for Langfuse Integration.

This module provides a comprehensive Langfuse service that combines:
1. Langfuse Python SDK for core observability (tracing, scoring, prompts)
2. Additional API methods for annotation queues and datasets
3. Graceful degradation when Langfuse is unavailable
4. Singleton pattern for application-wide access

Benefits over separate config/client modules:
- Single import for all Langfuse operations
- Consistent error handling and logging
- SDK-first approach (better type safety, auto-batching)
- Backward compatible with existing code

Architecture:
    Application Code
         |
         v
    LangfuseService (singleton)
         |
         +-- SDK Methods (traces, scores, prompts)
         |   - Uses langfuse.Langfuse client
         |   - Auto-batching, type-safe
         |
         +-- API Methods (annotation queues, datasets)
             - Uses httpx for REST calls
             - Retry with exponential backoff

Usage:
    >>> from app.core.langfuse_service import get_langfuse_service
    >>> service = get_langfuse_service()
    >>> if service:
    ...     # Submit scores
    ...     service.submit_score(name="relevance", value=0.9)
    ...     # Get prompts
    ...     prompt = await service.get_prompt("security-auditor")
    ...     # Add to annotation queue
    ...     await service.add_to_annotation_queue("queue-123", "trace-456")

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

from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class LangfuseServiceError(Exception):
    """Base exception for Langfuse service errors."""


class LangfuseUnavailableError(LangfuseServiceError):
    """Raised when Langfuse is unavailable after retries."""


# ============================================================================
# Unified Langfuse Service
# ============================================================================


class LangfuseService:
    """Unified service for all Langfuse operations.

    This service provides a single interface for:
    - SDK-based operations (traces, scores, prompts via Python SDK)
    - REST API operations (annotation queues, datasets via HTTP)
    - LangChain callback handler integration
    - Graceful degradation when Langfuse is unavailable

    The service uses the Langfuse Python SDK as the primary interface,
    falling back to REST API only for features not available in the SDK.

    Example:
        >>> service = LangfuseService.from_env()
        >>> # SDK-based scoring
        >>> service.submit_score(name="relevance", value=0.9)
        >>> # REST API for annotation queues
        >>> await service.add_to_annotation_queue("queue-id", "trace-id")

    """

    def __init__(  # noqa: PLR0913 - Required params for Langfuse configuration
        self,
        public_key: str,
        secret_key: str,
        host: str = "http://localhost:3000",
        *,
        release: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize Langfuse service.

        Args:
            public_key: Langfuse public API key
            secret_key: Langfuse secret API key
            host: Langfuse server URL
            release: Application release version for tracing
            timeout: Request timeout in seconds (for REST API calls)
            max_retries: Maximum retry attempts for REST API calls

        """
        self.public_key = public_key
        self.secret_key = secret_key
        self.host = host.rstrip("/")
        self.release = release
        self.timeout = timeout
        self.max_retries = max_retries

        # Initialize Langfuse SDK client
        self._sdk_client: Any = None
        self._http_client: httpx.AsyncClient | None = None

        self._initialize_sdk()

        logger.info(
            "langfuse_service_initialized",
            host=self.host,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

    def _initialize_sdk(self) -> None:
        """Initialize the Langfuse Python SDK client."""
        try:
            from langfuse import Langfuse

            self._sdk_client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host,
                release=self.release,
                tracing_enabled=True,
            )

            logger.info(
                "langfuse_sdk_initialized",
                message="Langfuse SDK client configured successfully",
                host=self.host,
            )

        except ImportError:
            logger.warning(
                "langfuse_sdk_import_failed",
                message="Langfuse package not installed, run: poetry add langfuse",
            )
            self._sdk_client = None
        except Exception as e:
            logger.error(
                "langfuse_sdk_initialization_failed",
                error_type=type(e).__name__,
                error=str(e),
                exc_info=True,
            )
            self._sdk_client = None

    @classmethod
    def from_env(cls) -> LangfuseService | None:
        """Create service from environment variables.

        Required environment variables:
        - LANGFUSE_ENABLED: Set to "true" to enable Langfuse
        - LANGFUSE_PUBLIC_KEY: Langfuse public API key
        - LANGFUSE_SECRET_KEY: Langfuse secret API key

        Optional environment variables:
        - LANGFUSE_HOST: Langfuse server URL (default: http://localhost:3000)
        - LANGFUSE_RELEASE: Application release version
        - LANGFUSE_TIMEOUT: Request timeout in seconds (default: 30)
        - LANGFUSE_MAX_RETRIES: Maximum retry attempts (default: 3)

        Returns:
            LangfuseService instance or None if not configured/disabled

        """
        langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        if not langfuse_enabled:
            logger.debug("langfuse_disabled", message="LANGFUSE_ENABLED is not true")
            return None

        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")

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
            release=os.getenv("LANGFUSE_RELEASE"),
            timeout=float(os.getenv("LANGFUSE_TIMEOUT", "30")),
            max_retries=int(os.getenv("LANGFUSE_MAX_RETRIES", "3")),
        )

    # ========================================================================
    # SDK Client Access
    # ========================================================================

    @property
    def sdk_client(self) -> Any:
        """Get the Langfuse Python SDK client.

        Returns:
            Langfuse SDK client instance or None if not available

        """
        return self._sdk_client

    # ========================================================================
    # HTTP Client for REST API Operations
    # ========================================================================

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                auth=(self.public_key, self.secret_key),
                timeout=httpx.Timeout(self.timeout),
                headers={
                    "Content-Type": "application/json",
                    "X-Langfuse-SDK-Name": "skillforge-langfuse-service",
                    "X-Langfuse-SDK-Version": "2.0.0",
                },
            )
        return self._http_client

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json: Request body as JSON
            params: Query parameters

        Returns:
            Response JSON

        Raises:
            LangfuseUnavailableError: If all retries fail
            LangfuseServiceError: For HTTP errors

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
            return await _make_request()
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
            raise LangfuseServiceError(msg) from e

    # ========================================================================
    # Lifecycle Management (SDK)
    # ========================================================================

    def flush(self) -> None:
        """Flush pending Langfuse events.

        Call this before application shutdown or in serverless environments
        to ensure all traces are sent.

        """
        if self._sdk_client is not None:
            try:
                self._sdk_client.flush()
                logger.debug("langfuse_flushed", message="Langfuse events flushed")
            except Exception as e:
                logger.error(
                    "langfuse_flush_failed",
                    error=str(e),
                    exc_info=True,
                )

    async def shutdown(self) -> None:
        """Shutdown Langfuse service gracefully.

        Call this during application shutdown to flush pending events
        and close HTTP connections.

        """
        # Flush SDK client
        if self._sdk_client is not None:
            try:
                self._sdk_client.flush()
                self._sdk_client.shutdown()
                logger.info("langfuse_sdk_shutdown", message="Langfuse SDK client shutdown")
            except Exception as e:
                logger.error(
                    "langfuse_sdk_shutdown_failed",
                    error=str(e),
                    exc_info=True,
                )

        # Close HTTP client
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

        logger.info("langfuse_service_shutdown", message="Langfuse service shutdown complete")

    # ========================================================================
    # Score Operations (SDK)
    # ========================================================================

    def submit_score(
        self,
        *,
        trace_id: str | None = None,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:
        """Submit a score to Langfuse for quality tracking.

        Uses the Langfuse SDK to create scores. Scores enable quality analytics
        in Langfuse UI including:
        - Score distributions over time
        - Filtering traces by score
        - Correlation analysis between scores

        Args:
            trace_id: Trace ID to attach score to (uses current if not provided)
            name: Score name (e.g., "relevance", "depth", "coherence")
            value: Score value (typically 0.0 to 1.0)
            comment: Optional comment explaining the score

        Example:
            >>> service = get_langfuse_service()
            >>> service.submit_score(name="relevance", value=0.85, comment="High relevance")

        """
        if self._sdk_client is None:
            logger.debug("langfuse_score_skipped_no_sdk", message="Langfuse SDK not available")
            return

        try:
            # If no trace_id provided, try to get current trace
            if trace_id is None:
                trace_id = self._sdk_client.get_current_trace_id()

            if trace_id is None:
                logger.debug(
                    "langfuse_score_skipped_no_trace",
                    message="No trace context available for score submission",
                    score_name=name,
                )
                return

            self._sdk_client.create_score(
                trace_id=str(trace_id),
                name=name,
                value=value,
                comment=comment,
            )

            # Flush immediately to ensure score is sent to Langfuse
            # Without flush, scores stay in buffer and may not appear in UI
            self._sdk_client.flush()

            logger.debug(
                "langfuse_score_submitted",
                trace_id=str(trace_id),
                score_name=name,
                score_value=value,
            )

        except Exception as e:  # noqa: BLE001 - Graceful degradation for observability
            logger.warning(
                "langfuse_score_failed",
                error=str(e),
                score_name=name,
                exc_info=True,
            )

    # ========================================================================
    # Callback Handler (SDK)
    # ========================================================================

    def get_callback_handler(self) -> Any:
        """Get Langfuse CallbackHandler for LangChain integration.

        This callback handler captures LLM calls with token counts and costs,
        enabling full observability in Langfuse including:
        - Input/output tokens
        - Cost tracking per model
        - LLM generation spans with metadata

        Note: Langfuse v3 CallbackHandler auto-configures from environment variables:
        - LANGFUSE_PUBLIC_KEY
        - LANGFUSE_SECRET_KEY
        - LANGFUSE_HOST

        Returns:
            CallbackHandler instance, or None if not available

        Example:
            >>> service = get_langfuse_service()
            >>> callbacks = [service.get_callback_handler()] if service else []
            >>> result = await chain.ainvoke(input, config={"callbacks": callbacks})

        """
        try:
            from langfuse.langchain import CallbackHandler

            # Langfuse v3 CallbackHandler auto-configures from environment variables
            handler = CallbackHandler()

            logger.debug(
                "langfuse_callback_created",
                message="Langfuse CallbackHandler created for LangChain integration",
            )

            return handler

        except ImportError:
            logger.warning(
                "langfuse_callback_import_failed",
                message="langfuse.langchain not available - install langfuse[langchain]",
            )
            return None
        except Exception as e:
            logger.exception(
                "langfuse_callback_failed",
                error_type=type(e).__name__,
                error=str(e),
            )
            return None

    # ========================================================================
    # Prompt Management (REST API)
    # ========================================================================

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

        Example:
            >>> service = get_langfuse_service()
            >>> prompt = await service.get_prompt("security-auditor", label="production")

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
        except LangfuseServiceError:
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
        except LangfuseServiceError:
            return []

    # ========================================================================
    # Annotation Queue Operations (REST API)
    # ========================================================================

    async def add_to_annotation_queue(
        self,
        queue_id: str,
        trace_id: str,
        *,
        object_type: str = "TRACE",
    ) -> bool:
        """Add an item to a Langfuse annotation queue.

        Annotation queues allow teams to review and annotate traces
        for quality assurance and model improvement.

        Args:
            queue_id: Annotation queue ID
            trace_id: Trace or observation ID to add
            object_type: Type of object (TRACE, OBSERVATION, SESSION)

        Returns:
            True if successfully added

        Example:
            >>> service = get_langfuse_service()
            >>> await service.add_to_annotation_queue("quality-review", "trace-123")

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
        except LangfuseServiceError:
            logger.warning(
                "langfuse_queue_add_failed",
                queue_id=queue_id,
                trace_id=trace_id,
            )
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

        Example:
            >>> service = get_langfuse_service()
            >>> queue = await service.get_annotation_queue("quality-review")
            >>> print(f"Queue has {queue['total']} items")

        """
        try:
            return await self._request(
                "GET",
                f"/api/public/annotation-queues/{queue_id}/items",
                params={"limit": limit, "page": page},
            )
        except LangfuseServiceError:
            logger.warning(
                "langfuse_queue_get_failed",
                queue_id=queue_id,
            )
            return {"items": [], "total": 0}

    # ========================================================================
    # Dataset Operations (REST API)
    # ========================================================================

    async def get_dataset(self, dataset_name: str) -> dict[str, Any] | None:
        """Fetch a dataset from Langfuse.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dataset data or None if not found

        """
        try:
            return await self._request(
                "GET",
                f"/api/public/v2/datasets/{dataset_name}",
            )
        except LangfuseServiceError:
            logger.warning(
                "langfuse_dataset_not_found",
                dataset_name=dataset_name,
            )
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
        except LangfuseServiceError:
            logger.warning(
                "langfuse_dataset_items_failed",
                dataset_name=dataset_name,
            )
            return []


# ============================================================================
# Module-Level Singleton and Helper Functions
# ============================================================================

_langfuse_service: LangfuseService | None = None


def get_langfuse_service() -> LangfuseService | None:
    """Get or create Langfuse service singleton.

    Returns:
        LangfuseService instance or None if not configured/disabled

    Example:
        >>> from app.core.langfuse_service import get_langfuse_service
        >>> service = get_langfuse_service()
        >>> if service:
        ...     service.submit_score(name="relevance", value=0.9)

    """
    global _langfuse_service  # noqa: PLW0603 - Module-level singleton pattern

    if _langfuse_service is None:
        _langfuse_service = LangfuseService.from_env()

    return _langfuse_service


def configure_langfuse_service() -> None:
    """Configure Langfuse service on application startup.

    This should be called during application lifespan startup.
    Unlike LangSmith, no generator filtering workarounds are needed.

    """
    service = get_langfuse_service()
    if service:
        logger.info(
            "langfuse_startup_complete",
            message="Langfuse observability ready",
        )


async def shutdown_langfuse_service() -> None:
    """Shutdown Langfuse service gracefully.

    Call this during application shutdown to flush pending events
    and close connections.

    """
    global _langfuse_service  # noqa: PLW0603

    if _langfuse_service is not None:
        await _langfuse_service.shutdown()
        _langfuse_service = None
