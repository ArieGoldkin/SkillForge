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
    with patch("app.domains.analysis.workflows.tasks.extract_content._create_artifact_ref") as mock:
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
        "app.domains.analysis.workflows.tasks.extract_content.emit_streaming_event",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


@pytest.mark.asyncio
async def test_extract_content_includes_title_in_metadata(
    mock_jina_response, mock_emit_event, mock_artifact_store
):
    """Test that title from extractor is included in extraction_metadata."""
    # Mock the fallback function to return Jina response
    with patch(
        "app.domains.analysis.workflows.tasks.extract_content._extract_with_fallback"
    ) as mock_fallback:
        mock_fallback.return_value = mock_jina_response

        # Import after patching
        from app.domains.analysis.workflows.tasks.extract_content import extract_content

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
    """Test that word_count from extractor is included in extraction_metadata."""
    with patch(
        "app.domains.analysis.workflows.tasks.extract_content._extract_with_fallback"
    ) as mock_fallback:
        mock_fallback.return_value = mock_jina_response

        from app.domains.analysis.workflows.tasks.extract_content import extract_content

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
    """Test that original metadata fields from extractor are preserved."""
    with patch(
        "app.domains.analysis.workflows.tasks.extract_content._extract_with_fallback"
    ) as mock_fallback:
        mock_fallback.return_value = mock_jina_response

        from app.domains.analysis.workflows.tasks.extract_content import extract_content

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

    with patch(
        "app.domains.analysis.workflows.tasks.extract_content._extract_with_fallback"
    ) as mock_fallback:
        mock_fallback.return_value = response_without_title

        from app.domains.analysis.workflows.tasks.extract_content import extract_content

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
    with patch(
        "app.domains.analysis.workflows.tasks.extract_content._extract_with_fallback"
    ) as mock_fallback:
        mock_fallback.return_value = mock_jina_response

        from app.domains.analysis.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify raw_content is returned
        assert "raw_content" in result
        assert result["raw_content"] == "The simplest FastAPI file could look like this..."


@pytest.mark.asyncio
async def test_extract_content_uses_trafilatura_first(mock_emit_event, mock_artifact_store):
    """Test that Trafilatura is tried first for standard URLs."""
    trafilatura_response = {
        "title": "Test Article",
        "content": "This is a test article with sufficient content. " * 100,  # ~600 words
        "word_count": 600,
        "metadata": {
            "extractor": "trafilatura",
            "source_url": "https://example.com/article",
        },
    }

    with (
        patch(
            "app.domains.analysis.workflows.tasks.extract_content.TrafilaturaExtractor"
        ) as mock_trafilatura_class,
        patch("app.domains.analysis.workflows.tasks.extract_content.JinaReader") as mock_jina_class,
    ):
        # Setup Trafilatura mock
        mock_trafilatura_instance = AsyncMock()
        mock_trafilatura_instance.extract_article.return_value = trafilatura_response
        mock_trafilatura_instance.close = AsyncMock()
        mock_trafilatura_class.return_value = mock_trafilatura_instance

        # Setup Jina mock (should not be called)
        mock_jina_instance = AsyncMock()
        mock_jina_class.return_value = mock_jina_instance

        from app.domains.analysis.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com/article",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify Trafilatura was called
        mock_trafilatura_instance.extract_article.assert_called_once_with(
            "https://example.com/article"
        )

        # Verify Jina was NOT called (fallback not needed)
        mock_jina_instance.extract_article.assert_not_called()

        # Verify result from Trafilatura
        assert result["extraction_metadata"]["extractor"] == "trafilatura"
        assert result["extraction_metadata"]["word_count"] == 600


@pytest.mark.asyncio
async def test_extract_content_falls_back_to_jina_on_low_content(
    mock_emit_event, mock_artifact_store
):
    """Test that extraction falls back to Jina when Trafilatura returns low content."""
    trafilatura_low_content = {
        "title": "Short Article",
        "content": "Too short.",
        "word_count": 2,
        "metadata": {"extractor": "trafilatura"},
    }

    jina_response = {
        "title": "Full Article",
        "content": "Full article content with more details. " * 100,
        "word_count": 600,
        "metadata": {"extractor": "jina_reader"},
    }

    with (
        patch(
            "app.domains.analysis.workflows.tasks.extract_content.TrafilaturaExtractor"
        ) as mock_trafilatura_class,
        patch("app.domains.analysis.workflows.tasks.extract_content.JinaReader") as mock_jina_class,
    ):
        # Trafilatura returns low content
        mock_trafilatura_instance = AsyncMock()
        mock_trafilatura_instance.extract_article.return_value = trafilatura_low_content
        mock_trafilatura_instance.close = AsyncMock()
        mock_trafilatura_class.return_value = mock_trafilatura_instance

        # Jina returns full content
        mock_jina_instance = AsyncMock()
        mock_jina_instance.extract_article.return_value = jina_response
        mock_jina_instance.close = AsyncMock()
        mock_jina_class.return_value = mock_jina_instance

        from app.domains.analysis.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com/spa-page",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify both extractors were called
        mock_trafilatura_instance.extract_article.assert_called_once()
        mock_jina_instance.extract_article.assert_called_once()

        # Verify fallback metadata was added
        metadata = result["extraction_metadata"]
        assert metadata["used_fallback"] is True
        assert metadata["primary_extractor"] == "trafilatura"
        assert metadata["fallback_extractor"] == "jina"


@pytest.mark.asyncio
async def test_extract_content_falls_back_to_jina_on_trafilatura_error(
    mock_emit_event, mock_artifact_store
):
    """Test that extraction falls back to Jina when Trafilatura fails."""
    jina_response = {
        "title": "Article Title",
        "content": "Article content from Jina fallback. " * 100,
        "word_count": 600,
        "metadata": {"extractor": "jina_reader"},
    }

    with (
        patch(
            "app.domains.analysis.workflows.tasks.extract_content.TrafilaturaExtractor"
        ) as mock_trafilatura_class,
        patch("app.domains.analysis.workflows.tasks.extract_content.JinaReader") as mock_jina_class,
    ):
        # Trafilatura raises exception
        mock_trafilatura_instance = AsyncMock()
        mock_trafilatura_instance.extract_article.side_effect = Exception("Trafilatura failed")
        mock_trafilatura_instance.close = AsyncMock()
        mock_trafilatura_class.return_value = mock_trafilatura_instance

        # Jina succeeds
        mock_jina_instance = AsyncMock()
        mock_jina_instance.extract_article.return_value = jina_response
        mock_jina_instance.close = AsyncMock()
        mock_jina_class.return_value = mock_jina_instance

        from app.domains.analysis.workflows.tasks.extract_content import extract_content

        result = await extract_content(
            url="https://example.com/article",
            analysis_id=TEST_ANALYSIS_ID,
        )

        # Verify Trafilatura was attempted
        mock_trafilatura_instance.extract_article.assert_called_once()

        # Verify Jina was called as fallback
        mock_jina_instance.extract_article.assert_called_once()

        # Verify fallback metadata
        metadata = result["extraction_metadata"]
        assert metadata["used_fallback"] is True
        assert metadata["primary_extractor"] == "trafilatura"
        assert metadata["fallback_extractor"] == "jina"
