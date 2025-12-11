"""Unit tests for extract_content task.

Tests verify that title and word_count are correctly included in extraction_metadata.
This addresses Issue #170: Title not persisted from content extraction.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

# Valid UUID for testing
TEST_ANALYSIS_ID = str(uuid.uuid4())


@pytest.fixture
def mock_artifact_store():
    """Mock the artifact store to prevent database calls."""
    with patch("app.workflows.tasks.extract_content._create_artifact_ref") as mock:
        mock.return_value = {
            "uri": "content://test-ref",
            "size_bytes": 1024,
            "summary": "Test summary",
            "sections": [],
        }
        yield mock


@pytest.fixture
def mock_jina_response():
    """Return standard Jina Reader response with title."""
    return {
        "title": "First Steps - FastAPI",
        "content": "The simplest FastAPI file could look like this...",
        "word_count": 150,
        "metadata": {
            "extractor": "jina_reader",
            "source_url": "https://fastapi.tiangolo.com/tutorial/first-steps/",
            "raw_content_length": 14703,
            "cleaned_content_length": 14522,
        },
    }


@pytest.fixture
def mock_emit_event():
    """Mock SSE event emission."""
    with patch(
        "app.workflows.tasks.extract_content.emit_streaming_event", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.mark.asyncio
async def test_extract_content_includes_title_in_metadata(
    mock_jina_response, mock_emit_event, mock_artifact_store
):
    """Test that title from Jina Reader is included in extraction_metadata."""
    with patch("app.workflows.tasks.extract_content.JinaReader") as mock_jina_class:
        # Setup mock
        mock_instance = AsyncMock()
        mock_instance.extract_article.return_value = mock_jina_response
        mock_instance.close = AsyncMock()
        mock_jina_class.return_value = mock_instance

        # Import after patching
        from app.workflows.tasks.extract_content import extract_content

        # Execute
        result = await extract_content(
            url="https://fastapi.tiangolo.com/tutorial/first-steps/",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify title is in extraction_metadata
        assert "extraction_metadata" in result
        assert result["extraction_metadata"]["title"] == "First Steps - FastAPI"


@pytest.mark.asyncio
async def test_extract_content_includes_word_count_in_metadata(
    mock_jina_response, mock_emit_event, mock_artifact_store
):
    """Test that word_count from Jina Reader is included in extraction_metadata."""
    with patch("app.workflows.tasks.extract_content.JinaReader") as mock_jina_class:
        mock_instance = AsyncMock()
        mock_instance.extract_article.return_value = mock_jina_response
        mock_instance.close = AsyncMock()
        mock_jina_class.return_value = mock_instance

        from app.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify word_count is in extraction_metadata
        assert result["extraction_metadata"]["word_count"] == 150


@pytest.mark.asyncio
async def test_extract_content_preserves_original_metadata(
    mock_jina_response, mock_emit_event, mock_artifact_store
):
    """Test that original metadata fields from Jina Reader are preserved."""
    with patch("app.workflows.tasks.extract_content.JinaReader") as mock_jina_class:
        mock_instance = AsyncMock()
        mock_instance.extract_article.return_value = mock_jina_response
        mock_instance.close = AsyncMock()
        mock_jina_class.return_value = mock_instance

        from app.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify original metadata fields are preserved
        metadata = result["extraction_metadata"]
        assert metadata["extractor"] == "jina_reader"
        assert metadata["source_url"] == "https://fastapi.tiangolo.com/tutorial/first-steps/"
        assert metadata["raw_content_length"] == 14703
        assert metadata["cleaned_content_length"] == 14522


@pytest.mark.asyncio
async def test_extract_content_handles_missing_title(mock_emit_event, mock_artifact_store):
    """Test that extraction handles missing title gracefully (returns None)."""
    response_without_title = {
        "content": "Some content without title...",
        "word_count": 50,
        "metadata": {
            "extractor": "jina_reader",
            "source_url": "https://example.com",
        },
    }

    with patch("app.workflows.tasks.extract_content.JinaReader") as mock_jina_class:
        mock_instance = AsyncMock()
        mock_instance.extract_article.return_value = response_without_title
        mock_instance.close = AsyncMock()
        mock_jina_class.return_value = mock_instance

        from app.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Title should be None, not raise an error
        assert result["extraction_metadata"]["title"] is None


@pytest.mark.asyncio
async def test_extract_content_returns_raw_content(
    mock_jina_response, mock_emit_event, mock_artifact_store
):
    """Test that raw_content is correctly returned."""
    with patch("app.workflows.tasks.extract_content.JinaReader") as mock_jina_class:
        mock_instance = AsyncMock()
        mock_instance.extract_article.return_value = mock_jina_response
        mock_instance.close = AsyncMock()
        mock_jina_class.return_value = mock_instance

        from app.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify raw_content is returned
        assert "raw_content" in result
        assert result["raw_content"] == "The simplest FastAPI file could look like this..."
