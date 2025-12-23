"""Hallucination prevention through source content grounding validation.

This module validates that LLM synthesis output is grounded in source content
by comparing key technical terms between source material and generated output.

Issue #487 - Prevents hallucinations in multi-agent synthesis.
"""

from collections import Counter

from app.core.logging import get_logger

logger = get_logger(__name__)

# Common English stopwords to filter out (not technical terms)
COMMON_STOPWORDS = {
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
}


def extract_key_terms(text: str, min_length: int = 4, top_n: int = 50) -> set[str]:
    """Extract key technical terms from text using frequency analysis.

    Args:
        text: Source text to analyze
        min_length: Minimum word length to consider (filters noise)
        top_n: Number of top terms to return

    Returns:
        Set of top N most frequent terms, excluding stopwords

    """
    # Normalize text: lowercase and split on whitespace/punctuation
    words = text.lower().split()

    # Filter: length, stopwords, and basic cleaning
    filtered_words = []
    for word in words:
        # Remove common punctuation
        cleaned = word.strip(".,!?;:()[]{}\"'`-_")
        # Keep if meets length requirement, not a stopword, and contains a letter
        if (
            len(cleaned) >= min_length
            and cleaned not in COMMON_STOPWORDS
            and any(c.isalpha() for c in cleaned)
        ):
            filtered_words.append(cleaned)

    # Count frequency and get top N
    term_counts = Counter(filtered_words)
    top_terms = {term for term, _ in term_counts.most_common(top_n)}

    logger.debug(
        f"Extracted {len(top_terms)} key terms from {len(words)} total words "
        f"(filtered to {len(filtered_words)} candidates)"
    )

    return top_terms


def calculate_grounding_score(source_terms: set[str], output_terms: set[str]) -> float:
    """Calculate how well output terms are grounded in source terms.

    Args:
        source_terms: Key terms from source content
        output_terms: Key terms from generated output

    Returns:
        Float 0.0-1.0 representing overlap ratio (1.0 = all output terms present in source)

    """
    if not output_terms:
        logger.warning("No output terms provided for grounding calculation")
        return 0.0

    overlap = source_terms & output_terms
    score = len(overlap) / len(output_terms)

    logger.debug(f"Grounding score: {score:.2%} ({len(overlap)}/{len(output_terms)} terms overlap)")

    return score


def validate_grounding(
    source_content: str,
    generated_content: str,
    min_overlap: float = 0.15,
) -> tuple[bool, float, list[str]]:
    """Validate that generated content is grounded in source content.

    Prevents hallucinations by ensuring generated output contains primarily terms
    that appear in the source material.

    Args:
        source_content: Original source text (ground truth)
        generated_content: LLM-generated synthesis output
        min_overlap: Minimum overlap ratio required (default 0.15 = 15%)

    Returns:
        Tuple of (is_grounded, score, warnings):
            - is_grounded: True if score >= min_overlap
            - score: Grounding score (0.0-1.0)
            - warnings: List of warning messages if ungrounded

    """
    logger.info(
        f"Validating grounding (min_overlap={min_overlap:.1%}, "
        f"source_len={len(source_content)}, generated_len={len(generated_content)})"
    )

    # Extract key terms from both texts
    source_terms = extract_key_terms(source_content)
    output_terms = extract_key_terms(generated_content)

    # Calculate grounding score
    score = calculate_grounding_score(source_terms, output_terms)

    # Validate against threshold
    is_grounded = score >= min_overlap
    warnings: list[str] = []

    if not is_grounded:
        # Identify ungrounded terms (present in output but not source)
        ungrounded_terms = output_terms - source_terms

        warning_msg = (
            f"Generated content may contain hallucinations. "
            f"Grounding score: {score:.1%} (threshold: {min_overlap:.1%}). "
            f"Found {len(ungrounded_terms)} ungrounded terms out of {len(output_terms)} total."
        )
        warnings.append(warning_msg)

        # Log sample of ungrounded terms for debugging
        sample_ungrounded = list(ungrounded_terms)[:10]
        logger.warning(f"{warning_msg} Sample ungrounded terms: {', '.join(sample_ungrounded)}")
    else:
        logger.info(f"Content is well-grounded. Score: {score:.1%} (threshold: {min_overlap:.1%})")

    return (is_grounded, score, warnings)
