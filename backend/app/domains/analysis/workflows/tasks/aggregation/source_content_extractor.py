"""Source content extraction for LLM grounding (Issue #487 - Hallucination Prevention).

This module extracts essential source content summaries to provide LLMs with
grounding during synthesis. By including title, summary, and key terms from the
original content, we help prevent hallucinations and improve synthesis accuracy.

Usage:
    summary = extract_source_summary(
        raw_content=content_text,
        extraction_metadata={"title": "Article Title"},
        max_chars=2000
    )
    # Returns: {"title": str, "summary": str, "key_terms": list[str]}
"""

import re
from collections import Counter
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum length for technical terms (shorter words are usually not technical)
MIN_TERM_LENGTH = 4

# Common English stopwords to filter from key term extraction
STOPWORDS = {
    "the",
    "be",
    "to",
    "of",
    "and",
    "a",
    "in",
    "that",
    "have",
    "i",
    "it",
    "for",
    "not",
    "on",
    "with",
    "he",
    "as",
    "you",
    "do",
    "at",
    "this",
    "but",
    "his",
    "by",
    "from",
    "they",
    "we",
    "say",
    "her",
    "she",
    "or",
    "an",
    "will",
    "my",
    "one",
    "all",
    "would",
    "there",
    "their",
    "what",
    "so",
    "up",
    "out",
    "if",
    "about",
    "who",
    "get",
    "which",
    "go",
    "me",
    "when",
    "make",
    "can",
    "like",
    "time",
    "no",
    "just",
    "him",
    "know",
    "take",
    "people",
    "into",
    "year",
    "your",
    "good",
    "some",
    "could",
    "them",
    "see",
    "other",
    "than",
    "then",
    "now",
    "look",
    "only",
    "come",
    "its",
    "over",
    "think",
    "also",
    "back",
    "after",
    "use",
    "two",
    "how",
    "our",
    "work",
    "first",
    "well",
    "way",
    "even",
    "new",
    "want",
    "because",
    "any",
    "these",
    "give",
    "day",
    "most",
    "us",
    "is",
    "was",
    "are",
    "been",
    "has",
    "had",
    "were",
    "said",
    "did",
    "having",
    "may",
    "should",
    "does",
    "am",
}


def truncate_at_word_boundary(text: str, max_chars: int) -> str:
    """Truncate text at word boundary to avoid mid-word cuts.

    Truncates at the last complete word before max_chars limit.
    Adds "..." if text was truncated.

    Args:
        text: Text to truncate
        max_chars: Maximum character length (includes "..." if added)

    Returns:
        Truncated text with "..." appended if truncated

    Examples:
        >>> truncate_at_word_boundary("Hello world this is a test", 15)
        'Hello world...'
        >>> truncate_at_word_boundary("Short", 100)
        'Short'

    """
    if len(text) <= max_chars:
        return text

    # Reserve 3 characters for "..."
    truncate_at = max_chars - 3

    # Find last space before truncation point
    last_space = text.rfind(" ", 0, truncate_at)

    if last_space == -1:
        # No space found - truncate at max_chars directly
        return text[:truncate_at] + "..."

    # Truncate at last complete word
    return text[:last_space] + "..."


def extract_key_terms(text: str, top_n: int = 20) -> list[str]:
    """Extract technical key terms using frequency analysis.

    Identifies important technical terms by:
    1. Tokenizing text into words (alphanumeric only)
    2. Filtering out common English stopwords
    3. Keeping only terms with 4+ characters (technical terms are usually longer)
    4. Counting frequency and returning top N most common

    Args:
        text: Text to extract terms from
        top_n: Number of top terms to return (default: 20)

    Returns:
        List of top N key terms sorted by frequency (descending)

    Examples:
        >>> extract_key_terms("Python FastAPI REST API Python", top_n=2)
        ['python', 'fastapi']

    """
    if not text:
        return []

    # Tokenize: extract words (alphanumeric sequences)
    # Convert to lowercase for case-insensitive matching
    words = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())

    # Filter: remove stopwords and short words
    # Technical terms are usually MIN_TERM_LENGTH+ characters
    filtered_words = [
        word for word in words if len(word) >= MIN_TERM_LENGTH and word.lower() not in STOPWORDS
    ]

    if not filtered_words:
        return []

    # Count frequency
    word_counts = Counter(filtered_words)

    # Return top N most common terms
    return [word for word, _count in word_counts.most_common(top_n)]


def extract_source_summary(
    raw_content: str,
    extraction_metadata: dict[str, Any],
    max_chars: int = 2000,
) -> dict[str, Any]:
    """Extract source content summary for LLM grounding.

    Creates a compact summary of the source content to provide LLMs with
    grounding context during synthesis. This helps prevent hallucinations
    by reminding the LLM of the original source material.

    Args:
        raw_content: Raw text content extracted from source
        extraction_metadata: Metadata dict with optional "title" key
        max_chars: Maximum characters for summary (default: 2000)

    Returns:
        Dictionary with:
            - title (str): Document title or "Untitled"
            - summary (str): First max_chars of content, word-boundary truncated
            - key_terms (list[str]): Top 20 technical terms by frequency

    Examples:
        >>> summary = extract_source_summary(
        ...     raw_content="Python is a programming language...",
        ...     extraction_metadata={"title": "Python Guide"},
        ...     max_chars=50,
        ... )
        >>> summary["title"]
        'Python Guide'
        >>> len(summary["key_terms"]) <= 20
        True

    """
    logger.debug(
        "extracting_source_summary",
        content_length=len(raw_content),
        max_chars=max_chars,
    )

    # Extract title from metadata
    title = extraction_metadata.get("title", "Untitled")
    if not isinstance(title, str):
        title = str(title) if title else "Untitled"

    # Create summary: truncate content at word boundary
    summary = truncate_at_word_boundary(raw_content, max_chars)

    # Extract key technical terms
    key_terms = extract_key_terms(raw_content, top_n=20)

    result = {
        "title": title,
        "summary": summary,
        "key_terms": key_terms,
    }

    logger.info(
        "source_summary_extracted",
        title=title,
        summary_length=len(summary),
        key_terms_count=len(key_terms),
        truncated=len(raw_content) > max_chars,
    )

    return result
