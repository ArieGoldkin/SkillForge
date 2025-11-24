"""Embedding service for generating semantic embeddings using Ollama.

This service provides:
- Single text embedding generation
- Dimension handling (truncate/pad to match schema)
- L2 normalization for cosine similarity search
- Retry logic with exponential backoff
- Comprehensive error handling

Architecture:
- Uses ollama AsyncClient for async requests
- Connects to Ollama API endpoint (localhost:11434 by default)
- Generates 768-dimensional embeddings (nomic-embed-text)
- Returns normalized vectors for pgvector cosine similarity
"""

import os
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.constants import (
    EMBEDDING_TIMEOUT,
    HTTP_ERROR_THRESHOLD,
    MAX_ERROR_MESSAGE_LENGTH_LONG,
    MAX_RETRY_ATTEMPTS,
    MAX_TEXT_LENGTH,
    RETRY_MAX_WAIT_EMBEDDING,
    RETRY_MAX_WAIT_EMBEDDING_TEST,
    RETRY_MIN_WAIT_EMBEDDING,
    RETRY_MIN_WAIT_EMBEDDING_TEST,
    RETRY_MULTIPLIER_EMBEDDING,
)
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.core.types import EmbeddingVector
from app.services.embeddings_utils import normalize_vector

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating semantic embeddings using Ollama.

    Uses Ollama's embeddings endpoint to generate vectors for content.
    Handles dimension mismatches and normalizes vectors for cosine similarity.

    Example:
        >>> service = EmbeddingService()
        >>> embedding = await service.generate_embedding("Sample text")
        >>> len(embedding)
        768

    """

    BASE_URL = "http://localhost:11434"

    def __init__(self) -> None:
        """Initialize EmbeddingService with API client and configuration."""
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_EMBEDDING_MODEL
        self.expected_dimensions = settings.EMBEDDING_DIMENSIONS
        self.client = httpx.AsyncClient(timeout=EMBEDDING_TIMEOUT)
        self.embeddings_endpoint = f"{self.ollama_url}/api/embeddings"

        logger.info(
            "embedding_service_initialized",
            model=self.model,
            dimensions=self.expected_dimensions,
            endpoint=self.embeddings_endpoint,
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(
            multiplier=RETRY_MULTIPLIER_EMBEDDING,
            min=(
                RETRY_MIN_WAIT_EMBEDDING_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MIN_WAIT_EMBEDDING
            ),
            max=(
                RETRY_MAX_WAIT_EMBEDDING_TEST
                if os.environ.get("PYTEST_CURRENT_TEST")
                else RETRY_MAX_WAIT_EMBEDDING
            ),
        ),
        reraise=True,
    )
    async def generate_embedding(self, text: str, normalize: bool = True) -> EmbeddingVector:
        """Generate embedding vector for text using Ollama.

        Args:
            text: Text to embed
            normalize: If True, apply L2 normalization (default: True)

        Returns:
            List of floats representing the embedding vector (expected dimensions)

        Raises:
            EmbeddingError: If embedding generation fails

        """
        if not text or not text.strip():
            msg = "Text cannot be empty"
            logger.error("embedding_empty_text")
            raise ValueError(msg)

        # Truncate text if too long (Ollama has limits, typically 8192 tokens)
        original_length = len(text)
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
            logger.warning(
                "embedding_text_truncated",
                original_length=original_length,
                truncated_length=MAX_TEXT_LENGTH,
            )

        try:
            # Call Ollama embeddings API
            response = await self.client.post(
                self.embeddings_endpoint,
                json={"model": self.model, "prompt": text},
            )

            # Handle HTTP errors
            if response.status_code >= HTTP_ERROR_THRESHOLD:
                error_msg = (
                    f"HTTP {response.status_code}: {response.text[:MAX_ERROR_MESSAGE_LENGTH_LONG]}"
                )
                logger.error(
                    "embedding_http_error",
                    status_code=response.status_code,
                    error=error_msg,
                )
                raise EmbeddingError(error_msg)  # noqa: TRY301

            # Parse response
            data: dict[str, Any] = response.json()
            embedding = data.get("embedding")

            if not embedding:
                error_msg = "No 'embedding' field in API response"
                logger.error(
                    "embedding_missing_field",
                    response_data=str(data)[:MAX_ERROR_MESSAGE_LENGTH_LONG],
                )
                raise EmbeddingError(error_msg)  # noqa: TRY301

            if not isinstance(embedding, list):
                error_msg = f"Expected list embedding, got {type(embedding)}"
                logger.error("embedding_invalid_type", embedding_type=type(embedding).__name__)
                raise EmbeddingError(error_msg)  # noqa: TRY301

            # Handle dimension mismatch (like reporter-accuracy)
            if len(embedding) > self.expected_dimensions:
                logger.info(
                    "embedding_truncated",
                    original_dimensions=len(embedding),
                    expected_dimensions=self.expected_dimensions,
                )
                embedding = embedding[: self.expected_dimensions]
            elif len(embedding) < self.expected_dimensions:
                logger.warning(
                    "embedding_padded",
                    original_dimensions=len(embedding),
                    expected_dimensions=self.expected_dimensions,
                )
                embedding = embedding + [0.0] * (self.expected_dimensions - len(embedding))

            # Normalize if requested (L2 norm for cosine similarity)
            if normalize:
                embedding = normalize_vector(embedding)

            logger.info(
                "embedding_generated",
                text_length=original_length,
                embedding_dimensions=len(embedding),
                normalized=normalize,
            )
        except httpx.TimeoutException as e:
            timeout_msg = "Request timed out"
            logger.exception("embedding_timeout", error=str(e))
            raise EmbeddingError(timeout_msg) from e

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
        else:
            return embedding

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
