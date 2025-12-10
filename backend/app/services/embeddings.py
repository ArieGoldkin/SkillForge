"""Embedding service for generating semantic embeddings using OpenAI.

This service provides:
- Single text embedding generation
- L2 normalization for cosine similarity search
- Retry logic with exponential backoff
- Comprehensive error handling
- Metrics collection and telemetry
- Backpressure handling with adaptive rate limiting

Architecture:
- Uses OpenAI SDK for async requests
- Generates 1536-dimensional embeddings (text-embedding-3-small)
- Returns normalized vectors for pgvector cosine similarity
- Records metrics via MetricsService for observability
- Integrates error tracking and rate limiting for resilience
"""

import time
from typing import cast

import tiktoken
from openai import APIStatusError, AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.constants import (
    HTTP_RATE_LIMITED,
    HTTP_SERVER_ERROR_THRESHOLD,
    MAX_RETRY_ATTEMPTS,
    RETRY_MAX_WAIT_EMBEDDING,
    RETRY_MIN_WAIT_EMBEDDING,
    RETRY_MULTIPLIER_EMBEDDING,
)
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.core.types import EmbeddingVector
from app.services.backpressure import (
    ErrorType,
    get_embedding_batch_sizer,
    get_embedding_error_tracker,
    get_embedding_rate_limiter,
)
from app.services.embeddings_utils import normalize_vector
from app.services.metrics import get_metrics_service

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

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"
        self.expected_dimensions = 1536
        self.max_tokens = 8_000  # Safety margin below 8,191 token limit
        # Lazy-load encoding to avoid blocking calls in async context
        # Encoding will be initialized on first use in generate_embedding()
        self._encoding: tiktoken.Encoding | None = None

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

        assert self._encoding is not None
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

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER_EMBEDDING,
            min=RETRY_MIN_WAIT_EMBEDDING,
            max=RETRY_MAX_WAIT_EMBEDDING,
        ),
        reraise=True,
    )
    async def generate_embedding(self, text: str, normalize: bool = True) -> EmbeddingVector:
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
            # Call OpenAI embeddings API
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            # Extract embedding from response
            # Type cast needed because OpenAI SDK types embedding as Any
            embedding = cast(EmbeddingVector, response.data[0].embedding)

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

        except APIStatusError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_api_status_error(e, latency_ms, original_token_count, truncated)
            error_msg = f"Embedding generation failed: {e!s}"
            raise EmbeddingError(error_msg) from e

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_generic_error(e, latency_ms, original_token_count, truncated)
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
    ) -> list[tuple[EmbeddingVector, float]]:
        """Generate embeddings for multiple texts using batch API.

        Uses OpenAI's multi-input embedding API for efficiency.
        Returns embeddings in the same order as input texts.

        Args:
            texts: List of texts to embed
            normalize: If True, apply L2 normalization (default: True)
            batch_size: Optional batch size override. Uses adaptive batch sizer if None.

        Returns:
            List of tuples (embedding_vector, latency_ms) in same order as input

        Raises:
            EmbeddingError: If embedding generation fails
            ValueError: If texts is empty

        """
        if not texts:
            return []

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

    async def _embed_batch(
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
            # Call OpenAI embeddings API with batch input
            response = await self.client.embeddings.create(
                model=self.model,
                input=prepared_texts,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000
            per_text_latency = latency_ms / len(prepared_texts)

            # Extract embeddings and maintain order
            results: list[tuple[EmbeddingVector, float]] = []
            for data in response.data:
                embedding = cast(EmbeddingVector, data.embedding)

                if len(embedding) != self.expected_dimensions:
                    error_msg = (
                        f"Expected {self.expected_dimensions} dimensions, got {len(embedding)}"
                    )
                    raise EmbeddingError(error_msg)

                if normalize:
                    embedding = normalize_vector(embedding)

                results.append((embedding, per_text_latency))

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

            return results

        except APIStatusError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_api_status_error(e, latency_ms, 0, False)
            error_msg = f"Batch embedding generation failed: {e!s}"
            raise EmbeddingError(error_msg) from e

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._handle_generic_error(e, latency_ms, 0, False)
            error_msg = f"Batch embedding generation failed: {e!s}"
            raise EmbeddingError(error_msg) from e
