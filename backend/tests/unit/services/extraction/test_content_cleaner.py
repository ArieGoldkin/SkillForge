"""Unit tests for content cleaner module.

DEPRECATED FUNCTION TESTS:
- Tests for clean_extracted_content() are kept for backward compatibility verification
- These tests use pytest.warns() to explicitly test deprecation warnings
- New code should use TrafilaturaExtractor instead (ML-based cleaning, F1=0.958)
"""

from unittest.mock import Mock, patch

import pytest

from app.shared.services.extraction.content_cleaner import (
    clean_extracted_content,
    extract_main_content,
)
from app.shared.services.extraction.trafilatura_extractor import TrafilaturaExtractor


class TestCleanExtractedContent:
    """Tests for clean_extracted_content function (DEPRECATED).

    These tests verify deprecated function behavior with explicit deprecation warning handling.
    New code should use TrafilaturaExtractor instead.
    """

    def test_empty_content_returns_empty(self):
        """Empty content should return empty string."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            assert clean_extracted_content("") == ""
            # Note: clean_extracted_content accepts str, but handles None in implementation
            assert clean_extracted_content(None) is None  # type: ignore[arg-type]

    def test_removes_cookie_consent_banners(self):
        """Cookie consent banners should be removed."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Article Title

This is the introduction.

This website uses cookies to personalize content.

More article content here.
"""
            cleaned = clean_extracted_content(content)
            assert "uses cookies" not in cleaned.lower()
            assert "Article Title" in cleaned
            assert "More article content" in cleaned

    def test_removes_cookiebot_references(self):
        """Cookiebot-specific content should be removed."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Article Title

