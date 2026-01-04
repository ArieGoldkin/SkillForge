"""Unit tests for TrafilaturaExtractor batch extraction and deduplication.

Tests the new batch extraction and content deduplication features.
"""

from unittest.mock import Mock, patch

import pytest

from app.core.exceptions import JinaReaderError
from app.shared.services.extraction.trafilatura_extractor import TrafilaturaExtractor


class TestTrafilaturaExtractorBatch:
    """Tests for batch URL extraction."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_extract_batch_success(self, extractor: TrafilaturaExtractor) -> None:
        """Test successful batch extraction of multiple URLs.

        Verifies that buffered_downloads is called with correct parameters
        and that results are correctly extracted from all URLs.
        """
        # Arrange - mock batch download
        urls = ["https://example.com/1", "https://example.com/2", "https://example.com/3"]

        # Mock HTML for each URL
        mock_html_1 = "<html><body>Article 1</body></html>"
        mock_html_2 = "<html><body>Article 2</body></html>"
        mock_html_3 = "<html><body>Article 3</body></html>"

        # Mock content extraction
        mock_content_1 = "# Title 1\n\nContent 1"
        mock_content_2 = "# Title 2\n\nContent 2"
        mock_content_3 = "# Title 3\n\nContent 3"

        # buffered_downloads returns generator of (url, html) tuples
        mock_downloads = [
            (urls[0], mock_html_1),
            (urls[1], mock_html_2),
            (urls[2], mock_html_3),
        ]

        mock_metadata = Mock()
        mock_metadata.title = None

        with (
            patch(
                "trafilatura.downloads.buffered_downloads", return_value=mock_downloads
            ) as mock_buffered,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_extract.side_effect = [
                mock_content_1,
                mock_content_2,
                mock_content_3,
            ]
            mock_extract_metadata.return_value = mock_metadata

            # Act
            results = await extractor.extract_batch(urls, threads=5)

            # Assert
            assert len(results) == 3
            assert results[0]["title"] == "Title 1"
            assert results[1]["title"] == "Title 2"
            assert results[2]["title"] == "Title 3"
            assert results[0]["content"] == mock_content_1
            assert results[1]["content"] == mock_content_2
            assert results[2]["content"] == mock_content_3

            # Verify buffered_downloads was called correctly
            mock_buffered.assert_called_once_with(urls, download_threads=5)

    @pytest.mark.asyncio
    async def test_extract_batch_partial_failure(self, extractor: TrafilaturaExtractor) -> None:
        """Test batch extraction handles individual URL failures gracefully.

        When some URLs fail to download or extract, successful ones should
        still be returned without raising exceptions.
        """
        # Arrange
        urls = [
            "https://example.com/good1",
            "https://example.com/fail",
            "https://example.com/good2",
        ]

        mock_html_1 = "<html><body>Article 1</body></html>"
        mock_html_2 = "<html><body>Article 2</body></html>"

        # Second URL returns None (download failed)
        mock_downloads = [
            (urls[0], mock_html_1),
            (urls[1], None),  # Download failed
            (urls[2], mock_html_2),
        ]

        mock_content_1 = "# Good Article 1\n\nContent 1"
        mock_content_2 = "# Good Article 2\n\nContent 2"

        mock_metadata = Mock()
        mock_metadata.title = None

        with (
            patch(
                "trafilatura.downloads.buffered_downloads", return_value=mock_downloads
            ) as mock_buffered,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_extract.side_effect = [mock_content_1, mock_content_2]
            mock_extract_metadata.return_value = mock_metadata

            # Act
            results = await extractor.extract_batch(urls, threads=5)

            # Assert - only 2 successful extractions
            assert len(results) == 2
            assert results[0]["title"] == "Good Article 1"
            assert results[1]["title"] == "Good Article 2"

            # Verify buffered_downloads was called
            mock_buffered.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_batch_extraction_error(self, extractor: TrafilaturaExtractor) -> None:
        """Test batch extraction handles extraction errors for individual URLs.

        If _extract_content raises JinaReaderError for a URL,
        it should be logged and skipped without failing the entire batch.
        """
        # Arrange
        urls = ["https://example.com/1", "https://example.com/2"]

        mock_html_1 = "<html><body>Good content</body></html>"
        mock_html_2 = "<html><body>Bad content</body></html>"

        mock_downloads = [(urls[0], mock_html_1), (urls[1], mock_html_2)]

        mock_content = "# Article\n\nContent"
        mock_metadata = Mock()
        mock_metadata.title = None

        with (
            patch(
                "trafilatura.downloads.buffered_downloads", return_value=mock_downloads
            ) as mock_buffered,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            # First extraction succeeds, second returns None (no content)
            mock_extract.side_effect = [mock_content, None, None]
            mock_extract_metadata.return_value = mock_metadata

            # Act
            results = await extractor.extract_batch(urls, threads=5)

            # Assert - only first URL succeeded
            assert len(results) == 1
            assert results[0]["title"] == "Article"

            mock_buffered.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_batch_empty_urls(self, extractor: TrafilaturaExtractor) -> None:
        """Test batch extraction with empty URL list."""
        # Arrange
        urls: list[str] = []

        with patch("trafilatura.downloads.buffered_downloads", return_value=[]) as mock_buffered:
            # Act
            results = await extractor.extract_batch(urls, threads=5)

            # Assert
            assert results == []
            mock_buffered.assert_called_once_with(urls, download_threads=5)

    @pytest.mark.asyncio
    async def test_extract_batch_custom_threads(self, extractor: TrafilaturaExtractor) -> None:
        """Test that custom thread count is passed to buffered_downloads."""
        # Arrange
        urls = ["https://example.com/1"]
        custom_threads = 20

        with patch("trafilatura.downloads.buffered_downloads", return_value=[]) as mock_buffered:
            # Act
            await extractor.extract_batch(urls, threads=custom_threads)

            # Assert
            mock_buffered.assert_called_once_with(urls, download_threads=custom_threads)

    @pytest.mark.asyncio
    async def test_extract_batch_buffered_downloads_exception(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test batch extraction when buffered_downloads raises exception.

        If the batch download itself fails (not individual URLs),
        the entire operation should raise JinaReaderError.
        """
        # Arrange
        urls = ["https://example.com/1"]

        with patch(
            "trafilatura.downloads.buffered_downloads",
            side_effect=RuntimeError("Network error"),
        ):
            # Act & Assert
            with pytest.raises(JinaReaderError, match="Trafilatura batch extraction failed"):
                await extractor.extract_batch(urls, threads=5)


