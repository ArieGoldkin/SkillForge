"""Content type detection utility."""


def detect_content_type(url: str) -> str:
    """
    Detect content type from URL patterns.

    Args:
        url: The URL to analyze

    Returns:
        Content type string: 'article', 'video', or 'repo'
    """
    url_lower = url.lower()

    # Check for YouTube patterns
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "video"

    # Check for GitHub patterns
    if "github.com" in url_lower:
        return "repo"

    # Default to article
    return "article"
