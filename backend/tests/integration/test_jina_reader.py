"""Tests for Jina AI Reader service."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import get_settings
from app.services.extraction.content_type import detect_content_type
from app.services.extraction.jina_reader import JinaReader, JinaReaderError


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample markdown content from Jina Reader."""
    return "# React 19 Features\n\nReact 19 introduces several new features..."


@pytest.fixture
def jina_reader() -> JinaReader:
    """Create JinaReader instance for testing."""
    return JinaReader()


@pytest.mark.asyncio
async def test_extract_article_success(
    jina_reader: JinaReader, sample_markdown_content: str
) -> None:
    """Test successful article extraction."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sample_markdown_content

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await jina_reader.extract_article("https://react.dev")

        assert result["title"] == "React 19 Features"
        assert result["content"] == sample_markdown_content
        assert result["word_count"] > 0
        assert result["metadata"]["extractor"] == "jina_reader"
        assert result["metadata"]["source_url"] == "https://react.dev"

        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "https://r.jina.ai/https://react.dev" in str(call_args[0][0])
        assert call_args[1]["follow_redirects"] is True


@pytest.mark.asyncio
async def test_extract_article_extracts_title(jina_reader: JinaReader) -> None:
    """Test title extraction from markdown."""
    markdown_with_header = "# My Article Title\n\nContent here..."
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = markdown_with_header

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await jina_reader.extract_article("https://example.com")

        assert result["title"] == "My Article Title"


@pytest.mark.asyncio
async def test_extract_article_without_header(jina_reader: JinaReader) -> None:
    """Test title extraction when no markdown header exists."""
    markdown_no_header = "First line as title\n\nContent here..."
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = markdown_no_header

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await jina_reader.extract_article("https://example.com")

        assert result["title"] == "First line as title"


@pytest.mark.asyncio
async def test_extract_article_empty_content(jina_reader: JinaReader) -> None:
    """Test extraction with empty content."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = ""

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        result = await jina_reader.extract_article("https://example.com")

        assert result["title"] == "Untitled"
        assert result["content"] == ""
        assert result["word_count"] == 0


@pytest.mark.asyncio
async def test_extract_article_with_api_key(
    jina_reader: JinaReader, sample_markdown_content: str
) -> None:
    """Test extraction includes Authorization header when API key is present."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sample_markdown_content

    # Set API key
    jina_reader.api_key = "test_api_key_123"

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        await jina_reader.extract_article("https://react.dev")

        # Verify Authorization header was included
        call_args = mock_get.call_args
        headers = call_args[1]["headers"]
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_api_key_123"


@pytest.mark.asyncio
async def test_extract_article_without_api_key(
    jina_reader: JinaReader, sample_markdown_content: str
) -> None:
    """Test extraction works without API key."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = sample_markdown_content

    # Clear API key
    jina_reader.api_key = None

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        await jina_reader.extract_article("https://react.dev")

        # Verify no Authorization header was included
        call_args = mock_get.call_args
        headers = call_args[1].get("headers", {})
        assert "Authorization" not in headers


@pytest.mark.asyncio
async def test_extract_article_404_error(jina_reader: JinaReader) -> None:
    """Test 404 error handling."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Not Found"

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        with pytest.raises(JinaReaderError, match="URL not found"):
            await jina_reader.extract_article("https://nonexistent.com")


@pytest.mark.asyncio
async def test_extract_article_http_error(jina_reader: JinaReader) -> None:
    """Test HTTP error handling for non-404 errors."""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        with pytest.raises(JinaReaderError, match="HTTP 500"):
            await jina_reader.extract_article("https://example.com")


@pytest.mark.asyncio
async def test_extract_article_timeout(jina_reader: JinaReader) -> None:
    """Test timeout error handling."""
    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(JinaReaderError, match="Request timed out"):
            await jina_reader.extract_article("https://example.com")


@pytest.mark.asyncio
async def test_extract_article_generic_error(jina_reader: JinaReader) -> None:
    """Test generic exception handling."""
    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Unexpected error")

        with pytest.raises(JinaReaderError, match="Extraction failed"):
            await jina_reader.extract_article("https://example.com")


@pytest.mark.asyncio
async def test_extract_article_retry_on_failure(jina_reader: JinaReader) -> None:
    """Test retry logic on transient failures."""
    mock_response_success = MagicMock()
    mock_response_success.status_code = 200
    mock_response_success.text = "# Success\n\nContent"

    # First call fails, second succeeds
    mock_response_fail = MagicMock()
    mock_response_fail.status_code = 500
    mock_response_fail.text = "Server Error"

    with patch.object(jina_reader.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [mock_response_fail, mock_response_success]

        result = await jina_reader.extract_article("https://example.com")

        # Should succeed after retry
        assert result["title"] == "Success"
        assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_close_client(jina_reader: JinaReader) -> None:
    """Test client closure."""
    with patch.object(jina_reader.client, "aclose", new_callable=AsyncMock) as mock_close:
        await jina_reader.close()
        mock_close.assert_called_once()


def test_detect_content_type_youtube() -> None:
    """Test content type detection for YouTube URLs."""
    assert detect_content_type("https://youtube.com/watch?v=123") == "video"
    assert detect_content_type("https://www.youtube.com/watch?v=123") == "video"
    assert detect_content_type("https://youtu.be/123") == "video"
    assert detect_content_type("https://YOUTUBE.COM/WATCH") == "video"


def test_detect_content_type_github() -> None:
    """Test content type detection for GitHub URLs."""
    assert detect_content_type("https://github.com/user/repo") == "repo"
    assert detect_content_type("https://www.github.com/user/repo") == "repo"
    assert detect_content_type("https://GITHUB.COM/user/repo") == "repo"


def test_detect_content_type_article() -> None:
    """Test content type detection defaults to article."""
    assert detect_content_type("https://react.dev") == "article"
    assert detect_content_type("https://example.com/article") == "article"
    assert detect_content_type("https://medium.com/story") == "article"


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.skipif(
    not get_settings().JINA_API_KEY,
    reason="JINA_API_KEY not set in .env - skipping integration test",
)
async def test_extract_article_real_api() -> None:
    """Integration test with real Jina API (requires API key in .env).

    This test requires:
    - Jina API key configured
    - Network access to jina.ai

    Can take 10-30 seconds due to external API call.
    """
    settings = get_settings()
    reader = JinaReader()
    reader.api_key = settings.JINA_API_KEY

    try:
        result = await reader.extract_article("https://react.dev")

        assert "title" in result
        assert "content" in result
        assert "word_count" in result
        assert "metadata" in result
        assert result["metadata"]["extractor"] == "jina_reader"
        assert len(result["content"]) > 0
    finally:
        await reader.close()
