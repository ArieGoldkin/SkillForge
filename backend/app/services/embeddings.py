"""Embedding service for generating semantic embeddings using OpenAI.

This service provides:
- Single text embedding generation
- L2 normalization for cosine similarity search
- Retry logic with exponential backoff
- Comprehensive error handling

Architecture:
- Uses OpenAI SDK for async requests
- Generates 1536-dimensional embeddings (text-embedding-3-small)
- Returns normalized vectors for pgvector cosine similarity
"""

from openai import AsyncOpenAI
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
from app.services.embeddings_utils import normalize_vector

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
        """Initialize EmbeddingService with OpenAI client.

        Raises:
            ValueError: If OPENAI_API_KEY is not configured.

        """
        if not settings.OPENAI_API_KEY:
            msg = "OPENAI_API_KEY is required for embedding generation"
            raise ValueError(msg)

        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "text-embedding-3-small"
        self.expected_dimensions = 1536
        self.max_text_length = 32_000  # ~8,191 tokens (OpenAI limit)

        logger.info(
            "embedding_service_initialized",
            model=self.model,
            dimensions=self.expected_dimensions,
            provider="openai",
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
            text: Text to embed (max 32,000 characters)
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

        # Truncate text if too long (OpenAI limit: 8,191 tokens ≈ 32,000 chars)
        original_length = len(text)
        if len(text) > self.max_text_length:
            text = text[: self.max_text_length]
            logger.warning(
                "embedding_text_truncated",
                original_length=original_length,
                truncated_length=self.max_text_length,
            )

        try:
            # Call OpenAI embeddings API
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            # Extract embedding from response
            embedding = response.data[0].embedding

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

            logger.info(
                "embedding_generated",
                text_length=original_length,
                embedding_dimensions=len(embedding),
                normalized=normalize,
            )

            return embedding

        except EmbeddingError:
            # Re-raise EmbeddingError without modification
            raise

        except Exception as e:
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
