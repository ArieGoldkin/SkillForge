"""Unit tests for content_cleaner module.

Tests UTF-8 sanitization for PostgreSQL compatibility.
"""

from app.shared.services.extraction.content_cleaner import (
    clean_extracted_content,
    sanitize_utf8,
)


class TestSanitizeUtf8:
    """Tests for sanitize_utf8 function."""

    def test_sanitize_utf8_removes_null_bytes(self) -> None:
        """Test that null bytes are removed from text."""
        # Arrange
        text_with_nulls = "Hello\x00World\x00Test"

        # Act
        result = sanitize_utf8(text_with_nulls)

        # Assert
        assert result == "HelloWorldTest"
        assert "\x00" not in result

    def test_sanitize_utf8_removes_surrogates(self) -> None:
        """Test that UTF-16 surrogate characters are removed."""
        # Arrange - create string with surrogate characters
        # Surrogates are in range 0xD800-0xDFFF
        text_with_surrogates = "Hello" + chr(0xD800) + "World" + chr(0xDFFF) + "Test"

        # Act
        result = sanitize_utf8(text_with_surrogates)

        # Assert
        assert result == "HelloWorldTest"
        # Verify no surrogate characters remain
        for char in result:
            code_point = ord(char)
            assert not (0xD800 <= code_point <= 0xDFFF)

    def test_sanitize_utf8_removes_invalid_code_points(self) -> None:
        """Test that invalid Unicode code points (0xFFFE, 0xFFFF) are removed."""
        # Arrange
        text_with_invalid = "Hello" + chr(0xFFFE) + "World" + chr(0xFFFF) + "Test"

        # Act
        result = sanitize_utf8(text_with_invalid)

        # Assert
        assert result == "HelloWorldTest"
        assert chr(0xFFFE) not in result
        assert chr(0xFFFF) not in result

    def test_sanitize_utf8_preserves_valid_unicode(self) -> None:
        """Test that legitimate Unicode (emoji, CJK, etc.) is preserved."""
        # Arrange - text with emoji, CJK characters, and other valid Unicode
        text_with_unicode = (
            "Hello 🚀 World\n"
            "日本語 (Japanese)\n"
            "한국어 (Korean)\n"
            "中文 (Chinese)\n"
            "Ελληνικά (Greek)\n"
            "العربية (Arabic)\n"
            "🎉🎊✨💡🔥"
        )

        # Act
        result = sanitize_utf8(text_with_unicode)

        # Assert - should be unchanged
        assert result == text_with_unicode

    def test_sanitize_utf8_empty_string(self) -> None:
        """Test that empty string is handled correctly."""
        # Arrange
        empty = ""

        # Act
        result = sanitize_utf8(empty)

        # Assert
        assert result == ""

    def test_sanitize_utf8_none_value(self) -> None:
        """Test that None is handled correctly."""
        # Arrange
        none_value = None

        # Act
        result = sanitize_utf8(none_value)  # type: ignore[arg-type]

        # Assert
        assert result is None

    def test_sanitize_utf8_mixed_invalid_characters(self) -> None:
        """Test removal of mixed invalid characters (nulls, surrogates, invalid code points)."""
        # Arrange
        text = (
            "Start\x00"  # null byte
            + "Middle"
            + chr(0xD800)  # surrogate
            + "More"
            + chr(0xFFFE)  # invalid code point
            + "End"
        )

        # Act
        result = sanitize_utf8(text)

        # Assert
        assert result == "StartMiddleMoreEnd"
        assert "\x00" not in result
        assert chr(0xD800) not in result
        assert chr(0xFFFE) not in result


class TestCleanExtractedContentSanitization:
    """Tests that clean_extracted_content calls sanitize_utf8."""

    def test_clean_extracted_content_sanitizes_utf8(self) -> None:
        """Test that clean_extracted_content sanitizes UTF-8 as final step."""
        # Arrange - content with null bytes and boilerplate
        content = (
            "# Article Title\n\n"
            "This is the\x00 main content.\n\n"
            "More content here" + chr(0xFFFE) + ".\n\n"
            "Cookie consent: We use cookies.\n"
        )

        # Act
        result = clean_extracted_content(content)

        # Assert - both boilerplate cleaning AND UTF-8 sanitization should occur
        assert "\x00" not in result  # Null bytes removed
        assert chr(0xFFFE) not in result  # Invalid code points removed
        assert "cookie" not in result.lower()  # Boilerplate removed
        assert "Article Title" in result  # Main content preserved
        assert "main content" in result

    def test_clean_extracted_content_preserves_valid_unicode(self) -> None:
        """Test that legitimate Unicode is preserved through cleaning pipeline."""
        # Arrange
        content = (
            "# Technical Article 🚀\n\n"
            "This article discusses RAG (检索增强生成).\n\n"
            "Key points:\n"
            "- Embedding models 💡\n"
            "- Vector databases 🗄️\n"
            "- Retrieval strategies 🔍\n\n"
            "Cookie consent: Accept all cookies.\n"
        )

        # Act
        result = clean_extracted_content(content)

        # Assert
        assert "🚀" in result
        assert "检索增强生成" in result
        assert "💡" in result
        assert "🗄️" in result
        assert "🔍" in result
        assert "cookie" not in result.lower()  # Boilerplate removed

    def test_clean_extracted_content_empty_string(self) -> None:
        """Test that empty string is handled correctly."""
        # Arrange
        empty = ""

        # Act
        result = clean_extracted_content(empty)

        # Assert
        assert result == ""


