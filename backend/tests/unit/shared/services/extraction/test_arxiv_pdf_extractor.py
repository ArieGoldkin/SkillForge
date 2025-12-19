"""Unit tests for ArXiv PDF extractor.

Tests UTF-8 sanitization in PDF content extraction pipeline.
"""

from unittest.mock import Mock, patch

import pytest
from pypdf import PdfReader

from app.shared.services.extraction.arxiv_pdf_extractor import ArxivPDFExtractor


class TestArxivPDFExtractorUtf8Sanitization:
    """Tests for UTF-8 sanitization in ArXiv PDF extraction."""

    @pytest.fixture
    def extractor(self) -> ArxivPDFExtractor:
        """Create ArxivPDFExtractor instance."""
        return ArxivPDFExtractor()

    def test_clean_pdf_content_removes_null_bytes(self, extractor: ArxivPDFExtractor) -> None:
        """Test that _clean_pdf_content removes null bytes."""
        # Arrange - PDF content with null bytes (common in PDFs)
        content_with_nulls = (
            "Abstract\x00: This paper discusses RAG retrieval.\n"
            "Introduction\x00\n\n"
            "The main contribution\x00 is a novel approach.\n"
        )

        # Act
        result = extractor._clean_pdf_content(content_with_nulls)

        # Assert
        assert "\x00" not in result
        assert "Abstract: This paper discusses RAG retrieval." in result
        assert "The main contribution is a novel approach." in result

    def test_clean_pdf_content_logs_null_byte_warning(
        self,
        extractor: ArxivPDFExtractor,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that null byte detection logs warning."""
        # Arrange
        content_with_nulls = "Text\x00with\x00null\x00bytes"

        # Act
        with caplog.at_level("WARNING"):
            result = extractor._clean_pdf_content(content_with_nulls)

        # Assert
        assert "\x00" not in result
        assert "Textwithnullbytes" in result
        assert any("pdf_null_bytes_detected" in record.message for record in caplog.records)

    def test_clean_pdf_content_preserves_valid_content(
        self, extractor: ArxivPDFExtractor
    ) -> None:
        """Test that _clean_pdf_content preserves normal text."""
        # Arrange - clean content without null bytes
        clean_content = (
            "arXiv:2512.08296v1 [cs.AI] 11 Dec 2024\n\n"
            "Efficient RAG Retrieval\n\n"
            "Abstract: This paper discusses vector databases.\n\n"
            "1 Introduction\n\n"
            "Retrieval-Augmented Generation (RAG) has become...\n"
        )

        # Act
        result = extractor._clean_pdf_content(clean_content)

        # Assert
        assert "Efficient RAG Retrieval" in result
        assert "Abstract: This paper discusses vector databases." in result
        assert "Retrieval-Augmented Generation (RAG) has become" in result

    def test_clean_pdf_content_handles_ligatures(self, extractor: ArxivPDFExtractor) -> None:
        """Test that ligatures are properly replaced."""
        # Arrange - PDF content with common ligatures (ff, fi, fl)
        content_with_ligatures = (
            "E\ufb00ective algorithms\n"  # ff ligature
            "The \ufb01rst \ufb01nding\n"  # fi ligature (twice)
            "In\ufb02uence and bene\ufb01ts\n"  # fl and fi ligatures
        )

        # Act
        result = extractor._clean_pdf_content(content_with_ligatures)

        # Assert
        assert "Effective algorithms" in result
        assert "The first finding" in result
        assert "Influence and benefits" in result
        # Original ligatures should be replaced
        assert "\ufb00" not in result  # ff
        assert "\ufb01" not in result  # fi
        assert "\ufb02" not in result  # fl

    def test_clean_pdf_content_removes_excessive_whitespace(
        self, extractor: ArxivPDFExtractor
    ) -> None:
        """Test that excessive newlines are reduced."""
        # Arrange
        content_with_whitespace = (
            "Section 1\n\n\n\n\nSection 2\n\n\n\n\n\nSection 3"
        )

        # Act
        result = extractor._clean_pdf_content(content_with_whitespace)

        # Assert
        # Should reduce to at most 2 consecutive newlines
        assert "\n\n\n" not in result
        assert "Section 1\n\nSection 2\n\nSection 3" in result

    def test_clean_pdf_content_fixes_hyphenation(self, extractor: ArxivPDFExtractor) -> None:
        """Test that line-break hyphenation is fixed."""
        # Arrange - words broken across lines with hyphens
        content_with_hyphens = (
            "This is an exam-\nple of hyphen-\nation at line\nbreaks."
        )

        # Act
        result = extractor._clean_pdf_content(content_with_hyphens)

        # Assert
        assert "example" in result
        assert "hyphenation" in result
        assert "exam-\nple" not in result
        assert "hyphen-\nation" not in result

    def test_clean_pdf_content_combined_artifacts(
        self, extractor: ArxivPDFExtractor
    ) -> None:
        """Test cleaning with multiple PDF artifacts combined."""
        # Arrange - realistic PDF content with multiple issues
        # Note: Using ff/fi/fl ligatures which are actually replaced by the code
        messy_pdf_content = (
            "E\ufb00icient RAG Re-\ntrieval\n\n\n\n"  # ff ligature + hyphenation
            "Abstract\x00: This paper\x00 discusses vector\n"
            "data-\nbases for semantic search.\n\n"
            "1 Introduction\n\n"
            "The \ufb01rst contribution\x00 is...\n"  # fi ligature + null byte
        )

        # Act
        result = extractor._clean_pdf_content(messy_pdf_content)

        # Assert
        assert "\x00" not in result  # Null bytes removed
        assert "\ufb00" not in result  # ff ligature replaced
        assert "\ufb01" not in result  # fi ligature replaced
        assert "Efficient RAG Retrieval" in result  # Ligature + hyphen fixed
        assert "databases" in result  # Hyphenation fixed
        assert "Abstract: This paper discusses" in result
        assert "\n\n\n" not in result  # Excessive whitespace reduced


class TestArxivPDFExtractorIntegration:
    """Integration tests for full PDF extraction with sanitization."""

    @pytest.fixture
    def extractor(self) -> ArxivPDFExtractor:
        """Create ArxivPDFExtractor instance."""
        return ArxivPDFExtractor()

    @pytest.fixture
    def mock_pdf_bytes(self) -> bytes:
        """Create mock PDF bytes for testing.

        Note: This is a simplified mock. Real PDFs would use actual PDF structure.
        """
        # This would need actual PDF bytes for real testing
        # For now, we'll use a placeholder that tests can mock
        return b"Mock PDF content"

    def test_extract_pdf_text_applies_sanitization(self, extractor: ArxivPDFExtractor) -> None:
        """Test that _extract_pdf_text applies UTF-8 sanitization."""
        # Arrange - mock PdfReader to return content with null bytes
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "Page content\x00 with null bytes\n"
            "And some\x00 more text."
        )

        mock_reader = Mock(spec=PdfReader)
        mock_reader.pages = [mock_page]
        mock_reader.metadata = {"/Title": "Test Paper"}

        # Act
        with patch("app.shared.services.extraction.arxiv_pdf_extractor.PdfReader") as MockPdfReader:
            MockPdfReader.return_value = mock_reader
            content, title, page_count = extractor._extract_pdf_text(b"fake pdf bytes", "2512.08296")

        # Assert
        assert "\x00" not in content  # Null bytes should be removed
        assert "Page content with null bytes" in content
        assert "And some more text." in content
        assert title == "Test Paper"
        assert page_count == 1

    def test_extract_pdf_text_preserves_unicode(self, extractor: ArxivPDFExtractor) -> None:
        """Test that legitimate Unicode is preserved during extraction."""
        # Arrange - mock PdfReader with Unicode content
        mock_page = Mock()
        mock_page.extract_text.return_value = (
            "RAG retrieval 🚀\n"
            "检索增强生成 (Retrieval-Augmented Generation)\n"
            "Key findings: 💡\n"
        )

        mock_reader = Mock(spec=PdfReader)
        mock_reader.pages = [mock_page]
        mock_reader.metadata = {"/Title": "RAG Paper"}

        # Act
        with patch("app.shared.services.extraction.arxiv_pdf_extractor.PdfReader") as MockPdfReader:
            MockPdfReader.return_value = mock_reader
            content, title, page_count = extractor._extract_pdf_text(b"fake pdf bytes", "2512.08296")

        # Assert
        assert "🚀" in content
        assert "检索增强生成" in content
        assert "💡" in content
        assert title == "RAG Paper"

    def test_extract_pdf_text_handles_multiple_pages(
        self, extractor: ArxivPDFExtractor
    ) -> None:
        """Test extraction across multiple pages with sanitization."""
        # Arrange - mock multi-page PDF with null bytes
        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Page 1\x00 content"

        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Page 2\x00 content"

        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "Page 3\x00 content"

        mock_reader = Mock(spec=PdfReader)
        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_reader.metadata = {"/Title": "Multi-page Paper"}

        # Act
        with patch("app.shared.services.extraction.arxiv_pdf_extractor.PdfReader") as MockPdfReader:
            MockPdfReader.return_value = mock_reader
            content, title, page_count = extractor._extract_pdf_text(b"fake pdf bytes", "2512.08296")

        # Assert
        assert "\x00" not in content  # All null bytes removed
        assert "[Page 1]" in content
        assert "[Page 2]" in content
        assert "[Page 3]" in content
        assert "Page 1 content" in content
        assert "Page 2 content" in content
        assert "Page 3 content" in content
        assert page_count == 3
