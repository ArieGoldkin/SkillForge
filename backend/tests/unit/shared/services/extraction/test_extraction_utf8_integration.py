"""Integration tests for UTF-8 sanitization across extraction pipeline.

Tests the full flow: extraction → cleaning → sanitization → storage prep.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.shared.services.extraction.arxiv_pdf_extractor import ArxivPDFExtractor
from app.shared.services.extraction.content_cleaner import clean_extracted_content, sanitize_utf8
from app.shared.services.extraction.jina_reader import JinaReader


class TestFullExtractionPipeline:
    """Tests for complete extraction pipeline with UTF-8 sanitization."""

    def test_extraction_to_storage_pipeline(self) -> None:
        """Test content flows through extraction → cleaning → sanitization → storage prep."""
        # Arrange - simulate raw extraction with null bytes and boilerplate
        raw_extraction = (
            "# Technical Article\n\n"
            "This article\x00 discusses RAG.\n\n"
            "Key points:\n"
            "- Vector databases" + chr(0xD800) + "\n"  # surrogate
            "- Semantic search" + chr(0xFFFE) + "\n"  # invalid code point
            "\n\n"
            "Cookie consent: We use cookies.\n"
            "Footer: © 2024 All rights reserved.\n"
        )

        # Act - simulate full pipeline
        # Step 1: Clean extracted content (removes boilerplate)
        cleaned = clean_extracted_content(raw_extraction)

        # Assert - boilerplate removed, invalid UTF-8 removed
        assert "\x00" not in cleaned
        assert chr(0xD800) not in cleaned
        assert chr(0xFFFE) not in cleaned
        assert "cookie" not in cleaned.lower()
        assert "©" not in cleaned
        assert "Technical Article" in cleaned
        assert "Vector databases" in cleaned
        assert "Semantic search" in cleaned

        # Step 2: Verify it's PostgreSQL-compatible
        # Should be able to store this without errors
        assert all(ord(c) < 0xD800 or ord(c) > 0xDFFF for c in cleaned)  # No surrogates
        assert "\x00" not in cleaned  # No null bytes

    def test_arxiv_style_content_pipeline(self) -> None:
        """Test ArXiv-style content with ligatures, null bytes, and PDF artifacts."""
        # Arrange - realistic arXiv PDF content
        arxiv_content = (
            "arXiv:2512.08296v1\x00 [cs.AI] 11 Dec 2024\n\n"
            "E\ufb03cient RAG Retrieval\x00\n\n"  # eff ligature + null
            "Abstract\x00: This paper discusses vector\n"
            "data-\nbases for semantic search.\n\n"  # hyphenation
            "1 Introduction\n\n"
            "The \ufb01rst contribution\x00 is a novel approach.\n"  # fi ligature + null
            "\n\n"
            "Cookie consent: Accept all cookies.\n"
        )

        # Act - full pipeline
        # Step 1: Clean extracted content
        cleaned = clean_extracted_content(arxiv_content)

        # Assert
        assert "\x00" not in cleaned
        assert "cookie" not in cleaned.lower()
        assert "arXiv:2512.08296v1" in cleaned
        # Ligatures are valid Unicode, should be preserved by sanitize_utf8
        # but clean_extracted_content doesn't handle ligatures
        # (that's done in ArxivPDFExtractor._clean_pdf_content)

    def test_jina_extraction_to_storage(self) -> None:
        """Test Jina Reader extraction produces PostgreSQL-compatible output."""
        # Arrange - simulate Jina response with null bytes
        jina_response = (
            "# Article Title\n\n"
            "Content with\x00 null bytes\n\n"
            "More content" + chr(0xFFFE) + "\n\n"
            "Cookie consent: We use cookies.\n"
        )

        # Act - clean_extracted_content is called in JinaReader.extract_article
        cleaned = clean_extracted_content(jina_response)

        # Assert - ready for PostgreSQL storage
        assert "\x00" not in cleaned
        assert chr(0xFFFE) not in cleaned
        assert "cookie" not in cleaned.lower()
        assert "Article Title" in cleaned
        assert "Content with null bytes" in cleaned
        assert "More content" in cleaned

    def test_unicode_preservation_through_pipeline(self) -> None:
        """Test that legitimate Unicode survives full extraction pipeline."""
        # Arrange - content with emoji, CJK, and other valid Unicode
        unicode_content = (
            "# RAG Tutorial 🚀\n\n"
            "This tutorial covers RAG (检索增强生成).\n\n"
            "Key concepts:\n"
            "- Embeddings 💡\n"
            "- Vector DBs 🗄️\n"
            "- Retrieval 🔍\n\n"
            "\x00"  # null byte to trigger sanitization
            "Cookie consent: Accept cookies.\n"
        )

        # Act
        cleaned = clean_extracted_content(unicode_content)

        # Assert
        assert "\x00" not in cleaned
        assert "cookie" not in cleaned.lower()
        # All legitimate Unicode preserved
        assert "🚀" in cleaned
        assert "检索增强生成" in cleaned
        assert "💡" in cleaned
        assert "🗄️" in cleaned
        assert "🔍" in cleaned

    def test_empty_content_pipeline(self) -> None:
        """Test pipeline handles empty content gracefully."""
        # Arrange
        empty_content = ""

        # Act
        cleaned = clean_extracted_content(empty_content)
        sanitized = sanitize_utf8(cleaned)

        # Assert
        assert cleaned == ""
        assert sanitized == ""

    def test_all_invalid_content_pipeline(self) -> None:
        """Test pipeline handles content with only invalid characters."""
        # Arrange
        all_invalid = "\x00" + chr(0xD800) + chr(0xFFFE) + "\x00\x00"

        # Act
        sanitized = sanitize_utf8(all_invalid)

        # Assert
        assert sanitized == ""

    def test_large_document_pipeline(self) -> None:
        """Test pipeline handles large documents efficiently."""
        # Arrange - create a 1MB document with some invalid characters
        paragraph = (
            "This is a paragraph about RAG retrieval.\x00 "
            "It contains technical content about vector databases.\n\n"
        )
        # Repeat to create ~1MB (500KB * 2 = ~1MB)
        large_doc = paragraph * 10000

        # Act
        cleaned = clean_extracted_content(large_doc)

        # Assert
        assert "\x00" not in cleaned
        assert "RAG retrieval" in cleaned
        assert "vector databases" in cleaned
        assert len(cleaned) < len(large_doc)  # Null bytes removed


class TestJinaReaderSanitization:
    """Tests that JinaReader applies UTF-8 sanitization."""

    @pytest.mark.asyncio
    async def test_jina_reader_sanitizes_content(self) -> None:
        """Test that JinaReader calls clean_extracted_content which sanitizes UTF-8."""
        # Arrange
        reader = JinaReader()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = (
            "# Article Title\n\n"
            "Content with\x00 null bytes.\n"
            "More content" + chr(0xFFFE) + ".\n"
        )

        # Act
        with patch.object(reader.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            result = await reader.extract_article("https://example.com/article")

        # Assert
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
        with patch("app.shared.services.extraction.arxiv_pdf_extractor.PdfReader") as MockPdfReader:
            MockPdfReader.return_value = mock_reader
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