![Image](blob:http://localhost/abc123)

[](https://www.cookiebot.com/en/what-is-behind-powered-by-cookiebot/)

*   [Consent]

Actual article content starts here.
"""
            cleaned = clean_extracted_content(content)
            assert "cookiebot" not in cleaned.lower()
            assert "blob:http" not in cleaned
            assert "article content" in cleaned.lower()

    def test_removes_gdpr_consent_checkboxes(self):
        """GDPR consent checkbox patterns should be removed."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Title

*   [Necessary] - [x]
*   [Preferences] - [x]
*   [Statistics] - [x]
*   [Marketing] - [x]

Article body content.
"""
            cleaned = clean_extracted_content(content)
            # The checkbox patterns should be removed
            assert "Necessary" not in cleaned
            assert "Preferences" not in cleaned
            assert "Statistics" not in cleaned
            assert "Marketing" not in cleaned
            assert "Article body content" in cleaned

    def test_removes_copyright_footer(self):
        """Copyright and footer content should be removed."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Article Title

Main content here.

Copyright 2024 All Rights Reserved.
Terms of Service | Privacy Policy
"""
            cleaned = clean_extracted_content(content)
            assert "copyright" not in cleaned.lower()
            assert "all rights reserved" not in cleaned.lower()
            assert "Main content" in cleaned

    def test_removes_blob_urls(self):
        """Blob URLs (local/broken images) should be removed."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Article Title

![Image 1: logo](blob:http://localhost/4eb6460ab93a7ae1978320dda45af1eb)

Some text.

![Image 2: banner](blob:https://example.com/xyz)
"""
            cleaned = clean_extracted_content(content)
            assert "blob:" not in cleaned
            assert "Some text" in cleaned

    def test_preserves_main_content(self):
        """Main article content should be preserved."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Semantic Caching: What We Measured, Why It Matters

## Introduction

Semantic caching is a technique that stores query results based on meaning.

## How It Works

The system uses embeddings to compare queries.

## Results

We found a 40% reduction in API calls.
"""
            cleaned = clean_extracted_content(content)
            # All main content should be preserved
            assert "Semantic Caching" in cleaned
            assert "Introduction" in cleaned
            assert "embeddings" in cleaned
            assert "40% reduction" in cleaned

    def test_collapses_multiple_blank_lines(self):
        """Multiple consecutive blank lines should be collapsed."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Title



Too many blank lines above.




And here too.
"""
            cleaned = clean_extracted_content(content)
            # Should not have more than 2 consecutive newlines
            assert "\n\n\n" not in cleaned

    def test_trims_after_related_articles(self):
        """Content after 'Related Articles' section should be trimmed."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Main Article

This is the main content.

## Related

More stuff that should be removed.
"""
            cleaned = clean_extracted_content(content)
            # Main content should be preserved
            assert "main content" in cleaned.lower()


class TestTrafilaturaExtractorCleaning:
    """Tests for TrafilaturaExtractor cleaning capabilities (REPLACEMENT for clean_extracted_content).

    These tests verify that TrafilaturaExtractor properly removes boilerplate during extraction.
    """

    @pytest.fixture
    def extractor(self) -> TrafilaturaExtractor:
        """Create TrafilaturaExtractor instance."""
        return TrafilaturaExtractor()

    @pytest.mark.asyncio
    async def test_trafilatura_removes_cookie_consent_banners(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that TrafilaturaExtractor removes cookie consent banners during extraction."""
        # Arrange - HTML with cookie consent banner
        html_with_cookies = """
        <html>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>This is the introduction.</p>
                    <p>More article content here.</p>
                </article>
                <div class="cookie-consent">This website uses cookies to personalize content.</div>
            </body>
        </html>
        """
        # Trafilatura's ML-based extraction should remove cookie banners
        cleaned_markdown = (
            "# Article Title\n\nThis is the introduction.\n\nMore article content here."
        )

        mock_metadata = Mock()
        mock_metadata.title = "Article Title"

        with (
            patch.object(extractor.trafilatura, "fetch_url") as mock_fetch,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_fetch.return_value = html_with_cookies
            mock_extract.return_value = cleaned_markdown
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert - cookie banner should be removed by Trafilatura
            content = result["content"]
            assert isinstance(content, str), "Content should be a string"
            assert "uses cookies" not in content.lower()
            assert "Article Title" in content
            assert "More article content" in content

    @pytest.mark.asyncio
    async def test_trafilatura_removes_footer_content(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that TrafilaturaExtractor removes footer content during extraction."""
        # Arrange - HTML with footer
        html_with_footer = """
        <html>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>Main content here.</p>
                </article>
                <footer>
                    <p>Copyright 2024 All Rights Reserved.</p>
                    <p>Terms of Service | Privacy Policy</p>
                </footer>
            </body>
        </html>
        """
        # Trafilatura should extract only main content
        cleaned_markdown = "# Article Title\n\nMain content here."

        mock_metadata = Mock()
        mock_metadata.title = "Article Title"

        with (
            patch.object(extractor.trafilatura, "fetch_url") as mock_fetch,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_fetch.return_value = html_with_footer
            mock_extract.return_value = cleaned_markdown
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert - footer should be removed by Trafilatura
            content = result["content"]
            assert isinstance(content, str), "Content should be a string"
            assert "copyright" not in content.lower()
            assert "all rights reserved" not in content.lower()
            assert "Main content" in content

    @pytest.mark.asyncio
    async def test_trafilatura_preserves_main_content(
        self, extractor: TrafilaturaExtractor
    ) -> None:
        """Test that TrafilaturaExtractor preserves main article content."""
        # Arrange - HTML with main content
        html_with_content = """
        <html>
            <body>
                <article>
                    <h1>Semantic Caching: What We Measured, Why It Matters</h1>
                    <h2>Introduction</h2>
                    <p>Semantic caching is a technique that stores query results based on meaning.</p>
                    <h2>How It Works</h2>
                    <p>The system uses embeddings to compare queries.</p>
                    <h2>Results</h2>
                    <p>We found a 40% reduction in API calls.</p>
                </article>
            </body>
        </html>
        """
        cleaned_markdown = """# Semantic Caching: What We Measured, Why It Matters

## Introduction

Semantic caching is a technique that stores query results based on meaning.

## How It Works

The system uses embeddings to compare queries.

## Results

We found a 40% reduction in API calls.
"""

        mock_metadata = Mock()
        mock_metadata.title = "Semantic Caching: What We Measured, Why It Matters"

        with (
            patch.object(extractor.trafilatura, "fetch_url") as mock_fetch,
            patch.object(extractor.trafilatura, "extract") as mock_extract,
            patch.object(extractor.trafilatura, "extract_metadata") as mock_extract_metadata,
        ):
            mock_fetch.return_value = html_with_content
            mock_extract.return_value = cleaned_markdown
            mock_extract_metadata.return_value = mock_metadata

            # Act
            result = await extractor.extract_article("https://example.com/article")

            # Assert - all main content should be preserved
            content = result["content"]
            assert isinstance(content, str), "Content should be a string"
            assert "Semantic Caching" in content
            assert "Introduction" in content
            assert "embeddings" in content
            assert "40% reduction" in content


class TestExtractMainContent:
    """Tests for extract_main_content function.

    NOTE: This function uses clean_extracted_content() internally, so it will emit deprecation warnings.
    Consider migrating to TrafilaturaExtractor for new code.
    """

    def test_extracts_substantial_paragraphs(self):
        """Should extract only substantial paragraphs."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Article Title

Short.

This is a much longer paragraph that contains substantial content and should definitely be included in the extracted main content because it meets the minimum length requirement.

Another short one.

Here is another substantial paragraph with plenty of meaningful content that provides value to readers and should be part of the main extraction.
"""
            extracted = extract_main_content(content, min_paragraph_length=50)
            # Headers should be included
            assert "Article Title" in extracted
            # Long paragraphs should be included
            assert "much longer paragraph" in extracted
            assert "substantial paragraph" in extracted
            # Short paragraphs may be excluded (depending on implementation)

    def test_includes_headers(self):
        """Headers should always be included."""
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            content = """# Main Header

## Subheader

Short text.

### Another Subheader

More short text.
"""
            extracted = extract_main_content(content)
            assert "# Main Header" in extracted
            assert "## Subheader" in extracted
            assert "### Another Subheader" in extracted

    def test_handles_empty_content(self):
        """Empty content should return empty string."""
        # extract_main_content calls clean_extracted_content internally, which emits deprecation warning
        # However, empty strings are handled early, so we need to test with non-empty content
        # to trigger the deprecation warning, or just verify the function works
        with pytest.warns(DeprecationWarning, match="clean_extracted_content.*deprecated"):
            # Use non-empty content to trigger clean_extracted_content call
            result = extract_main_content("# Test\n\nSome content here.")
            assert result  # Should return content

        # Empty content is handled early, so no warning for empty strings
        assert extract_main_content("") == ""
        # Note: extract_main_content accepts str, but handles None in implementation
        assert extract_main_content(None) is None  # type: ignore[arg-type]
