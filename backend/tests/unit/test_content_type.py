"""Unit tests for content type detection with validation."""

import pytest

from app.core.constants import CONTENT_TYPE_ARTICLE, CONTENT_TYPE_REPO, CONTENT_TYPE_VIDEO
from app.services.extraction.content_type import ContentTypeError, detect_content_type


def test_detect_youtube_video() -> None:
    """Test detection of YouTube video URLs."""
    assert detect_content_type("https://youtube.com/watch?v=123") == CONTENT_TYPE_VIDEO
    assert detect_content_type("https://www.youtube.com/watch?v=123") == CONTENT_TYPE_VIDEO
    assert detect_content_type("https://youtu.be/123") == CONTENT_TYPE_VIDEO


def test_detect_github_repo() -> None:
    """Test detection of GitHub repository URLs."""
    assert detect_content_type("https://github.com/user/repo") == CONTENT_TYPE_REPO
    assert detect_content_type("https://github.com/user/repo/tree/main") == CONTENT_TYPE_REPO
    assert detect_content_type("https://www.github.com/user/repo") == CONTENT_TYPE_REPO


def test_detect_article_default() -> None:
    """Test default to article for non-video, non-repo URLs."""
    assert detect_content_type("https://example.com/article") == CONTENT_TYPE_ARTICLE
    assert detect_content_type("https://medium.com/@user/article") == CONTENT_TYPE_ARTICLE
    assert detect_content_type("https://blog.example.com/post") == CONTENT_TYPE_ARTICLE


def test_url_validation_empty_string() -> None:
    """Test that empty string raises ContentTypeError."""
    with pytest.raises(
        ContentTypeError, match="URL must be a non-empty string|URL cannot be empty"
    ):
        detect_content_type("")


def test_url_validation_whitespace() -> None:
    """Test that whitespace-only URL raises ContentTypeError."""
    with pytest.raises(ContentTypeError, match="URL cannot be empty"):
        detect_content_type("   ")


def test_url_validation_invalid_type() -> None:
    """Test that non-string input raises ContentTypeError."""
    with pytest.raises(ContentTypeError, match="URL must be a non-empty string"):
        detect_content_type(None)  # type: ignore[arg-type]

    with pytest.raises(ContentTypeError, match="URL must be a non-empty string"):
        detect_content_type(123)  # type: ignore[arg-type]


def test_url_validation_missing_scheme() -> None:
    """Test that URL without scheme raises ContentTypeError."""
    with pytest.raises(ContentTypeError, match="Invalid URL format|Failed to parse URL"):
        detect_content_type("example.com/article")


def test_url_validation_missing_netloc() -> None:
    """Test that URL without netloc raises ContentTypeError."""
    with pytest.raises(ContentTypeError, match="Invalid URL format|Failed to parse URL"):
        detect_content_type("https://")


def test_url_validation_case_insensitive() -> None:
    """Test that URL detection is case-insensitive."""
    assert detect_content_type("https://YOUTUBE.COM/watch?v=123") == CONTENT_TYPE_VIDEO
    assert detect_content_type("https://GITHUB.COM/user/repo") == CONTENT_TYPE_REPO
    assert detect_content_type("https://EXAMPLE.COM/article") == CONTENT_TYPE_ARTICLE


def test_url_stripping() -> None:
    """Test that URLs with leading/trailing whitespace are handled."""
    assert detect_content_type("  https://youtube.com/watch?v=123  ") == CONTENT_TYPE_VIDEO
    assert detect_content_type("  https://github.com/user/repo  ") == CONTENT_TYPE_REPO