class TestTrafilaturaExtractorDeduplication:
    """Tests for content deduplication using Simhash."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    def test_deduplicate_content_all_unique(self, extractor: TrafilaturaExtractor) -> None:
        """Test deduplication when all content is unique.

        All items should be returned with their original indices.
        """
        # Arrange
        contents = [
            "This is article A about topic X",
            "This is article B about topic Y",
            "This is article C about topic Z",
        ]

        # Mock Simhash to return different hashes for each content
        with patch("trafilatura.deduplication.Simhash") as mock_simhash:
            mock_instances = [Mock(value=1), Mock(value=2), Mock(value=3)]
            mock_simhash.side_effect = mock_instances

            # Act
            unique = extractor.deduplicate_content(contents)

            # Assert
            assert len(unique) == 3
            assert unique[0] == (0, contents[0])
            assert unique[1] == (1, contents[1])
            assert unique[2] == (2, contents[2])

    def test_deduplicate_content_exact_duplicates(self, extractor: TrafilaturaExtractor) -> None:
        """Test deduplication with exact duplicate content.

        Only the first occurrence of each duplicate should be kept.
        """
        # Arrange
        contents = [
            "Article A content here",
            "Article B content here",
            "Article A content here",  # Duplicate of index 0
        ]

        # Mock Simhash - first and third have same hash
        with patch("trafilatura.deduplication.Simhash") as mock_simhash:
            mock_instances = [Mock(value=100), Mock(value=200), Mock(value=100)]
            mock_simhash.side_effect = mock_instances

            # Act
            unique = extractor.deduplicate_content(contents)

            # Assert
            assert len(unique) == 2
            assert unique[0] == (0, contents[0])
            assert unique[1] == (1, contents[1])
            # Index 2 should be filtered out as duplicate

    def test_deduplicate_content_multiple_duplicates(self, extractor: TrafilaturaExtractor) -> None:
        """Test deduplication with multiple sets of duplicates."""
        # Arrange
        contents = [
            "Article A",
            "Article B",
            "Article A",  # Dup of 0
            "Article C",
            "Article B",  # Dup of 1
            "Article A",  # Dup of 0
        ]

        # Mock Simhash - duplicates have same hashes
        with patch("trafilatura.deduplication.Simhash") as mock_simhash:
            mock_instances = [
                Mock(value=1),
                Mock(value=2),
                Mock(value=1),  # Dup
                Mock(value=3),
                Mock(value=2),  # Dup
                Mock(value=1),  # Dup
            ]
            mock_simhash.side_effect = mock_instances

            # Act
            unique = extractor.deduplicate_content(contents)

            # Assert
            assert len(unique) == 3
            assert unique[0] == (0, "Article A")
            assert unique[1] == (1, "Article B")
            assert unique[2] == (3, "Article C")

    def test_deduplicate_content_empty_list(self, extractor: TrafilaturaExtractor) -> None:
        """Test deduplication with empty content list."""
        # Arrange
        contents: list[str] = []

        # Act
        unique = extractor.deduplicate_content(contents)

        # Assert
        assert unique == []

    def test_deduplicate_content_single_item(self, extractor: TrafilaturaExtractor) -> None:
        """Test deduplication with single content item."""
        # Arrange
        contents = ["Single article content"]

        with patch("trafilatura.deduplication.Simhash") as mock_simhash:
            mock_simhash.return_value = Mock(value=12345)

            # Act
            unique = extractor.deduplicate_content(contents)

            # Assert
            assert len(unique) == 1
            assert unique[0] == (0, contents[0])

    def test_deduplicate_content_preserves_first_occurrence(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that deduplication keeps the first occurrence of duplicates.

        When content appears multiple times, the original index should be
        from the first occurrence.
        """
        # Arrange
        contents = [
            "First version",
            "Duplicate content",
            "Another article",
            "Duplicate content",  # Dup of index 1
            "Last article",
        ]

        with patch("trafilatura.deduplication.Simhash") as mock_simhash:
            mock_instances = [
                Mock(value=1),
                Mock(value=2),
                Mock(value=3),
                Mock(value=2),  # Same as index 1
                Mock(value=4),
            ]
            mock_simhash.side_effect = mock_instances

            # Act
            unique = extractor.deduplicate_content(contents)

            # Assert
            assert len(unique) == 4
            # Index 1 appears (not index 3)
            assert (1, "Duplicate content") in unique
            assert (3, "Duplicate content") not in unique


