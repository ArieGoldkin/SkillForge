"""Unit tests for UTF-8 sanitization across extraction pipeline.

Tests the full flow: extraction → sanitization → storage prep using mocked extractors.
Note: clean_extracted_content() is deprecated - TrafilaturaExtractor handles cleaning during extraction.

These are unit tests (using mocks), not integration tests.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.shared.services.extraction.arxiv_pdf_extractor import ArxivPDFExtractor
from app.shared.services.extraction.content_cleaner import sanitize_utf8
from app.shared.services.extraction.jina_reader import JinaReader
from app.shared.services.extraction.trafilatura_extractor import TrafilaturaExtractor


class TestTrafilaturaExtractionPipeline:
    """Tests for TrafilaturaExtractor pipeline with UTF-8 sanitization."""

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_trafilatura_extraction_to_storage_pipeline(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test Trafilatura extraction produces PostgreSQL-compatible output.

        Trafilatura performs ML-based cleaning during extraction and sanitize_utf8()
        is applied in the extraction pipeline.
        """
        # Arrange - HTML with null bytes and boilerplate
        html_with_issues = """
        <html>
            <body>
                <article>
                    <h1>Technical Article</h1>
                    <p>This article discusses RAG.</p>
                    <p>Key points:</p>
                    <ul>
                        <li>Vector databases</li>
                        <li>Semantic search</li>
                    </ul>
                </article>
                <div class="cookie-consent">We use cookies.</div>
                <footer>© 2024 All rights reserved.</footer>
            </body>
        </html>
        """
        # Trafilatura extracts clean content (boilerplate removed)
        extracted_markdown = (
            "# Technical Article\n\n"
            "This article discusses RAG.\n\n"
            "Key points:\n"
            "- Vector databases\n"
            "- Semantic search\n"
        )

        mock_metadata = Mock()
        mock_metadata.title = "Technical Article"

        with (
            patch.object(extractor.trafilatura, "fetch_url") as mock_fetch,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_fetch.return_value = html_with_issues
            mock_extract.return_value = extracted_markdown
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert - boilerplate removed by Trafilatura, content preserved
            content = result["content"]
            assert isinstance(content, str), "Content should be a string"
            assert "cookie" not in content.lower()
            assert "Technical Article" in content
            assert "Vector databases" in content
            assert "Semantic search" in content

            # Verify it's PostgreSQL-compatible (sanitize_utf8 is applied in pipeline)
            assert "\x00" not in content
            assert all(ord(c) < 0xD800 or ord(c) > 0xDFFF for c in content)  # No surrogates

    @pytest.mark.asyncio
    async def test_trafilatura_unicode_preservation(self, extractor: TrafilaturaExtractor) -> None:
        """Test that legitimate Unicode survives Trafilatura extraction pipeline."""
        # Arrange - HTML with emoji, CJK, and other valid Unicode
        html_with_unicode = """
        <html>
            <body>
                <article>
                    <h1>RAG Tutorial 🚀</h1>
                    <p>This tutorial covers RAG (检索增强生成).</p>
                    <p>Key concepts:</p>
                    <ul>
                        <li>Embeddings 💡</li>
                        <li>Vector DBs 🗄️</li>
                        <li>Retrieval 🔍</li>
                    </ul>
                </article>
                <div class="cookie-consent">Accept cookies.</div>
            </body>
        </html>
        """
        extracted_markdown = (
            "# RAG Tutorial 🚀\n\n"
            "This tutorial covers RAG (检索增强生成).\n\n"
            "Key concepts:\n"
            "- Embeddings 💡\n"
            "- Vector DBs 🗄️\n"
            "- Retrieval 🔍\n"
        )

        mock_metadata = Mock()
        mock_metadata.title = "RAG Tutorial 🚀"

        with (
            patch.object(extractor.trafilatura, "fetch_url") as mock_fetch,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_fetch.return_value = html_with_unicode
            mock_extract.return_value = extracted_markdown
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert - all legitimate Unicode preserved
            content = result["content"]
            assert isinstance(content, str), "Content should be a string"
            assert "🚀" in content
            assert "检索增强生成" in content
            assert "💡" in content
            assert "🗄️" in content
            assert "🔍" in content
            assert "cookie" not in content.lower()  # Boilerplate removed


class TestJinaReaderSanitization:
    """Tests that JinaReader applies UTF-8 sanitization.

    NOTE: JinaReader no longer uses clean_extracted_content() - only sanitize_utf8().
    """

    @pytest.mark.asyncio
    async def test_jina_reader_sanitizes_content(self) -> None:
        """Test that JinaReader applies sanitize_utf8() to content.

        JinaReader only uses sanitize_utf8() for UTF-8 compatibility,
        not clean_extracted_content() (which is deprecated).
        """
        # Arrange
        reader = JinaReader()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = (
            "# Article Title\n\nContent with\x00 null bytes.\nMore content" + chr(0xFFFE) + ".\n"
        )

        # Act
        with patch.object(reader.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await reader.extract_article("https://example.com/article")

        # Assert - sanitize_utf8() removes invalid characters
        assert "\x00" not in result["content"]
        assert chr(0xFFFE) not in result["content"]
        assert "Article Title" in result["title"]
        assert "Content with null bytes" in result["content"]
        assert "More content" in result["content"]

        # Cleanup
        await reader.close()


class TestArxivPDFExtractorSanitization:
    """Tests that ArxivPDFExtractor applies UTF-8 sanitization."""

    @pytest.mark.asyncio
    async def test_arxiv_extractor_sanitizes_content(self) -> None:
        """Test that ArxivPDFExtractor sanitizes PDF content."""
        # Arrange
        extractor = ArxivPDFExtractor()

        # Mock PDF extraction
        mock_page = Mock()
        # Use ff/fi/fl ligatures which are actually replaced by the code
        mock_page.extract_text.return_value = (
            "E\ufb00icient RAG\x00\n"  # ff ligature + null byte
            "Abstract\x00: Content here.\n"
        )

        mock_reader = Mock()
        mock_reader.pages = [mock_page]
        mock_reader.metadata = {"/Title": "Test Paper"}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake pdf bytes"

        # Act
        with patch(
            "app.shared.services.extraction.arxiv_pdf_extractor.PdfReader"
        ) as mock_pdf_reader:
            mock_pdf_reader.return_value = mock_reader
            with patch.object(extractor.client, "get", new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response
                result = await extractor.extract_article("https://arxiv.org/abs/2512.08296")

        # Assert
        assert "\x00" not in result["content"]
        assert "Abstract: Content here" in result["content"]
        # ff ligature should be replaced by _clean_pdf_content
        assert "Efficient RAG" in result["content"]
        assert "\ufb00" not in result["content"]

        # Cleanup
        await extractor.close()


class TestPostgreSQLCompatibility:
    """Tests that sanitized content is PostgreSQL-compatible."""

    def test_sanitized_content_is_postgresql_compatible(self) -> None:
        """Test that sanitized content can be stored in PostgreSQL text columns."""
        # Arrange - content with all known problematic characters
        problematic_content = (
            "Valid text\x00"  # null byte
            + chr(0xD800)  # low surrogate
            + chr(0xDFFF)  # high surrogate
            + chr(0xFFFE)  # invalid code point
            + chr(0xFFFF)  # invalid code point
            + "More valid text"
        )

        # Act
        sanitized = sanitize_utf8(problematic_content)

        # Assert - verify PostgreSQL-compatible UTF-8
        # 1. No null bytes
        assert "\x00" not in sanitized

        # 2. No UTF-16 surrogates (0xD800-0xDFFF)
        for char in sanitized:
            code_point = ord(char)
            assert not (0xD800 <= code_point <= 0xDFFF)

        # 3. No invalid code points (0xFFFE, 0xFFFF)
        assert chr(0xFFFE) not in sanitized
        assert chr(0xFFFF) not in sanitized

        # 4. Only valid text remains
        assert sanitized == "Valid textMore valid text"

    def test_sanitized_unicode_is_postgresql_compatible(self) -> None:
        """Test that legitimate Unicode remains PostgreSQL-compatible after sanitization."""
        # Arrange - content with legitimate Unicode
        unicode_content = (
            "English text\n"
            "Emoji: 🚀💡🔍\n"
            "CJK: 中文 日本語 한국어\n"
            "Greek: Ελληνικά\n"
            "Arabic: العربية\n"
        )

        # Act
        sanitized = sanitize_utf8(unicode_content)

        # Assert - should be unchanged and PostgreSQL-compatible
        assert sanitized == unicode_content

        # Verify all characters are valid
        for char in sanitized:
            code_point = ord(char)
            # No surrogates
            assert not (0xD800 <= code_point <= 0xDFFF)
            # No null bytes
            assert code_point != 0x00
            # No invalid code points
            assert code_point not in {0xFFFE, 0xFFFF}
