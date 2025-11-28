"""Content type detection utility."""

from urllib.parse import urlparse

from app.core.constants import (
    CONTENT_TYPE_ARTICLE,
    CONTENT_TYPE_REPO,
    CONTENT_TYPE_VIDEO,
)
from app.core.exceptions import ServiceException


class ContentTypeError(ServiceException):
    """Exception raised when content type detection fails."""

    pass


def detect_content_type(url: str) -> str:
    """Detect content type from URL patterns.

    Validates the URL format and detects content type based on domain patterns.
    Supports YouTube (video), GitHub (repo), and defaults to article.

    Args:
        url: The URL to analyze

    Returns:
        Content type string: 'article', 'video', or 'repo'

    Raises:
        ContentTypeError: If URL is invalid or cannot be parsed

    Example:
        >>> detect_content_type("https://youtube.com/watch?v=123")
        'video'
        >>> detect_content_type("https://github.com/user/repo")
        'repo'
        >>> detect_content_type("https://example.com/article")
        'article'

    """
    if not url or not isinstance(url, str):
        msg = "URL must be a non-empty string"
        raise ContentTypeError(msg)

    url = url.strip()
    if not url:
        msg = "URL cannot be empty"
        raise ContentTypeError(msg)

    # Validate URL format
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            msg = f"Invalid URL format: {url}"
            raise ContentTypeError(msg)
    except Exception as e:
        msg = f"Failed to parse URL: {url}"
        raise ContentTypeError(msg) from e

    url_lower = url.lower()

    # Check for YouTube patterns
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return CONTENT_TYPE_VIDEO

    # Check for GitHub patterns
    if "github.com" in url_lower:
        return CONTENT_TYPE_REPO

    # Default to article
    return CONTENT_TYPE_ARTICLE
