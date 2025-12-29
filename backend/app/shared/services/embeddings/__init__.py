"""Embedding service module.

Provides multiple embedding implementations:
- EmbeddingService: Production OpenAI embeddings (1536 dims)
- OllamaEmbeddingService: Local Ollama embeddings (768 dims, FREE)
- CachedEmbeddingService: Pre-computed cache with hybrid fallback
- DeterministicEmbeddingService: Hash-based for testing (no semantic understanding)
"""

from app.core.exceptions import EmbeddingError
from app.shared.services.embeddings.cached import CachedEmbeddingService
from app.shared.services.embeddings.deterministic import DeterministicEmbeddingService
from app.shared.services.embeddings.ollama_service import OllamaEmbeddingService
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.embeddings.utils import normalize_vector

__all__ = [
    "CachedEmbeddingService",
    "DeterministicEmbeddingService",
    "EmbeddingError",
    "EmbeddingService",
    "OllamaEmbeddingService",
    "normalize_vector",
]
