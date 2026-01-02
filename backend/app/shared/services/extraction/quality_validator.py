"""Quality validation for extraction results.

Validates extraction quality before accepting results, enabling
fallback strategies and quality-based extractor selection.
"""

import re

from app.core.constants import DEFAULT_TITLE
from app.core.logging import get_logger
from app.core.types import ExtractionResult

logger = get_logger(__name__)

# Quality thresholds
MIN_WORD_COUNT = 50  # Minimum words for valid article
MAX_WORD_COUNT = 500000  # Maximum words (detect if we got whole site)
MIN_TITLE_LENGTH = 5
MAX_TITLE_LENGTH = 200

# Error page indicators
ERROR_PAGE_INDICATORS = [
    "404",
    "not found",
    "page not found",
    "error",
    "access denied",
    "forbidden",
    "unauthorized",
    "redirecting",
    "moved permanently",
    "bad gateway",
    "service unavailable",
    "internal server error",
]


def validate_title_quality(title: str | None) -> float:
    """Validate title quality (0.0 to 1.0).

    Args:
        title: Title to validate

    Returns:
        Quality score between 0.0 and 1.0

    """
    if not title:
        return 0.0

    title = title.strip()

    # Empty or default title
    if not title or title == DEFAULT_TITLE:
        return 0.0

    # Too short or too long
    if len(title) < MIN_TITLE_LENGTH or len(title) > MAX_TITLE_LENGTH:
        return 0.3

    # Error page indicator
    title_lower = title.lower()
    if any(indicator in title_lower for indicator in ERROR_PAGE_INDICATORS):
        return 0.2

    # Contains "Title: " prefix (JinaReader sometimes adds this)
    if title.startswith("Title: "):
        return 0.7  # Valid but not perfect

    # Good title
    return 1.0


def validate_content_length(word_count: int) -> float:
    """Validate content length quality (0.0 to 1.0).

    Args:
        word_count: Number of words in content

    Returns:
        Quality score between 0.0 and 1.0

    """
    if word_count < MIN_WORD_COUNT:
        # Too short - likely incomplete or error page
        if word_count == 0:
            return 0.0
        # Partial content
        return min(word_count / MIN_WORD_COUNT, 0.5)

    if word_count > MAX_WORD_COUNT:
        # Too long - likely got whole site instead of article
        return 0.3

    # Good length
    return 1.0


def validate_content_structure(content: str) -> float:
    """Validate content structure quality (0.0 to 1.0).

    Args:
        content: Extracted content

    Returns:
        Quality score between 0.0 and 1.0

    """
    if not content:
        return 0.0

    lines = content.split("\n")
    if len(lines) < 3:
        # Too few lines - likely incomplete
        return 0.3

    # Check for paragraph structure (blank lines)
    blank_lines = sum(1 for line in lines if not line.strip())
    if blank_lines < 2:
        # No paragraph breaks - might be single block
        return 0.6

    # Check for headings (markdown structure)
    has_headings = any(line.strip().startswith("#") for line in lines)
    if has_headings:
        return 1.0

    # Has paragraphs but no headings - still good
    return 0.8


def validate_content_relevance(content: str, url: str) -> float:
    """Validate content relevance to URL (0.0 to 1.0).

    Args:
        content: Extracted content
        url: Source URL

    Returns:
        Quality score between 0.0 and 1.0

    """
    if not content or not url:
        return 0.5  # Can't validate

    content_lower = content.lower()
    url_lower = url.lower()

    # Extract domain from URL
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        domain = domain.replace("www.", "")

        # Check if domain keywords appear in content
        domain_parts = domain.split(".")
        if domain_parts:
            main_domain = domain_parts[0]
            if main_domain and main_domain in content_lower:
                return 1.0

    except Exception:  # noqa: BLE001 - Graceful degradation
        pass

    # Check for common error page patterns
    error_patterns = [
        r"login",
        r"sign in",
        r"access denied",
        r"403 forbidden",
        r"404 not found",
        r"page not found",
    ]

    content_snippet = content_lower[:500]  # Check first 500 chars
    if any(re.search(pattern, content_snippet) for pattern in error_patterns):
        return 0.2

    # Can't determine relevance - neutral score
    return 0.7


def validate_extraction_completeness(content: str) -> float:
    """Validate extraction completeness (0.0 to 1.0).

    Args:
        content: Extracted content

    Returns:
        Quality score between 0.0 and 1.0

    """
    if not content:
        return 0.0

    # Check if content ends mid-sentence (incomplete extraction)
    content_stripped = content.strip()
    if not content_stripped:
        return 0.0

    # Check last 100 characters for sentence completion
    last_part = content_stripped[-100:]
    # Look for sentence-ending punctuation
    has_ending = any(last_part.rstrip().endswith(punct) for punct in [".", "!", "?"])

    if not has_ending and len(content_stripped) > 500:
        # Long content without sentence ending - might be truncated
        return 0.7

    # Content appears complete
    return 1.0


def calculate_quality_score(
    result: ExtractionResult,
    url: str,
) -> dict[str, float | bool]:
    """Calculate overall quality score for extraction result.

    Args:
        result: Extraction result from extractor
        url: Source URL

    Returns:
        Dictionary with quality scores and flags

    """
    title = result.get("title")
    content = result.get("content", "")
    word_count = result.get("word_count", 0)

    # Calculate individual scores
    title_score = validate_title_quality(title)
    length_score = validate_content_length(word_count)
    structure_score = validate_content_structure(content)
    relevance_score = validate_content_relevance(content, url)
    completeness_score = validate_extraction_completeness(content)

    # Weighted overall score
    # Title: 20%, Length: 20%, Structure: 25%, Relevance: 20%, Completeness: 15%
    overall_score = (
        title_score * 0.2
        + length_score * 0.2
        + structure_score * 0.25
        + relevance_score * 0.2
        + completeness_score * 0.15
    )

    # Quality flags
    title_valid = title_score >= 0.7
    content_valid = length_score >= 0.5 and structure_score >= 0.6
    is_complete = completeness_score >= 0.8

    return {
        "overall_score": round(overall_score, 3),
        "title_score": round(title_score, 3),
        "length_score": round(length_score, 3),
        "structure_score": round(structure_score, 3),
        "relevance_score": round(relevance_score, 3),
        "completeness_score": round(completeness_score, 3),
        "title_valid": title_valid,
        "content_valid": content_valid,
        "is_complete": is_complete,
        "passes_threshold": overall_score >= 0.8,  # 80% threshold
    }


def is_acceptable_quality(
    result: ExtractionResult,
    url: str,
    min_score: float = 0.8,
) -> tuple[bool, dict[str, float | bool]]:
    """Check if extraction result meets quality threshold.

    Args:
        result: Extraction result from extractor
        url: Source URL
        min_score: Minimum quality score to accept (default: 0.8)

    Returns:
        Tuple of (is_acceptable, quality_metrics)

    """
    quality = calculate_quality_score(result, url)
    is_acceptable = quality["overall_score"] >= min_score and quality["passes_threshold"]

    return is_acceptable, quality
