"""Unit tests for Trafilatura web content extractor.

Tests extraction workflow, error handling, and title extraction strategies.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.exceptions import JinaReaderError
from app.shared.services.extraction.trafilatura_extractor import TrafilaturaExtractor


class TestTrafilaturaExtractorSuccess:
    """Tests for successful content extraction scenarios."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_extract_article_success(self, extractor: TrafilaturaExtractor) -> None:
        """Test successful article extraction with valid content.

        Mocks trafilatura.fetch_url and extract to return valid content,
        verifying the full extraction pipeline.
        """
        # Arrange - mock trafilatura responses
        mock_html = "<html><body><article>Sample article content</article></body></html>"
        mock_markdown = "# Article Title\n\nSample article content with insights."

        # Mock metadata object with title attribute
        mock_metadata = Mock()
        mock_metadata.title = "Article Title"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_markdown
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["title"] == "Article Title"
            assert result["content"] == mock_markdown
            assert result["word_count"] == len(mock_markdown.split())
            assert result["metadata"]["extractor"] == "trafilatura"
            assert result["metadata"]["source_url"] == "https://example.com/article"
            assert result["metadata"]["has_metadata"] is True

            # Verify trafilatura calls
            mock_fetch.assert_called_once_with("https://example.com/article")
            mock_extract.assert_called_once_with(
                mock_html,
                favor_recall=True,
                include_comments=False,
                include_tables=True,
                include_images=False,
                include_links=False,
                output_format="markdown",
            )
            mock_extract_metadata.assert_called_once_with(mock_html)


