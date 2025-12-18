"""Embedding service module."""

from app.core.exceptions import EmbeddingError
from app.shared.services.embeddings.deterministic import DeterministicEmbeddingService
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.embeddings.utils import normalize_vector

__all__ = [
    "DeterministicEmbeddingService",
    "EmbeddingError",
    "EmbeddingService",
    "normalize_vector",
]
