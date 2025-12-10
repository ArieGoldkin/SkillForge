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

        # Token-based truncation (not character-based)
        # OpenAI text-embedding-3-small limit is 8,191 tokens
        # Lazy-load encoding on first use using thread pool to avoid blocking
        import asyncio

        if self._encoding is None:
            # Initialize encoding in thread pool to avoid blocking the event loop
            self._encoding = await asyncio.to_thread(
                tiktoken.encoding_for_model, "text-embedding-3-small"
            )

        assert self._encoding is not None
        tokens = self._encoding.encode(text)
        original_token_count = len(tokens)
        original_length = len(text)
        truncated = False

        if original_token_count > self.max_tokens:
            # Truncate tokens, then decode back to text
            truncated_tokens = tokens[: self.max_tokens]
            text = self._encoding.decode(truncated_tokens)
            truncated = True
            logger.warning(
                "embedding_text_truncated",
                original_tokens=original_token_count,
                truncated_tokens=self.max_tokens,
                original_chars=original_length,
                truncated_chars=len(text),
            )

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
            # Handle OpenAI API errors with proper error tracking
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Track error type for backpressure decisions
            if e.status_code == 429:
                self._error_tracker.record_rate_limit()
                self._batch_sizer.decrease_for_rate_limit()
                self._metrics.record_api_error(provider="openai", status=429)
            elif e.status_code >= 500:
                self._error_tracker.record_server_error(e.status_code)
                self._batch_sizer.decrease_for_server_error()
                self._metrics.record_api_error(provider="openai", status=e.status_code)
            else:
                self._error_tracker.record_error(ErrorType.OTHER, e.status_code)
                self._metrics.record_api_error(provider="openai", status=e.status_code)

            self._metrics.record_embedding_request(
                status="api_error",
                latency_ms=latency_ms,
                token_count=original_token_count,
                truncated=truncated,
            )

            error_msg = f"Embedding generation failed: {e!s}"
            logger.exception(
                "embedding_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
                status_code=e.status_code,
            )
            raise EmbeddingError(error_msg) from e

        except Exception as e:
            # Handle unexpected errors
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._error_tracker.record_error(ErrorType.OTHER)
            self._metrics.record_embedding_request(
                status="error",
                latency_ms=latency_ms,
                token_count=original_token_count,
                truncated=truncated,
            )
            self._metrics.record_api_error(provider="openai", status="unknown")

            error_msg = f"Embedding generation failed: {e!s}"
            logger.exception(
                "embedding_generation_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise EmbeddingError(error_msg) from e

    async def close(self) -> None:
        """Close the OpenAI client."""
        await self.client.close()