class TestTrafilaturaExtractorBatchWithDeduplication:
    """Integration tests combining batch extraction and deduplication."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_batch_then_deduplicate_workflow(self, extractor: TrafilaturaExtractor) -> None:
        """Test typical workflow: batch extract then deduplicate.

        Simulates extracting multiple URLs then removing duplicates.
        """
        # Arrange - URLs that might have duplicate content
        urls = [
            "https://example.com/article1",
            "https://example.com/article2",
            "https://example.com/article1-copy",  # Same content as article1
        ]

        mock_html_1 = "<html><body>Article 1</body></html>"
        mock_html_2 = "<html><body>Article 2</body></html>"
        mock_html_3 = "<html><body>Article 1</body></html>"  # Duplicate

        mock_downloads = [
            (urls[0], mock_html_1),
            (urls[1], mock_html_2),
            (urls[2], mock_html_3),
        ]

        mock_content_1 = "# Title A\n\nUnique content A"
        mock_content_2 = "# Title B\n\nUnique content B"
        mock_content_3 = "# Title A\n\nUnique content A"  # Duplicate of 1

        mock_metadata = Mock()
        mock_metadata.title = None

        with (
            patch("trafilatura.downloads.buffered_downloads", return_value=mock_downloads),
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_extract.side_effect = [
                mock_content_1,
                mock_content_2,
                mock_content_3,
            ]
            mock_extract_metadata.return_value = mock_metadata

            # Act - batch extract
            results = await extractor.extract_batch(urls)

            # Extract content strings from results
            content_strings = [result["content"] for result in results]

            # Deduplicate
            with patch("trafilatura.deduplication.Simhash") as mock_simhash:
                # First and third have same hash (duplicates)
                mock_instances = [Mock(value=100), Mock(value=200), Mock(value=100)]
                mock_simhash.side_effect = mock_instances

                unique = extractor.deduplicate_content(content_strings)

            # Assert
            assert len(results) == 3  # All URLs extracted successfully
            assert len(unique) == 2  # Only 2 unique contents
            assert unique[0] == (0, mock_content_1)
            assert unique[1] == (1, mock_content_2)
            # Index 2 filtered as duplicate
