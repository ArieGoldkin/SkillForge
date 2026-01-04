"""Embedding service module.

Provides multiple embedding implementations:
- EmbeddingService: Production OpenAI embeddings (1536 dims)
- OllamaEmbeddingService: Local Ollama embeddings (768 dims, FREE)
- CachedEmbeddingService: Pre-computed cache with hybrid fallback
- DeterministicEmbeddingService: Hash-based for testing (no semantic understanding)

All implementations conform to the EmbeddingServiceProtocol for type safety.
"""

from typing import Protocol, runtime_checkable

from app.core.exceptions import EmbeddingError
from app.shared.services.embeddings.cached import CachedEmbeddingService
from app.shared.services.embeddings.deterministic import DeterministicEmbeddingService
from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.embeddings.utils import normalize_vector


@runtime_checkable
class EmbeddingServiceProtocol(Protocol):
    """Protocol defining the common interface for all embedding services.

    All embedding service implementations must provide:
    - model: str attribute for identifying the model
    - expected_dimensions: int property for embedding vector size
    - generate_embedding: async method for single text embedding
    """

    model: str

    @property
    def expected_dimensions(self) -> int:
        """Return the embedding vector dimensions."""
        ...

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text."""
        ...


__all__ = [
    "CachedEmbeddingService",
    "DeterministicEmbeddingService",
    "EmbeddingError",
    "EmbeddingService",
    "EmbeddingServiceProtocol",
    "OllamaEmbeddingService",
    "normalize_vector",
]
