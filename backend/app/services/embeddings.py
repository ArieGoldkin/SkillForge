"""Embedding service for generating vector embeddings.

Placeholder implementation for Task 1.5.2. Full implementation will use
Ollama or OpenAI embeddings service.
"""

from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings.

    Currently returns placeholder embeddings. Full implementation will
    use Ollama or OpenAI to generate real embeddings.

    """

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding vector for text.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding vector

        Note:
            This is a placeholder implementation. Returns a zero vector
            of dimension 1536 (standard embedding size). Full implementation
            will call Ollama or OpenAI embedding API.

        """
        # Placeholder: return zero vector of standard dimension
        # TODO(@yonatan): Implement with Ollama/OpenAI (Task 1.5.2, Issue #5)
        dimension = 1536
        embedding = [0.0] * dimension

        logger.warning(
            "embedding_placeholder_used",
            text_length=len(text),
            dimension=dimension,
        )

        return embedding


# Global service instance
embedding_service = EmbeddingService()
