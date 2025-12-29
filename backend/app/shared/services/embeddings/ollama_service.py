"""Ollama embedding service for local embedding generation.

This module provides a local embedding service using Ollama, designed as a
drop-in replacement for EmbeddingService when OLLAMA_ENABLED=true.

Uses langchain-ollama v1.0.1 OllamaEmbeddings with:
- Async batch embedding support
- Configurable dimensions
- Model caching for CI performance

Recommended models:
- nomic-embed-text: 768 dimensions, fast, good quality
- mxbai-embed-large: 1024 dimensions, higher quality
- all-minilm: 384 dimensions, very fast, smaller quality

Usage:
    ```python
    from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService

    service = OllamaEmbeddingService()
    embedding = await service.generate_embedding("Hello world")
    print(len(embedding))  # 768 for nomic-embed-text
    ```

Issue #606: CI Cost Reduction via Local Models
"""

from __future__ import annotations

import time
from http import HTTPStatus
from typing import TYPE_CHECKING

import httpx
from langchain_ollama import OllamaEmbeddings

from app.core.config import settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
from app.shared.services.embeddings.utils import normalize_vector

if TYPE_CHECKING:
    from app.core.types import EmbeddingVector

logger = get_logger(__name__)


class OllamaEmbeddingService:
    """Service for generating embeddings using local Ollama models.

    This service mirrors the EmbeddingService interface but uses Ollama
    for local inference instead of OpenAI API calls.

    Key differences from EmbeddingService:
    - No API key required (local inference)
    - Different dimensions (768 for nomic-embed-text vs 1536 for OpenAI)
    - No rate limiting needed (local)
    - No cost per embedding (FREE)

    Example:
        >>> service = OllamaEmbeddingService()
        >>> embedding = await service.generate_embedding("Sample text")
        >>> len(embedding)
        768

    """

    def __init__(
        self,
        model: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        """Initialize OllamaEmbeddingService.

        Args:
            model: Ollama embedding model. Defaults to settings.OLLAMA_MODEL_EMBED.
            dimensions: Expected embedding dimensions. Defaults to settings value.

        """
        self.model = model or settings.OLLAMA_MODEL_EMBED
        self.expected_dimensions = dimensions or settings.OLLAMA_EMBEDDING_DIMENSIONS

        self._embeddings = OllamaEmbeddings(
            model=self.model,
            base_url=settings.OLLAMA_HOST,
        )

        logger.info(
            "ollama_embedding_service_initialized",
            model=self.model,
            host=settings.OLLAMA_HOST,
            dimensions=self.expected_dimensions,
            provider="ollama",
        )

    async def generate_embedding(
        self,
        text: str,
        normalize: bool = True,
    ) -> EmbeddingVector:
        """Generate embedding vector for text using Ollama.

        Args:
            text: Text to embed
            normalize: If True, apply L2 normalization (default: True)

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
            ValueError: If text is empty

        """
        if not text or not text.strip():
            msg = "Text cannot be empty"
            logger.error("embedding_empty_text")
            raise ValueError(msg)

        start_time = time.perf_counter()

        try:
            # Use aembed_query for single text (async)
            embedding = await self._embeddings.aembed_query(text)

            if not embedding:
                error_msg = "No embedding returned from Ollama"
                logger.error("ollama_embedding_empty")
                raise EmbeddingError(error_msg)

            # Validate dimensions
            if len(embedding) != self.expected_dimensions:
                logger.warning(
                    "ollama_embedding_dimension_mismatch",
                    expected=self.expected_dimensions,
                    actual=len(embedding),
                )
                # Update expected dimensions dynamically
                self.expected_dimensions = len(embedding)

            # Normalize if requested
            if normalize:
                embedding = normalize_vector(embedding)

            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "ollama_embedding_generated",
                text_length=len(text),
                embedding_dimensions=len(embedding),
                normalized=normalize,
                latency_ms=latency_ms,
            )

            return embedding

        except EmbeddingError:
            raise
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "ollama_embedding_failed",
                error=str(e),
                latency_ms=latency_ms,
            )
            error_msg = f"Ollama embedding generation failed: {e!s}"
            raise EmbeddingError(error_msg) from e

    async def generate_embeddings_batch(
        self,
        texts: list[str],
        normalize: bool = True,
    ) -> list[tuple[EmbeddingVector, float]]:
        """Generate embeddings for multiple texts.

        Uses Ollama's batch embedding capability for efficiency.

        Args:
            texts: List of texts to embed
            normalize: If True, apply L2 normalization (default: True)

        Returns:
            List of tuples (embedding_vector, latency_ms) in same order as input

        Raises:
            EmbeddingError: If embedding generation fails

        """
        if not texts:
            return []

        # Filter empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            return []

        start_time = time.perf_counter()

        try:
            # Use aembed_documents for batch (async)
            embeddings = await self._embeddings.aembed_documents(valid_texts)

            total_latency_ms = (time.perf_counter() - start_time) * 1000
            per_text_latency = total_latency_ms / len(valid_texts)

            results: list[tuple[EmbeddingVector, float]] = []
            for emb in embeddings:
                normalized_emb = normalize_vector(emb) if normalize else emb
                results.append((normalized_emb, per_text_latency))

            logger.info(
                "ollama_batch_embedding_complete",
                text_count=len(valid_texts),
                total_latency_ms=total_latency_ms,
                avg_latency_per_text=per_text_latency,
            )

            return results

        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "ollama_batch_embedding_failed",
                error=str(e),
                text_count=len(valid_texts),
                latency_ms=latency_ms,
            )
            error_msg = f"Ollama batch embedding failed: {e!s}"
            raise EmbeddingError(error_msg) from e

    async def close(self) -> None:
        """Close the service (no-op for Ollama, included for interface compatibility)."""

    @property
    def is_available(self) -> bool:
        """Check if Ollama server is available for embeddings.

        Returns:
            True if Ollama is reachable

        """
        try:
            response = httpx.get(
                f"{settings.OLLAMA_HOST}/api/tags",
                timeout=5.0,
            )
            return response.status_code == HTTPStatus.OK
        except httpx.HTTPError:
            return False


def get_embedding_service() -> OllamaEmbeddingService:
    """Get the Ollama embedding service if enabled.

    Returns OllamaEmbeddingService if OLLAMA_ENABLED, else raises.
    Use the provider factory for automatic cloud/local switching.

    Returns:
        OllamaEmbeddingService instance

    Raises:
        ValueError: If Ollama is not enabled

    """
    if not settings.OLLAMA_ENABLED:
        msg = "Ollama is not enabled. Set OLLAMA_ENABLED=true to use local embeddings."
        raise ValueError(msg)

    return OllamaEmbeddingService()
