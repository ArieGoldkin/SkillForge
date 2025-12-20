"""Utility functions for embedding operations."""

import math

from app.core.logging import get_logger
from app.core.types import EmbeddingVector

logger = get_logger(__name__)


def normalize_vector(vector: EmbeddingVector) -> EmbeddingVector:
    """Apply L2 normalization to vector.

    L2 normalization scales the vector to unit length, which is optimal
    for cosine similarity search with pgvector. This function can be used
    by any embedding service that needs to normalize vectors.

    Args:
        vector: Input vector to normalize

    Returns:
        Normalized vector (L2 norm = 1.0)

    Example:
        >>> vector = [3.0, 4.0, 0.0]
        >>> normalized = normalize_vector(vector)
        >>> # Vector is now unit length: [0.6, 0.8, 0.0]

    """
    # Calculate L2 norm
    norm = math.sqrt(sum(x * x for x in vector))

    # Avoid division by zero
    if norm == 0.0:
        logger.warning("embedding_zero_norm_vector")
        return vector

    # Normalize
    normalized = [x / norm for x in vector]

    return normalized
