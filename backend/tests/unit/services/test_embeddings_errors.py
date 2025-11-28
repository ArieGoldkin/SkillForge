"""Unit tests for embedding service error handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.embeddings import EmbeddingError, EmbeddingService


@pytest_asyncio.fixture
async def embedding_service():
    """Create an EmbeddingService instance with mocked client."""
    # Mock AsyncOpenAI before service initialization
    with patch("app.services.embeddings.AsyncOpenAI") as mock_openai_class:
        mock_client = MagicMock()
        mock_client.embeddings = MagicMock()
        mock_client.embeddings.create = AsyncMock()
        mock_openai_class.return_value = mock_client

        # Create service (will use mocked AsyncOpenAI)
        # OPENAI_API_KEY is set in environment above
        service = EmbeddingService()
        # Replace client with our mock for easier testing
        service.client = mock_client

        yield service

        # Cleanup
        if hasattr(service, "client") and hasattr(service.client, "close"):
            try:
                await service.close()
            except Exception:
                pass


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(embedding_service):
    """Test embedding generation with empty text raises ValueError."""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await embedding_service.generate_embedding("")


@pytest.mark.asyncio
async def test_generate_embedding_whitespace_only(embedding_service):
    """Test embedding generation with whitespace-only text raises ValueError."""
    with pytest.raises(ValueError, match="Text cannot be empty"):
        await embedding_service.generate_embedding("   \n\t  ")


@pytest.mark.asyncio
async def test_generate_embedding_token_truncation(embedding_service):
    """Test embedding generation with text exceeding token limit."""
    # Create text that exceeds 8000 tokens
    # Each "word " is ~1 token, so 10,000 words = ~10,000 tokens > 8,000 limit
    large_text = "word " * 10_000  # ~10,000 tokens

    # Mock encoding to return more than max_tokens
    mock_tokens = list(range(9000))  # 9000 tokens > 8000 limit
    embedding_service.encoding.encode = MagicMock(return_value=mock_tokens)
    # Mock decode to return truncated text
    truncated_text = "word " * 8_000
    embedding_service.encoding.decode = MagicMock(return_value=truncated_text)

    # Mock successful API response
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    embedding_service.client.embeddings.create = AsyncMock(return_value=mock_response)

    # Should truncate and succeed
    result = await embedding_service.generate_embedding(large_text)

    # Verify truncation occurred
    assert len(result) == 1536
    embedding_service.encoding.decode.assert_called_once()


@pytest.mark.asyncio
async def test_generate_embedding_dimension_mismatch(embedding_service):
    """Test embedding generation with dimension mismatch raises EmbeddingError."""
    # Mock encoding
    embedding_service.encoding.encode = MagicMock(return_value=[1, 2, 3])

    # Mock API response with wrong dimensions
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 512)]  # Wrong dimension (expected 1536)
    embedding_service.client.embeddings.create = AsyncMock(return_value=mock_response)

    with pytest.raises(EmbeddingError, match="Expected 1536 dimensions"):
        await embedding_service.generate_embedding("test text")


@pytest.mark.asyncio
async def test_generate_embedding_missing_embedding(embedding_service):
    """Test embedding generation with missing embedding field raises EmbeddingError."""
    # Mock encoding
    embedding_service.encoding.encode = MagicMock(return_value=[1, 2, 3])

    # Mock API response with empty embedding
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=None)]
    embedding_service.client.embeddings.create = AsyncMock(return_value=mock_response)

    with pytest.raises(EmbeddingError, match="No embedding in API response"):
        await embedding_service.generate_embedding("test text")


@pytest.mark.asyncio
async def test_generate_embedding_api_error(embedding_service):
    """Test embedding generation with API error raises EmbeddingError."""
    # Mock encoding
    embedding_service.encoding.encode = MagicMock(return_value=[1, 2, 3])

    # Mock API to raise an error
    embedding_service.client.embeddings.create = AsyncMock(
        side_effect=Exception("API rate limit exceeded")
    )

    with pytest.raises(EmbeddingError, match="Embedding generation failed"):
        await embedding_service.generate_embedding("test text")


@pytest.mark.asyncio
async def test_generate_embedding_with_normalization(embedding_service):
    """Test embedding generation with normalization enabled."""
    # Mock encoding
    embedding_service.encoding.encode = MagicMock(return_value=[1, 2, 3])

    # Mock API response
    mock_response = MagicMock()
    # Create a non-normalized embedding vector
    embedding_vector = [3.0, 4.0, 0.0] + [0.0] * 1533  # L2 norm = 5.0
    mock_response.data = [MagicMock(embedding=embedding_vector)]
    embedding_service.client.embeddings.create = AsyncMock(return_value=mock_response)

    result = await embedding_service.generate_embedding("test text", normalize=True)

    # Verify result is normalized (L2 norm should be ~1.0)
    import math

    l2_norm = math.sqrt(sum(x * x for x in result))
    assert abs(l2_norm - 1.0) < 0.01  # Allow small floating point error


@pytest.mark.asyncio
async def test_generate_embedding_embedding_error_re_raised(embedding_service):
    """Test that EmbeddingError is re-raised without modification."""
    # Mock encoding
    embedding_service.encoding.encode = MagicMock(return_value=[1, 2, 3])

    # Mock API to raise EmbeddingError
    original_error = EmbeddingError("Original error")
    embedding_service.client.embeddings.create = AsyncMock(side_effect=original_error)

    with pytest.raises(EmbeddingError, match="Original error") as exc_info:
        await embedding_service.generate_embedding("test text")

    # Verify it's the same error instance (not wrapped)
    assert exc_info.value is original_error
