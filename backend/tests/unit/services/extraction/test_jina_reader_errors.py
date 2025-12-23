"""Unit tests for Jina Reader error handling."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.shared.services.extraction.jina_reader import JinaReader, JinaReaderError


@pytest.fixture
def jina_reader():
    """Create a JinaReader instance."""
    with patch("app.shared.services.extraction.jina_reader.settings") as mock_settings:
        mock_settings.JINA_API_KEY = "test-key"
        return JinaReader()


@pytest.mark.asyncio
async def test_extract_article_404(jina_reader):
    """Test extraction with 404 error raises JinaReaderError."""
    # Mock HTTP client to return 404
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"
    jina_reader.client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(JinaReaderError, match="URL not found \\(404\\)"):
        await jina_reader.extract_article("https://example.com/not-found")


@pytest.mark.asyncio
async def test_extract_article_http_error(jina_reader):
    """Test extraction with HTTP 5xx error raises JinaReaderError."""
    # Mock HTTP client to return 500
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.headers = {}
    jina_reader.client.get = AsyncMock(return_value=mock_response)

    with pytest.raises(JinaReaderError, match="HTTP 500 error"):
        await jina_reader.extract_article("https://example.com/error")


@pytest.mark.asyncio
async def test_extract_article_timeout(jina_reader):
    """Test extraction with timeout raises JinaReaderError."""
    # Mock HTTP client to raise TimeoutException
    jina_reader.client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))

    with pytest.raises(JinaReaderError, match="Request timed out"):
        await jina_reader.extract_article("https://example.com/slow")


@pytest.mark.asyncio
async def test_extract_article_title_extraction(jina_reader):
    """Test title extraction from markdown content."""
    # Mock HTTP client to return markdown with title
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "# Article Title\n\nContent here..."
    jina_reader.client.get = AsyncMock(return_value=mock_response)

    result = await jina_reader.extract_article("https://example.com/article")

    assert result["title"] == "Article Title"
    assert "Content here" in result["content"]


@pytest.mark.asyncio
async def test_extract_article_title_no_header(jina_reader):
    """Test title extraction when no markdown header."""
    # Mock HTTP client to return content without markdown header
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Plain text content without header"
    jina_reader.client.get = AsyncMock(return_value=mock_response)

    result = await jina_reader.extract_article("https://example.com/article")

    # Should use first line as title
    assert result["title"] == "Plain text content without header"


@pytest.mark.asyncio
async def test_extract_article_generic_exception(jina_reader):
    """Test extraction with generic exception raises JinaReaderError."""
    # Mock HTTP client to raise generic exception
    jina_reader.client.get = AsyncMock(side_effect=ValueError("Unexpected error"))

    with pytest.raises(JinaReaderError, match="Extraction failed"):
        await jina_reader.extract_article("https://example.com/article")


@pytest.mark.asyncio
async def test_extract_article_jina_reader_error_re_raised(jina_reader):
    """Test that JinaReaderError is re-raised without modification."""
    # Mock HTTP client to raise JinaReaderError
    original_error = JinaReaderError("Original error")
    jina_reader.client.get = AsyncMock(side_effect=original_error)

    with pytest.raises(JinaReaderError, match="Original error") as exc_info:
        await jina_reader.extract_article("https://example.com/article")

    # Verify it's the same error instance (not wrapped)
    assert exc_info.value is original_error


@pytest.mark.asyncio
async def test_extract_article_retry_on_transient_error(jina_reader):
    """Test that retry logic is triggered on transient errors."""
    # Mock HTTP client to fail first, then succeed
    mock_response_500 = MagicMock()
    mock_response_500.status_code = 500
    mock_response_500.text = "Internal Server Error"
    mock_response_500.headers = {}

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.text = "# Title\nContent"

    jina_reader.client.get = AsyncMock(
        side_effect=[mock_response_500, mock_response_200]  # Fail once, then succeed
    )

    # Should retry and eventually succeed
    result = await jina_reader.extract_article("https://example.com/article")

    assert result["title"] == "Title"
    # Should have been called twice (retry)
    assert jina_reader.client.get.call_count == 2
