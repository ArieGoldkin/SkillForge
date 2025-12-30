"""Embedding service for generating semantic embeddings using OpenAI.

This service provides:
- Single text embedding generation
- Batch embedding generation with optional Batch API support (50% cost savings)
- L2 normalization for cosine similarity search
- Retry logic with exponential backoff
- Comprehensive error handling with specific OpenAI exception types
- Metrics collection and telemetry
- Backpressure handling with adaptive rate limiting
- Circuit breaker pattern for resilience (opens after 5 failures, recovers after 60s)
- Fine-grained httpx timeout configuration (connect, read, write, pool)

Architecture:
- Uses OpenAI SDK for async requests with httpx.Timeout configuration
- Generates 1536-dimensional embeddings (text-embedding-3-small)
- Returns normalized vectors for pgvector cosine similarity
- Records metrics via MetricsService for observability
- Integrates error tracking and rate limiting for resilience
- Optionally uses Batch API for 50% cost savings on non-time-sensitive operations
- Circuit breaker prevents cascade failures and enables graceful degradation
"""

import time
from typing import cast

import httpx
import tiktoken
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from app.core.config import settings
from app.core.constants import (
    EMBEDDING_CIRCUIT_FAILURE_THRESHOLD,
    EMBEDDING_CIRCUIT_SUCCESS_THRESHOLD,
    EMBEDDING_CIRCUIT_TIMEOUT_SECONDS,
    EMBEDDING_HTTP_CONNECT_TIMEOUT,
    EMBEDDING_HTTP_POOL_TIMEOUT,
    EMBEDDING_HTTP_READ_TIMEOUT,
    EMBEDDING_HTTP_WRITE_TIMEOUT,
    HTTP_RATE_LIMITED,
    HTTP_SERVER_ERROR_THRESHOLD,
    MAX_RETRY_ATTEMPTS,
    RETRY_MAX_WAIT_EMBEDDING,
    RETRY_MIN_WAIT_EMBEDDING,
    RETRY_MULTIPLIER_EMBEDDING,
)
from app.core.exceptions import EmbeddingError, ServiceException
from app.core.logging import get_logger
from app.core.types import EmbeddingVector
from app.shared.services.backpressure import (
    ErrorType,
    get_embedding_batch_sizer,
    get_embedding_error_tracker,
    get_embedding_rate_limiter,
)
from app.shared.services.embeddings.utils import normalize_vector
from app.shared.services.metrics import get_metrics_service

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating semantic embeddings using OpenAI.

    Uses OpenAI's embeddings API to generate vectors for content.
    Normalizes vectors for cosine similarity search.

    Example:
        >>> service = EmbeddingService()
        >>> embedding = await service.generate_embedding("Sample text")
        >>> len(embedding)
        1536

    """

    def __init__(self) -> None:
        """Initialize EmbeddingService with OpenAI client and telemetry.

        Raises:
            ValueError: If OPENAI_API_KEY is not configured.

        """
        if not settings.OPENAI_API_KEY:
            msg = "OPENAI_API_KEY is required for embedding generation"
            raise ValueError(msg)

        # Configure httpx timeout following 2025 best practices
        timeout_config = httpx.Timeout(
            connect=EMBEDDING_HTTP_CONNECT_TIMEOUT,
            read=EMBEDDING_HTTP_READ_TIMEOUT,
            write=EMBEDDING_HTTP_WRITE_TIMEOUT,
            pool=EMBEDDING_HTTP_POOL_TIMEOUT,
        )

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=timeout_config)
        self.model = "text-embedding-3-small"
        self.expected_dimensions = 1536
        self.max_tokens = 8_000  # Safety margin below 8,191 token limit
        # Lazy-load encoding to avoid blocking calls in async context
        # Encoding will be initialized on first use in generate_embedding()
        self._encoding: tiktoken.Encoding | None = None

        # Circuit breaker for resilience (opens after 5 failures, recovers after 60s)
        self._circuit_breaker = CircuitBreaker(
            name="embedding_service",
            config=CircuitBreakerConfig(
                failure_threshold=EMBEDDING_CIRCUIT_FAILURE_THRESHOLD,
                success_threshold=EMBEDDING_CIRCUIT_SUCCESS_THRESHOLD,
                timeout_seconds=EMBEDDING_CIRCUIT_TIMEOUT_SECONDS,
                excluded_exceptions=(ValueError,),  # Don't trip on validation errors
            ),
        )

        # Telemetry components (lazy-loaded singletons)
        self._metrics = get_metrics_service()
        self._rate_limiter = get_embedding_rate_limiter()
        self._error_tracker = get_embedding_error_tracker()
        self._batch_sizer = get_embedding_batch_sizer()

        logger.info(
            "embedding_service_initialized",
            model=self.model,
            dimensions=self.expected_dimensions,
            max_tokens=self.max_tokens,
            encoding="cl100k_base",  # text-embedding-3-small uses cl100k_base
            provider="openai",
            metrics_enabled=settings.METRICS_ENABLED,
            timeout_config={
                "connect": EMBEDDING_HTTP_CONNECT_TIMEOUT,
                "read": EMBEDDING_HTTP_READ_TIMEOUT,
                "write": EMBEDDING_HTTP_WRITE_TIMEOUT,
                "pool": EMBEDDING_HTTP_POOL_TIMEOUT,
            },
            circuit_breaker={
                "failure_threshold": EMBEDDING_CIRCUIT_FAILURE_THRESHOLD,
                "success_threshold": EMBEDDING_CIRCUIT_SUCCESS_THRESHOLD,
                "timeout_seconds": EMBEDDING_CIRCUIT_TIMEOUT_SECONDS,
            },
        )

    def _handle_api_status_error(
        self,
        error: APIStatusError,
        latency_ms: float,
        token_count: int,
        truncated: bool,
    ) -> None:
        """Handle OpenAI API errors with backpressure and metrics.

        Args:
            error: The API status error from OpenAI
            latency_ms: Request latency in milliseconds
            token_count: Original token count before truncation
            truncated: Whether the input was truncated

        """
        if error.status_code == HTTP_RATE_LIMITED:
            self._error_tracker.record_rate_limit()
            self._batch_sizer.decrease_for_rate_limit()
            self._metrics.record_api_error(provider="openai", status=HTTP_RATE_LIMITED)
        elif error.status_code >= HTTP_SERVER_ERROR_THRESHOLD:
            self._error_tracker.record_server_error(error.status_code)
            self._batch_sizer.decrease_for_server_error()
            self._metrics.record_api_error(provider="openai", status=error.status_code)
        else:
            self._error_tracker.record_error(ErrorType.OTHER, error.status_code)
            self._metrics.record_api_error(provider="openai", status=error.status_code)

        self._metrics.record_embedding_request(
            status="api_error",
            latency_ms=latency_ms,
            token_count=token_count,
            truncated=truncated,
        )

        logger.exception(
            "embedding_generation_failed",
            error=str(error),
            error_type=type(error).__name__,
            status_code=error.status_code,
        )

    def _handle_generic_error(
        self,
        error: Exception,
        latency_ms: float,
        token_count: int,
        truncated: bool,
    ) -> None:
        """Handle unexpected errors with metrics recording.

        Args:
            error: The unexpected exception
            latency_ms: Request latency in milliseconds
            token_count: Original token count before truncation
            truncated: Whether the input was truncated

        """
        self._error_tracker.record_error(ErrorType.OTHER)
        self._metrics.record_embedding_request(
            status="error",
            latency_ms=latency_ms,
            token_count=token_count,
            truncated=truncated,
        )
        self._metrics.record_api_error(provider="openai", status="unknown")

        logger.exception(
            "embedding_generation_failed",
            error=str(error),
            error_type=type(error).__name__,
        )

    async def _prepare_text(self, text: str) -> tuple[str, int, bool]:
        """Prepare text for embedding by tokenizing and truncating if needed.

        Args:
            text: The input text to prepare

        Returns:
            Tuple of (processed_text, original_token_count, was_truncated)

        """
        import asyncio

        if self._encoding is None:
            self._encoding = await asyncio.to_thread(
                tiktoken.encoding_for_model, "text-embedding-3-small"
            )

        # Encoding should always be initialized at this point
        # as we called asyncio.to_thread above
        if self._encoding is None:
            msg = "Encoding failed to initialize"
            raise ServiceException(msg)
        tokens = self._encoding.encode(text)
        original_token_count = len(tokens)
        truncated = False

        if original_token_count > self.max_tokens:
            truncated_tokens = tokens[: self.max_tokens]
            text = self._encoding.decode(truncated_tokens)
            truncated = True
            logger.warning(
                "embedding_text_truncated",
                original_tokens=original_token_count,
                truncated_tokens=self.max_tokens,
                original_chars=len(text),
                truncated_chars=len(text),
            )

        return text, original_token_count, truncated

    async def _call_openai_api(self, text: str) -> list[float]:
        """Call OpenAI API with circuit breaker protection.

        This internal method wraps the OpenAI API call with circuit breaker
        for resilience. It handles all OpenAI-specific exceptions.

        Args:
            text: Prepared text to embed

        Returns:
            Raw embedding vector from OpenAI

        Raises:
            APIConnectionError: Connection to OpenAI failed
            APITimeoutError: Request timed out
            RateLimitError: Rate limit exceeded
            APIStatusError: API returned error status
            EmbeddingError: Invalid response from API

        """

        async def _api_call() -> list[float]:
            """Inner function for circuit breaker to wrap."""
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            # Log usage metadata if available (OpenAI SDK 1.0+)
            if hasattr(response, "usage") and response.usage:
                logger.info(
                    "embedding_token_usage",
                    total_tokens=response.usage.total_tokens,
                    prompt_tokens=getattr(response.usage, "prompt_tokens", 0),
                )

            # Extract embedding from response
            embedding = cast("list[float]", response.data[0].embedding)

            if not embedding:
                error_msg = "No embedding in API response"
                logger.error("embedding_missing_field")
                raise EmbeddingError(error_msg)

            if len(embedding) != self.expected_dimensions:
                error_msg = f"Expected {self.expected_dimensions} dimensions, got {len(embedding)}"
                logger.error(
                    "embedding_dimension_mismatch",
                    expected=self.expected_dimensions,
                    actual=len(embedding),
                )
                raise EmbeddingError(error_msg)

            return embedding

        # Call through circuit breaker
        # Circuit breaker preserves return type at runtime; cast for static analysis
        result = await self._circuit_breaker.call(_api_call)
        return cast("list[float]", result)

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER_EMBEDDING,
            min=RETRY_MIN_WAIT_EMBEDDING,
            max=RETRY_MAX_WAIT_EMBEDDING,
        ),
        reraise=True,
    )
    async def generate_embedding(self, text: str, normalize: bool = True) -> EmbeddingVector:  # noqa: PLR0915
        """Generate embedding vector for text using OpenAI.

        Args:
            text: Text to embed (max 8,000 tokens)
            normalize: If True, apply L2 normalization (default: True)

        Returns:
            List of floats representing the embedding vector (1536 dimensions)

        Raises:
            EmbeddingError: If embedding generation fails
            ValueError: If text is empty

        """
        if not text or not text.strip():
            msg = "Text cannot be empty"
            logger.error("embedding_empty_text")
            raise ValueError(msg)

        # Tokenize and truncate if needed
        text, original_token_count, truncated = await self._prepare_text(text)

        # Apply rate limiting before API call
        await self._rate_limiter.acquire_async(tokens=1)

        # Track timing for metrics
        start_time = time.perf_counter()

        try:
            # Call OpenAI API through circuit breaker
            embedding = await self._call_openai_api(text)

            # Normalize if requested (L2 norm for cosine similarity)
            if normalize:
                embedding = normalize_vector(embedding)

            # Calculate latency and record success metrics
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_success()
            self._metrics.record_embedding_request(
                status="success",
                latency_ms=latency_ms,
                token_count=original_token_count,
                truncated=truncated,
                batch_size=1,
            )

            logger.info(
                "embedding_generated",
                text_length=len(text),
                token_count=original_token_count,
                embedding_dimensions=len(embedding),
                normalized=normalize,
                latency_ms=latency_ms,
                circuit_state=self._circuit_breaker.state.value,
            )

            return embedding

        except EmbeddingError:
            # Re-raise EmbeddingError without modification
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_embedding_request(
                status="error",
                latency_ms=latency_ms,
                token_count=original_token_count,
                truncated=truncated,
            )
            raise

        except APIConnectionError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_error(ErrorType.OTHER)
            self._metrics.record_embedding_request(
                status="connection_error",
                latency_ms=latency_ms,
                token_count=original_token_count,
                truncated=truncated,
            )
            self._metrics.record_api_error(provider="openai", status="connection_error")
            logger.exception(
                "embedding_connection_failed",
                error=str(e),
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = "Failed to connect to OpenAI API"
            raise EmbeddingError(error_msg) from e

        except APITimeoutError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_error(ErrorType.OTHER)
            self._metrics.record_embedding_request(
                status="timeout",
                latency_ms=latency_ms,
                token_count=original_token_count,
                truncated=truncated,
            )
            self._metrics.record_api_error(provider="openai", status="timeout")
            logger.exception(
                "embedding_timeout",
                error=str(e),
                timeout_config={
                    "connect": EMBEDDING_HTTP_CONNECT_TIMEOUT,
                    "read": EMBEDDING_HTTP_READ_TIMEOUT,
                },
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = "Request to OpenAI API timed out"
            raise EmbeddingError(error_msg) from e

        except RateLimitError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_rate_limit()
            self._batch_sizer.decrease_for_rate_limit()
            self._metrics.record_embedding_request(
                status="rate_limited",
                latency_ms=latency_ms,
                token_count=original_token_count,
                truncated=truncated,
            )
            self._metrics.record_api_error(provider="openai", status=HTTP_RATE_LIMITED)
            logger.exception(
                "embedding_rate_limited",
                error=str(e),
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = "OpenAI API rate limit exceeded"
            raise EmbeddingError(error_msg) from e

        except APIStatusError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_api_status_error(e, latency_ms, original_token_count, truncated)
            logger.exception(
                "embedding_api_error",
                status_code=e.status_code,
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = f"OpenAI API error: {e!s}"
            raise EmbeddingError(error_msg) from e

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_generic_error(e, latency_ms, original_token_count, truncated)
            logger.exception(
                "embedding_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = f"Embedding generation failed: {e!s}"
            raise EmbeddingError(error_msg) from e

    async def close(self) -> None:
        """Close the OpenAI client."""
        await self.client.close()

    async def generate_embeddings_batch(
        self,
        texts: list[str],
        normalize: bool = True,
        batch_size: int | None = None,
        use_batch_api: bool | None = None,
    ) -> list[tuple[EmbeddingVector, float]]:
        """Generate embeddings for multiple texts using batch API.

        Uses OpenAI's multi-input embedding API for efficiency.
        Optionally uses OpenAI Batch API for 50% cost savings on large batches.

        Args:
            texts: List of texts to embed
            normalize: If True, apply L2 normalization (default: True)
            batch_size: Optional batch size override. Uses adaptive batch sizer if None.
            use_batch_api: If True, uses Batch API for 50% savings (24h window).
                          If None, uses settings.OPENAI_BATCH_ENABLED.

        Returns:
            List of tuples (embedding_vector, latency_ms) in same order as input

        Raises:
            EmbeddingError: If embedding generation fails
            ValueError: If texts is empty

        """
        if not texts:
            return []

        # Determine if we should use Batch API
        should_use_batch_api = (
            use_batch_api
            if use_batch_api is not None
            else settings.OPENAI_BATCH_ENABLED and len(texts) >= settings.OPENAI_BATCH_MIN_SIZE
        )

        if should_use_batch_api:
            logger.info(
                "using_batch_api_for_embeddings",
                text_count=len(texts),
                cost_savings="50%",
                completion_window=settings.OPENAI_BATCH_COMPLETION_WINDOW,
            )
            return await self._generate_embeddings_batch_api(texts, normalize)

        # Use real-time API (existing implementation)
        # Use adaptive batch size from backpressure system if not specified
        if batch_size is None:
            batch_size = self._batch_sizer.current_size

        # Clamp batch size to configured limits
        batch_size = max(
            settings.BATCH_SIZE_MIN,
            min(batch_size, settings.BATCH_SIZE_MAX),
        )

        results: list[tuple[EmbeddingVector, float]] = []
        total_tokens = 0

        for batch_start in range(0, len(texts), batch_size):
            batch_texts = texts[batch_start : batch_start + batch_size]
            batch_results = await self._embed_batch(batch_texts, normalize)

            # Track stats
            for embedding, latency_ms in batch_results:
                results.append((embedding, latency_ms))
                total_tokens += len(embedding)

        # Record batch-level metrics
        self._metrics.record_batch_embedding(
            batch_count=len(texts),
            total_latency_ms=sum(r[1] for r in results),
            avg_batch_size=batch_size,
        )

        logger.info(
            "batch_embedding_complete",
            total_texts=len(texts),
            batch_size=batch_size,
            batch_count=(len(texts) + batch_size - 1) // batch_size,
        )

        return results

    async def _generate_embeddings_batch_api(
        self,
        texts: list[str],
        normalize: bool = True,
    ) -> list[tuple[EmbeddingVector, float]]:
        """Generate embeddings using OpenAI Batch API for 50% cost savings.

        This method uses the Batch API which has a 24h completion window but
        provides 50% cost savings. Suitable for golden dataset generation,
        evaluation runs, and other non-time-sensitive operations.

        Args:
            texts: List of texts to embed
            normalize: If True, apply L2 normalization (default: True)

        Returns:
            List of tuples (embedding_vector, latency_ms) in same order as input

        Raises:
            EmbeddingError: If batch processing fails

        """
        from app.shared.services.batch.openai_batch import batch_embeddings

        start_time = time.perf_counter()

        try:
            # Use batch_embeddings helper from openai_batch.py
            embeddings = await batch_embeddings(texts, model=self.model)

            # Normalize if requested
            if normalize:
                embeddings = [normalize_vector(emb) for emb in embeddings]

            # Calculate total latency
            total_latency_ms = (time.perf_counter() - start_time) * 1000
            per_text_latency = total_latency_ms / len(texts)

            # Record success metrics
            self._metrics.record_batch_embedding(
                batch_count=len(texts),
                total_latency_ms=total_latency_ms,
                avg_batch_size=len(texts),
            )

            logger.info(
                "batch_api_embeddings_complete",
                text_count=len(texts),
                total_latency_ms=total_latency_ms,
                cost_savings="50%",
            )

            # Return in expected format: list of (embedding, latency) tuples
            return [(emb, per_text_latency) for emb in embeddings]

        except Exception as e:
            logger.exception(
                "batch_api_embeddings_failed",
                error=str(e),
                text_count=len(texts),
            )
            # Fall back to real-time API
            logger.warning(
                "batch_api_fallback_to_realtime",
                reason="Batch API failed, using real-time API",
            )
            return await self.generate_embeddings_batch(
                texts, normalize=normalize, use_batch_api=False
            )

    async def _call_openai_batch_api(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI batch API with circuit breaker protection.

        Args:
            texts: List of prepared texts to embed

        Returns:
            List of raw embedding vectors from OpenAI

        Raises:
            APIConnectionError: Connection to OpenAI failed
            APITimeoutError: Request timed out
            RateLimitError: Rate limit exceeded
            APIStatusError: API returned error status
            EmbeddingError: Invalid response from API

        """

        async def _api_call() -> list[list[float]]:
            """Inner function for circuit breaker to wrap."""
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )

            # Log usage metadata if available (OpenAI SDK 1.0+)
            if hasattr(response, "usage") and response.usage:
                logger.info(
                    "batch_embedding_token_usage",
                    total_tokens=response.usage.total_tokens,
                    prompt_tokens=getattr(response.usage, "prompt_tokens", 0),
                    batch_size=len(texts),
                )

            # Extract embeddings and maintain order
            embeddings: list[list[float]] = []
            for data in response.data:
                embedding = cast("list[float]", data.embedding)

                if len(embedding) != self.expected_dimensions:
                    error_msg = (
                        f"Expected {self.expected_dimensions} dimensions, got {len(embedding)}"
                    )
                    raise EmbeddingError(error_msg)

                embeddings.append(embedding)

            return embeddings

        # Call through circuit breaker
        # Circuit breaker preserves return type at runtime; cast for static analysis
        result = await self._circuit_breaker.call(_api_call)
        return cast("list[list[float]]", result)

    async def _embed_batch(  # noqa: PLR0915
        self,
        texts: list[str],
        normalize: bool,
    ) -> list[tuple[EmbeddingVector, float]]:
        """Embed a single batch of texts.

        Args:
            texts: Batch of texts to embed
            normalize: Whether to normalize vectors

        Returns:
            List of (embedding, latency_ms) tuples

        """
        if not texts:
            return []

        # Prepare texts (tokenize and truncate each)
        prepared_texts: list[str] = []
        for text in texts:
            if not text or not text.strip():
                continue
            prepared_text, _, _ = await self._prepare_text(text)
            prepared_texts.append(prepared_text)

        if not prepared_texts:
            return []

        # Apply rate limiting before batch API call
        await self._rate_limiter.acquire_async(tokens=len(prepared_texts))

        start_time = time.perf_counter()

        try:
            # Call OpenAI batch API through circuit breaker
            embeddings = await self._call_openai_batch_api(prepared_texts)

            latency_ms = (time.perf_counter() - start_time) * 1000
            per_text_latency = latency_ms / len(prepared_texts)

            # Normalize if requested and create results
            results: list[tuple[EmbeddingVector, float]] = []
            for emb in embeddings:
                normalized_emb = normalize_vector(emb) if normalize else emb
                results.append((normalized_emb, per_text_latency))

            # Record success and metrics
            self._error_tracker.record_success()
            self._metrics.record_embedding_request(
                status="success",
                latency_ms=latency_ms,
                token_count=sum(len(t) for t in prepared_texts),  # Approximate
                truncated=False,
                batch_size=len(prepared_texts),
            )

            # Allow batch sizer to potentially increase after success
            self._batch_sizer.try_increase(self._error_tracker)

            logger.info(
                "batch_embedding_success",
                batch_size=len(prepared_texts),
                latency_ms=latency_ms,
                circuit_state=self._circuit_breaker.state.value,
            )

            return results

        except EmbeddingError:
            # Re-raise EmbeddingError without modification
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._metrics.record_embedding_request(
                status="error",
                latency_ms=latency_ms,
                token_count=0,
                truncated=False,
            )
            raise

        except APIConnectionError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_error(ErrorType.OTHER)
            self._metrics.record_embedding_request(
                status="connection_error",
                latency_ms=latency_ms,
                token_count=0,
                truncated=False,
            )
            self._metrics.record_api_error(provider="openai", status="connection_error")
            logger.exception(
                "batch_embedding_connection_failed",
                error=str(e),
                batch_size=len(prepared_texts),
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = "Failed to connect to OpenAI API for batch embedding"
            raise EmbeddingError(error_msg) from e

        except APITimeoutError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_error(ErrorType.OTHER)
            self._metrics.record_embedding_request(
                status="timeout",
                latency_ms=latency_ms,
                token_count=0,
                truncated=False,
            )
            self._metrics.record_api_error(provider="openai", status="timeout")
            logger.exception(
                "batch_embedding_timeout",
                error=str(e),
                batch_size=len(prepared_texts),
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = "Batch embedding request timed out"
            raise EmbeddingError(error_msg) from e

        except RateLimitError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_rate_limit()
            self._batch_sizer.decrease_for_rate_limit()
            self._metrics.record_embedding_request(
                status="rate_limited",
                latency_ms=latency_ms,
                token_count=0,
                truncated=False,
            )
            self._metrics.record_api_error(provider="openai", status=HTTP_RATE_LIMITED)
            logger.exception(
                "batch_embedding_rate_limited",
                error=str(e),
                batch_size=len(prepared_texts),
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = "OpenAI API rate limit exceeded for batch embedding"
            raise EmbeddingError(error_msg) from e

        except APIStatusError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_api_status_error(e, latency_ms, token_count=0, truncated=False)
            logger.exception(
                "batch_embedding_api_error",
                status_code=e.status_code,
                batch_size=len(prepared_texts),
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = f"Batch embedding API error: {e!s}"
            raise EmbeddingError(error_msg) from e

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_generic_error(e, latency_ms, token_count=0, truncated=False)
            logger.exception(
                "batch_embedding_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                batch_size=len(prepared_texts),
                circuit_state=self._circuit_breaker.state.value,
            )
            error_msg = f"Batch embedding generation failed: {e!s}"
            raise EmbeddingError(error_msg) from e
