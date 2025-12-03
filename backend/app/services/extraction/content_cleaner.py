"""Content cleaning utilities for extracted content.

This module provides utilities to clean extracted markdown content by removing
boilerplate elements like cookie consent banners, navigation menus, footers,
and other non-article content.
"""

import re

from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum reduction percentage to log cleaning metrics
SIGNIFICANT_REDUCTION_THRESHOLD = 5

# Patterns for content that should be removed (case-insensitive)
BOILERPLATE_PATTERNS = [
    # Cookie consent / GDPR
    r"(?:^|\n).*?cookie(?:bot|s?).*?(?:\n|$)",
    r"(?:^|\n).*?(?:we use cookies|this (?:website|site) uses cookies).*?(?:\n|$)",
    r"(?:^|\n).*?(?:consent|gdpr|privacy policy|cookie policy).*?(?:\n|$)",
    r"(?:^|\n)\s*\*?\s*\[?\s*(?:necessary|preferences|statistics|marketing)\s*\]?\s*-?\s*\[?[x ]?\]?\s*(?:\n|$)",
    # Navigation elements
    r"(?:^|\n)\s*\[(?:skip to (?:content|main)|menu|navigation)\].*?(?:\n|$)",
    r"(?:^|\n)\s*\*\s*\[(?:home|about|contact|blog|pricing|features|docs)\].*?(?:\n|$)",
    # Social media / sharing
    r"(?:^|\n).*?(?:share (?:on|this)|follow us|connect with us).*?(?:\n|$)",
    r"(?:^|\n)\s*\[?\s*(?:twitter|facebook|linkedin|instagram|youtube)\s*\]?.*?(?:\n|$)",
    # Footer elements
    r"(?:^|\n).*?(?:all rights reserved|copyright ©|\d{4} (?:all rights|©)).*?(?:\n|$)",
    r"(?:^|\n).*?(?:terms (?:of (?:service|use))|privacy policy|legal).*?(?:\n|$)",
    # Newsletter / subscription
    r"(?:^|\n).*?(?:subscribe to (?:our|the)|sign up for|get (?:our|the) newsletter).*?(?:\n|$)",
    # Ads / promotions
    r"(?:^|\n).*?(?:advertisement|sponsored|promoted).*?(?:\n|$)",
    # Blob URLs (local/broken images)
    r"\!\[.*?\]\(blob:.*?\)",
    # Empty image references
    r"\!\[Image \d+:.*?\]\((?:blob:)?.*?\)",
]

# Patterns for lines that indicate start of main content
MAIN_CONTENT_INDICATORS = [
    r"^#{1,3}\s+\w",  # Markdown headers (h1-h3)
    r"^>\s+",  # Blockquotes (often used for TL;DR or intro)
    r"^(?:In this|This (?:article|post|guide)|Today|Let's|We'll)",  # Common article starts
]

# Patterns for lines that indicate end of main content
END_CONTENT_INDICATORS = [
    r"^#{1,3}\s*(?:related|more|recommended|popular|trending)",
    r"^#{1,3}\s*(?:comments?|discussion|replies)",
    r"^#{1,3}\s*(?:about the author|author bio|written by)",
    r"^#{1,3}\s*(?:share this|spread the word)",
    r"^#{1,3}\s*(?:newsletter|subscribe|sign up)",
    r"^#{1,3}\s*(?:footer|sidebar|widget)",
]


def clean_extracted_content(content: str) -> str:
    """Clean extracted markdown content by removing boilerplate.

    This function removes:
    - Cookie consent banners and GDPR notices
    - Navigation menus and skip links
    - Social media sharing buttons
    - Footer elements (copyright, terms, privacy)
    - Newsletter signup prompts
    - Broken blob: image URLs
    - Trailing boilerplate after main content

    Args:
        content: Raw markdown content from extraction

    Returns:
        Cleaned markdown content with boilerplate removed

    """
    if not content:
        return content

    original_length = len(content)
    cleaned = content

    # Apply boilerplate removal patterns
    for pattern in BOILERPLATE_PATTERNS:
        cleaned = re.sub(pattern, "\n", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # Remove consecutive empty lines (more than 2)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    # Try to find and trim after end-of-content indicators
    lines = cleaned.split("\n")
    trimmed_lines = []
    found_main_content = False

    for _i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Check if this line indicates end of main content
        is_end_indicator = any(
            re.match(pattern, line_lower, re.IGNORECASE) for pattern in END_CONTENT_INDICATORS
        )

        if is_end_indicator and found_main_content:
            # Stop processing - we've reached boilerplate at the end
            break

        # Check if we've found main content
        if not found_main_content:
            for pattern in MAIN_CONTENT_INDICATORS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    found_main_content = True
                    break

        trimmed_lines.append(line)

    cleaned = "\n".join(trimmed_lines)

    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()

    # Log cleaning metrics
    cleaned_length = len(cleaned)
    reduction_pct = ((original_length - cleaned_length) / original_length * 100) if original_length > 0 else 0

    if reduction_pct > SIGNIFICANT_REDUCTION_THRESHOLD:  # Only log if significant cleaning occurred
        logger.info(
            "content_cleaned",
            original_length=original_length,
            cleaned_length=cleaned_length,
            reduction_percent=round(reduction_pct, 1),
            found_main_content=found_main_content,
        )

    return cleaned


def extract_main_content(content: str, min_paragraph_length: int = 100) -> str:
    """Extract main article content using heuristics.

    This is a more aggressive extraction that tries to identify
    the actual article body by looking for substantial paragraphs.

    Args:
        content: Raw or pre-cleaned markdown content
        min_paragraph_length: Minimum length for a paragraph to be considered main content

    Returns:
        Extracted main content

    """
    if not content:
        return content

    # First apply basic cleaning
    cleaned = clean_extracted_content(content)

    # Split into paragraphs (separated by blank lines)
    paragraphs = re.split(r"\n\s*\n", cleaned)

    # Filter to substantial paragraphs
    main_paragraphs = []
    for para in paragraphs:
        stripped_para = para.strip()
        # Include headers and substantial paragraphs
        if stripped_para.startswith("#") or len(stripped_para) >= min_paragraph_length:
            main_paragraphs.append(stripped_para)

    return "\n\n".join(main_paragraphs)
