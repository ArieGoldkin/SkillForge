"""Tests for EmbeddingService."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.embeddings import EmbeddingError, EmbeddingService

# Constants for test assertions
EXPECTED_EMBEDDING_DIMENSIONS = 768
MAX_TEXT_LENGTH = 8000
NORMALIZATION_TOLERANCE = 0.0001


@pytest.fixture
def sample_embedding_768() -> list[float]:
    """Sample 768-dimensional embedding vector."""
    return [0.1] * 768


@pytest.fixture
def sample_embedding_1536() -> list[float]:
    """Sample 1536-dimensional embedding vector (for testing truncation)."""
    return [0.1] * 1536


@pytest.fixture
def sample_embedding_512() -> list[float]:
    """Sample 512-dimensional embedding vector (for testing padding)."""
    return [0.1] * 512


@pytest.fixture
def embedding_service() -> EmbeddingService:
    """Create EmbeddingService instance for testing."""
    return EmbeddingService()


@pytest.mark.asyncio
async def test_generate_embedding_success(
    embedding_service: EmbeddingService, sample_embedding_768: list[float]
) -> None:
    """Test successful embedding generation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": sample_embedding_768}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text")

        assert len(result) == EXPECTED_EMBEDDING_DIMENSIONS
        assert all(isinstance(x, float) for x in result)
        # Result is normalized, so values will differ from input
        # Check that it's a valid normalized vector (L2 norm ≈ 1.0)
        norm = sum(x * x for x in result) ** 0.5
        assert abs(norm - 1.0) < NORMALIZATION_TOLERANCE

        # Verify API call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["json"]["model"] == "nomic-embed-text"
        assert call_args[1]["json"]["prompt"] == "Sample text"


@pytest.mark.asyncio
async def test_generate_embedding_truncates_large_embedding(
    embedding_service: EmbeddingService, sample_embedding_1536: list[float]
) -> None:
    """Test that embeddings larger than expected are truncated."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": sample_embedding_1536}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text", normalize=False)

        assert len(result) == EXPECTED_EMBEDDING_DIMENSIONS
        assert result == sample_embedding_1536[:EXPECTED_EMBEDDING_DIMENSIONS]


@pytest.mark.asyncio
async def test_generate_embedding_pads_small_embedding(
    embedding_service: EmbeddingService, sample_embedding_512: list[float]
) -> None:
    """Test that embeddings smaller than expected are padded with zeros."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": sample_embedding_512}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text", normalize=False)

        assert len(result) == EXPECTED_EMBEDDING_DIMENSIONS
        assert result[:512] == sample_embedding_512
        assert all(x == 0.0 for x in result[512:])


@pytest.mark.asyncio
async def test_generate_embedding_normalizes_vector(
    embedding_service: EmbeddingService, sample_embedding_768: list[float]
) -> None:
    """Test that vectors are normalized when normalize=True."""
    # Create a non-normalized vector
    non_normalized = [3.0, 4.0] + [0.0] * 766
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": non_normalized}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text", normalize=True)

        # Check that vector is normalized (L2 norm = 1.0)
        norm = sum(x * x for x in result) ** 0.5
        assert abs(norm - 1.0) < NORMALIZATION_TOLERANCE


@pytest.mark.asyncio
async def test_generate_embedding_without_normalization(
    embedding_service: EmbeddingService, sample_embedding_768: list[float]
) -> None:
    """Test that vectors are not normalized when normalize=False."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": sample_embedding_768}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await embedding_service.generate_embedding("Sample text", normalize=False)

        # Vector should be unchanged (not normalized)
        assert result == sample_embedding_768


@pytest.mark.asyncio
async def test_generate_embedding_truncates_long_text(embedding_service: EmbeddingService) -> None:
    """Test that very long text is truncated before sending to Ollama."""
    long_text = "x" * 10000  # 10k characters
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": [0.1] * 768}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        await embedding_service.generate_embedding(long_text)

        # Verify that truncated text was sent (8000 chars max)
        call_args = mock_post.call_args
        assert len(call_args[1]["json"]["prompt"]) == MAX_TEXT_LENGTH


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
async def test_generate_embedding_http_error(embedding_service: EmbeddingService) -> None:
    """Test handling of HTTP errors from Ollama."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingError, match="HTTP 500"):
            await embedding_service.generate_embedding("Sample text")


@pytest.mark.asyncio
async def test_generate_embedding_timeout(embedding_service: EmbeddingService) -> None:
    """Test handling of timeout errors."""
    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(EmbeddingError, match="timed out"):
            await embedding_service.generate_embedding("Sample text")


@pytest.mark.asyncio
async def test_generate_embedding_missing_embedding_field(
    embedding_service: EmbeddingService,
) -> None:
    """Test handling of missing embedding field in response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"error": "Model not found"}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingError, match="No 'embedding' field"):
            await embedding_service.generate_embedding("Sample text")


@pytest.mark.asyncio
async def test_generate_embedding_invalid_embedding_type(
    embedding_service: EmbeddingService,
) -> None:
    """Test handling of invalid embedding type in response."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": "not a list"}

    with patch.object(embedding_service.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(EmbeddingError, match="Expected list"):
            await embedding_service.generate_embedding("Sample text")


@pytest.mark.asyncio
async def test_normalize_vector(embedding_service: EmbeddingService) -> None:
    """Test vector normalization."""
    vector = [3.0, 4.0, 0.0]
    normalized = embedding_service._normalize_vector(vector)

    # Check L2 norm is 1.0
    norm = sum(x * x for x in normalized) ** 0.5
    assert abs(norm - 1.0) < NORMALIZATION_TOLERANCE

    # Check direction is preserved (proportional)
    assert abs(normalized[0] / normalized[1] - 3.0 / 4.0) < NORMALIZATION_TOLERANCE


@pytest.mark.asyncio
async def test_normalize_zero_vector(embedding_service: EmbeddingService) -> None:
    """Test that zero vector is returned unchanged."""
    zero_vector = [0.0] * 768
    result = embedding_service._normalize_vector(zero_vector)

    assert result == zero_vector


@pytest.mark.asyncio
async def test_close_client(embedding_service: EmbeddingService) -> None:
    """Test that client is properly closed."""
    with patch.object(embedding_service.client, "aclose", new_callable=AsyncMock) as mock_close:
        await embedding_service.close()
        mock_close.assert_called_once()
