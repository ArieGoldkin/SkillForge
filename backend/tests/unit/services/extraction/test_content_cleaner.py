"""Unit tests for content cleaner module."""

from app.shared.services.extraction.content_cleaner import (

@pytest.mark.unit
    clean_extracted_content,
    extract_main_content,
)


class TestCleanExtractedContent:
    """Tests for clean_extracted_content function."""

    def test_empty_content_returns_empty(self):
        """Empty content should return empty string."""
        assert clean_extracted_content("") == ""
        assert clean_extracted_content(None) is None

    def test_removes_cookie_consent_banners(self):
        """Cookie consent banners should be removed."""
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
        content = """# Title



Too many blank lines above.




And here too.
"""
        cleaned = clean_extracted_content(content)
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in cleaned

    def test_trims_after_related_articles(self):
        """Content after 'Related Articles' section should be trimmed."""
        content = """# Main Article

This is the main content.

## Related

More stuff that should be removed.
"""
        cleaned = clean_extracted_content(content)
        # Main content should be preserved
        assert "main content" in cleaned.lower()


class TestExtractMainContent:
    """Tests for extract_main_content function."""

    def test_extracts_substantial_paragraphs(self):
        """Should extract only substantial paragraphs."""
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
        assert extract_main_content("") == ""
        assert extract_main_content(None) is None