class TestTrafilaturaExtractorErrors:
    """Tests for error handling in extraction pipeline."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_extract_article_download_failure(self, extractor: TrafilaturaExtractor) -> None:
        """Test extraction fails when fetch_url returns None.

        Simulates network errors or invalid URLs that prevent content download.
        """
        # Arrange - mock fetch_url returning None (download failure)
        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch:
            mock_fetch.return_value = None

            # Act & Assert
            with pytest.raises(JinaReaderError, match="Failed to download content from"):
                await extractor.extract_article("https://invalid-url.com")

            mock_fetch.assert_called_once_with("https://invalid-url.com")

    @pytest.mark.asyncio
    async def test_extract_article_no_content(self, extractor: TrafilaturaExtractor) -> None:
        """Test extraction fails when extract returns None.

        Simulates pages with no extractable content (e.g., pure JavaScript sites,
        pages with only images, etc.).
        """
        # Arrange - mock successful download but no extractable content
        mock_html = "<html><body><div>No article content here</div></body></html>"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract:
            mock_fetch.return_value = mock_html
            # Both markdown and txt extraction return None
            mock_extract.return_value = None

            # Act & Assert
            with pytest.raises(JinaReaderError, match="No content extracted from"):
                await extractor.extract_article("https://example.com/no-content")

            # Verify extract was called twice (markdown, then txt)
            assert mock_extract.call_count == 2
            # First call: markdown format
            assert mock_extract.call_args_list[0][1]["output_format"] == "markdown"
            # Second call: txt format (fallback)
            assert mock_extract.call_args_list[1][1]["output_format"] == "txt"


class TestTrafilaturaExtractorTitleExtraction:
    """Tests for title extraction strategies."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_extract_article_title_from_metadata(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test title extracted from metadata.title attribute.

        Trafilatura's extract_metadata returns a Document object with a title attribute.
        This is the preferred source for article titles.
        """
        # Arrange
        mock_html = "<html><head><title>Metadata Title</title></head></html>"
        mock_content = "Article content without heading"

        # Mock metadata object with title attribute
        mock_metadata = Mock()
        mock_metadata.title = "Metadata Title"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["title"] == "Metadata Title"

    @pytest.mark.asyncio
    async def test_extract_article_title_from_heading(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test title extracted from markdown # heading.

        If metadata doesn't contain a title, falls back to extracting
        from the first markdown heading in the content.
        """
        # Arrange - no metadata title
        mock_html = "<html><body><h1>Heading Title</h1><p>Content</p></body></html>"
        mock_content = "# Heading Title\n\nArticle content here."

        # Mock metadata without title
        mock_metadata = Mock()
        mock_metadata.title = None  # No title in metadata

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["title"] == "Heading Title"

    @pytest.mark.asyncio
    async def test_extract_article_title_fallback_untitled(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test title defaults to 'Untitled' when no title found.

        If neither metadata nor markdown headings contain a title,
        defaults to 'Untitled'.
        """
        # Arrange - no metadata title, no markdown heading
        mock_html = "<html><body><p>Content without title</p></body></html>"
        mock_content = "Article content without any heading."

        # Mock metadata without title
        mock_metadata = Mock()
        mock_metadata.title = None

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["title"] == "Untitled"

    @pytest.mark.asyncio
    async def test_extract_article_title_strips_whitespace(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that title is stripped of leading/trailing whitespace."""
        # Arrange - metadata title with whitespace
        mock_html = "<html><body>Content</body></html>"
        mock_content = "Article content"

        mock_metadata = Mock()
        mock_metadata.title = "  Whitespace Title  \n"  # Whitespace around title

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["title"] == "Whitespace Title"  # Stripped

    @pytest.mark.asyncio
    async def test_extract_article_title_from_multiple_hash_heading(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test title extraction from headings with multiple # symbols."""
        # Arrange - content with ## heading
        mock_html = "<html><body>Content</body></html>"
        mock_content = "## Secondary Heading\n\nArticle content here."

        mock_metadata = Mock()
        mock_metadata.title = None

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["title"] == "Secondary Heading"


class TestTrafilaturaExtractorFallback:
    """Tests for markdown-to-text fallback behavior."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_extract_article_fallback_to_txt(self, extractor: TrafilaturaExtractor) -> None:
        """Test extraction falls back to txt format when markdown fails.

        If markdown extraction returns None, tries again with txt format.
        """
        # Arrange
        mock_html = "<html><body><article>Content</article></body></html>"
        mock_txt_content = "Plain text content"

        mock_metadata = Mock()
        mock_metadata.title = "Test Article"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            # First call (markdown) returns None, second call (txt) succeeds
            mock_extract.side_effect = [None, mock_txt_content]
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["content"] == mock_txt_content
            assert result["title"] == "Test Article"

            # Verify extract was called twice
            assert mock_extract.call_count == 2
            # First: markdown
            assert mock_extract.call_args_list[0][1]["output_format"] == "markdown"
            # Second: txt
            assert mock_extract.call_args_list[1][1]["output_format"] == "txt"


class TestTrafilaturaExtractorMetadata:
    """Tests for metadata population."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_extract_article_metadata_complete(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that metadata is correctly populated in extraction result."""
        # Arrange
        mock_html = "<html><body>Content</body></html>"
        mock_content = "# Title\n\nContent with ten words here now complete yes done."

        mock_metadata = Mock()
        mock_metadata.title = "Test Title"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/test-article")

            # Assert
            assert "metadata" in result
            assert result["metadata"]["extractor"] == "trafilatura"
            assert result["metadata"]["source_url"] == "https://example.com/test-article"
            assert result["metadata"]["raw_content_length"] == len(mock_content)
            assert result["metadata"]["cleaned_content_length"] == len(mock_content)
            assert result["metadata"]["has_metadata"] is True

    @pytest.mark.asyncio
    async def test_extract_article_word_count_accurate(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that word_count is accurately calculated from content."""
        # Arrange
        mock_html = "<html><body>Content</body></html>"
        # Content with exactly 10 words
        mock_content = "This is a test article with exactly ten words total."

        mock_metadata = Mock()
        mock_metadata.title = "Test"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["word_count"] == 10


class TestTrafilaturaExtractorLifecycle:
    """Tests for extractor lifecycle methods."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_close_is_noop(self, extractor: TrafilaturaExtractor) -> None:
        """Test that close() method doesn't raise and is a no-op.

        Trafilatura doesn't maintain persistent connections,
        so close() is implemented as a no-op for interface compatibility.
        """
        # Act & Assert - should not raise
        await extractor.close()

        # Verify extractor is still functional after close
        mock_html = "<html><body>Content</body></html>"
        mock_content = "Test content"
        mock_metadata = Mock()
        mock_metadata.title = "Test"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Should work fine after close()
            result = await extractor.extract_article("https://example.com/article")
            assert result["content"] == mock_content


class TestTrafilaturaExtractorEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_extract_article_no_metadata_object(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test extraction when extract_metadata returns None."""
        # Arrange
        mock_html = "<html><body>Content</body></html>"
        mock_content = "# Fallback Title\n\nContent here"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = None  # No metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["title"] == "Fallback Title"  # From markdown heading
            assert result["metadata"]["has_metadata"] is False

    @pytest.mark.asyncio
    async def test_extract_article_empty_title_in_metadata(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test extraction when metadata.title is empty string."""
        # Arrange
        mock_html = "<html><body>Content</body></html>"
        mock_content = "## Heading Title\n\nContent"

        mock_metadata = Mock()
        mock_metadata.title = ""  # Empty title

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            # Empty string becomes falsy after strip(), falls back to heading
            assert result["title"] == "Heading Title"

    @pytest.mark.asyncio
    async def test_extract_article_content_whitespace_stripped(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that extracted content has leading/trailing whitespace stripped."""
        # Arrange
        mock_html = "<html><body>Content</body></html>"
        mock_content = "\n\n  Content with whitespace  \n\n"

        mock_metadata = Mock()
        mock_metadata.title = "Test"

        with patch.object(extractor.trafilatura, "fetch_url") as mock_fetch, patch.object(
            extractor.trafilatura, "extract"
        ) as mock_extract, patch.object(
            extractor.trafilatura, "extract_metadata"
        ) as mock_extract_metadata:
            mock_fetch.return_value = mock_html
            mock_extract.return_value = mock_content
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert
            assert result["content"] == "Content with whitespace"
            assert not result["content"].startswith("\n")
            assert not result["content"].endswith("\n")

    @pytest.mark.asyncio
    async def test_extract_article_exception_wrapped_in_jinareader_error(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that any exception during extraction is wrapped in JinaReaderError."""
        # Arrange - mock unexpected exception
        with patch.object(
            extractor.trafilatura, "fetch_url", side_effect=ValueError("Unexpected error")
        ):
            # Act & Assert
            with pytest.raises(JinaReaderError, match="Trafilatura extraction failed"):
                await extractor.extract_article("https://example.com/article")
