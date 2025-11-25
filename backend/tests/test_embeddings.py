"""Tests for EmbeddingService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.services.embeddings import EmbeddingError, EmbeddingService
from app.services.embeddings_utils import normalize_vector

# Constants for test assertions
EXPECTED_EMBEDDING_DIMENSIONS = 1536
MAX_TEXT_LENGTH = 32_000
NORMALIZATION_TOLERANCE = 0.0001


@pytest.fixture
def sample_embedding_1536() -> list[float]:
    """Sample 1536-dimensional embedding vector."""
    return [0.1] * 1536


@pytest_asyncio.fixture
async def embedding_service() -> EmbeddingService:
    """Create EmbeddingService instance for testing with proper cleanup."""
    service = EmbeddingService()
    try:
        yield service
    finally:
        await service.close()


@pytest.mark.asyncio
async def test_generate_embedding_success(
    embedding_service: EmbeddingService, sample_embedding_1536: list[float]
) -> None:
    """Test successful embedding generation."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=sample_embedding_1536)]

    with patch.object(
        embedding_service.client.embeddings, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text")

        assert len(result) == EXPECTED_EMBEDDING_DIMENSIONS
        assert all(isinstance(x, float) for x in result)
        # Result is normalized, so values will differ from input
        # Check that it's a valid normalized vector (L2 norm ≈ 1.0)
        norm = sum(x * x for x in result) ** 0.5
        assert abs(norm - 1.0) < NORMALIZATION_TOLERANCE

        # Verify API call
        mock_create.assert_called_once()
        call_args = mock_create.call_args
        assert call_args.kwargs["model"] == "text-embedding-3-small"
        assert call_args.kwargs["input"] == "Sample text"


@pytest.mark.asyncio
async def test_generate_embedding_normalizes_vector(
    embedding_service: EmbeddingService, sample_embedding_1536: list[float]
) -> None:
    """Test that vectors are normalized when normalize=True."""
    # Create a non-normalized vector
    non_normalized = [3.0, 4.0] + [0.0] * 1534
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=non_normalized)]

    with patch.object(
        embedding_service.client.embeddings, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text", normalize=True)

        # Check that vector is normalized (L2 norm = 1.0)
        norm = sum(x * x for x in result) ** 0.5
        assert abs(norm - 1.0) < NORMALIZATION_TOLERANCE


@pytest.mark.asyncio
async def test_generate_embedding_without_normalization(
    embedding_service: EmbeddingService, sample_embedding_1536: list[float]
) -> None:
    """Test that vectors are not normalized when normalize=False."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=sample_embedding_1536)]

    with patch.object(
        embedding_service.client.embeddings, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text", normalize=False)

        # Vector should be unchanged (not normalized)
        assert result == sample_embedding_1536


@pytest.mark.asyncio
async def test_generate_embedding_truncates_long_text(embedding_service: EmbeddingService) -> None:
    """Test that very long text is truncated before sending to OpenAI."""
    long_text = "x" * 50_000  # 50k characters
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]

    with patch.object(
        embedding_service.client.embeddings, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        await embedding_service.generate_embedding(long_text)

        # Verify that truncated text was sent (32,000 chars max)
        call_args = mock_create.call_args
        assert len(call_args.kwargs["input"]) == MAX_TEXT_LENGTH


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(embedding_service: EmbeddingService) -> None:
    """Test that empty text raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        await embedding_service.generate_embedding("")


@pytest.mark.asyncio
async def test_generate_embedding_whitespace_only(embedding_service: EmbeddingService) -> None:
    """Test that whitespace-only text raises ValueError."""
    with pytest.raises(ValueError, match="cannot be empty"):
        await embedding_service.generate_embedding("   ")


@pytest.mark.asyncio
async def test_generate_embedding_api_error(embedding_service: EmbeddingService) -> None:
    """Test handling of API errors from OpenAI."""
    with patch.object(
        embedding_service.client.embeddings, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = Exception("API Error")

        with pytest.raises(EmbeddingError, match="Embedding generation failed"):
            await embedding_service.generate_embedding("Sample text")


@pytest.mark.asyncio
async def test_generate_embedding_missing_embedding_field(
    embedding_service: EmbeddingService,
) -> None:
    """Test handling of missing embedding field in response."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=None)]

    with patch.object(
        embedding_service.client.embeddings, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        with pytest.raises(EmbeddingError, match="No embedding in API response"):
            await embedding_service.generate_embedding("Sample text")


@pytest.mark.asyncio
async def test_generate_embedding_dimension_mismatch(
    embedding_service: EmbeddingService,
) -> None:
    """Test handling of dimension mismatch in response."""
    # OpenAI should always return 1536, but test error handling
    wrong_dimension_embedding = [0.1] * 768
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=wrong_dimension_embedding)]

    with patch.object(
        embedding_service.client.embeddings, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        with pytest.raises(EmbeddingError, match="Expected 1536 dimensions"):
            await embedding_service.generate_embedding("Sample text")


def test_normalize_vector() -> None:
    """Test vector normalization."""
    vector = [3.0, 4.0, 0.0]
    normalized = normalize_vector(vector)

    # Check L2 norm is 1.0
    norm = sum(x * x for x in normalized) ** 0.5
    assert abs(norm - 1.0) < NORMALIZATION_TOLERANCE

    # Check direction is preserved (proportional)
    assert abs(normalized[0] / normalized[1] - 3.0 / 4.0) < NORMALIZATION_TOLERANCE


def test_normalize_zero_vector() -> None:
    """Test that zero vector is returned unchanged."""
    zero_vector = [0.0] * 1536
    result = normalize_vector(zero_vector)

    assert result == zero_vector


@pytest.mark.asyncio
async def test_close_client(embedding_service: EmbeddingService) -> None:
    """Test that client is properly closed."""
    with patch.object(embedding_service.client, "close", new_callable=AsyncMock) as mock_close:
        await embedding_service.close()
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_embedding_service_requires_api_key() -> None:
    """Test that EmbeddingService requires OpenAI API key."""
    with patch("app.services.embeddings.settings") as mock_settings:
        mock_settings.OPENAI_API_KEY = None

        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            EmbeddingService()