class TestSanitizeUtf8EdgeCases:
    """Additional edge case tests for UTF-8 sanitization."""

    def test_sanitize_utf8_real_pdf_content(self) -> None:
        """Test with realistic PDF-like content containing null bytes."""
        # Arrange - simulates PDF extraction with null bytes and ligatures
        pdf_content = (
            "arXiv:2512.08296v1\x00 [cs.AI] 11 Dec 2024\n\n"
            "E\ufb03cient RAG Retrieval\x00\n\n"  # ligature: eff
            "Abstract\x00: This paper discusses\x00 vector databases.\n"
            "Key \ufb01ndings include...\n"  # ligature: fi
        )

        # Act
        result = sanitize_utf8(pdf_content)

        # Assert
        assert "\x00" not in result
        assert "arXiv:2512.08296v1" in result
        assert "Abstract" in result
        assert "vector databases" in result
        # Ligatures should be preserved (they're valid Unicode)
        assert "\ufb03" in result  # eff ligature
        assert "\ufb01" in result  # fi ligature

    def test_sanitize_utf8_mixed_valid_invalid_unicode(self) -> None:
        """Test with mixed valid and invalid Unicode in same string."""
        # Arrange - mix of emoji, CJK, surrogates, and null bytes
        mixed_content = (
            "Start 🚀\x00"  # emoji + null
            + chr(0xD800)  # surrogate
            + " 中文 "  # CJK
            + chr(0xFFFE)  # invalid code point
            + "End 💡"  # emoji
        )

        # Act
        result = sanitize_utf8(mixed_content)

        # Assert
        assert result == "Start 🚀 中文 End 💡"
        assert "\x00" not in result
        assert chr(0xD800) not in result
        assert chr(0xFFFE) not in result
        assert "🚀" in result
        assert "💡" in result
        assert "中文" in result

    def test_sanitize_utf8_performance_large_string(self) -> None:
        """Test performance with large strings (1MB+)."""
        # Arrange - create 1MB string with some invalid characters
        chunk = "Valid text " * 100  # ~1100 bytes
        invalid_chunk = "Text\x00with" + chr(0xD800) + "invalid\n"  # ~20 bytes
        # Repeat to get ~1MB (1000 * 1120 bytes = ~1.1MB)
        large_content = (chunk + invalid_chunk) * 1000

        # Act
        result = sanitize_utf8(large_content)

        # Assert
        assert "\x00" not in result
        assert chr(0xD800) not in result
        assert "Valid text" in result
        assert "Textwith" in result  # null byte removed
        assert len(result) < len(large_content)  # Some chars removed

    def test_sanitize_utf8_idempotent(self) -> None:
        """Test that sanitization is idempotent (running twice gives same result)."""
        # Arrange
        dirty_text = "Hello\x00World" + chr(0xD800) + "Test" + chr(0xFFFE)

        # Act
        first_clean = sanitize_utf8(dirty_text)
        second_clean = sanitize_utf8(first_clean)

        # Assert
        assert first_clean == second_clean
        assert first_clean == "HelloWorldTest"

    def test_sanitize_utf8_all_invalid_characters(self) -> None:
        """Test with string containing only invalid characters."""
        # Arrange
        all_invalid = "\x00" + chr(0xD800) + chr(0xDFFF) + chr(0xFFFE) + chr(0xFFFF)

        # Act
        result = sanitize_utf8(all_invalid)

        # Assert
        assert result == ""

    def test_sanitize_utf8_whitespace_preservation(self) -> None:
        """Test that whitespace (including newlines, tabs) is preserved."""
        # Arrange
        text_with_whitespace = (
            "Line 1\x00\n"
            "Line 2\t\tTab\n"
            "Line 3   Spaces\n"
            "\n"
            "Line 5"
        )

        # Act
        result = sanitize_utf8(text_with_whitespace)

        # Assert
        assert result == "Line 1\nLine 2\t\tTab\nLine 3   Spaces\n\nLine 5"
        assert "\x00" not in result
        assert "\n" in result
        assert "\t" in result
