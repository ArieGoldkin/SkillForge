"""Content type detection utilities for agent routing.

This module provides utilities to detect content types and determine
which agents can process specific content types.
"""

import re
from typing import Literal

from app.core.logging import get_logger

logger = get_logger(__name__)

# Content type definitions
ContentType = Literal[
    "code", "changelog", "documentation", "article", "news", "video", "repo", "unknown"
]


def detect_content_type(content: str, content_type_hint: str | None = None) -> ContentType:  # noqa: PLR0911 - Multiple return paths for content type detection
    """Detect content type from content string.

    Uses heuristics to identify content type:
    - Code: Contains code blocks, imports, function definitions
    - Changelog: Contains version numbers, dates, "Added", "Fixed", etc.
    - Documentation: Markdown headers, API docs, tutorials
    - Article: General text content
    - Video: Transcript patterns
    - Repo: Repository structure, file listings

    Args:
        content: Content string to analyze
        content_type_hint: Optional hint from extraction metadata

    Returns:
        Detected content type

    """
    if not content or len(content.strip()) < 50:  # noqa: PLR2004 - Minimum content length threshold
        return "unknown"

    content_lower = content.lower()
    content_first_500 = content[:500]

    # Check for code patterns
    code_patterns = [
        r"^import\s+\w+",  # Python imports
        r"^from\s+\w+\s+import",  # Python from imports
        r"^def\s+\w+\s*\(",  # Function definitions
        r"^class\s+\w+",  # Class definitions
        r"^\s*\{",  # JSON/object start
        r"^\s*function\s+\w+",  # JavaScript functions
        r"^\s*const\s+\w+\s*=",  # JavaScript const
        r"^\s*public\s+class",  # Java classes
        r"```\w+",  # Code blocks
    ]

    code_score = sum(
        1 for pattern in code_patterns if re.search(pattern, content_first_500, re.MULTILINE)
    )

    # Check for changelog patterns
    changelog_patterns = [
        r"##?\s*\[?\d+\.\d+\.\d+\]?",  # Version numbers
        r"^\s*\d{4}-\d{2}-\d{2}",  # Dates
        r"###?\s*(added|fixed|changed|removed|deprecated)",  # Changelog headers
        r"^\s*-\s*(added|fixed|changed|removed)",  # Changelog items
        r"changelog|release notes|what's new",
    ]

    changelog_score = sum(
        1 for pattern in changelog_patterns if re.search(pattern, content_lower, re.MULTILINE)
    )

    # Check for documentation patterns
    doc_patterns = [
        r"^#+\s+\w+",  # Markdown headers
        r"```\w+",  # Code blocks in docs
        r"api\s+reference|documentation|tutorial|guide",
        r"^\s*\|.*\|",  # Tables
        r"getting\s+started",  # Tutorial indicators
        r"pip\s+install|npm\s+install",  # Package installation commands
        r"step\s+\d+|step-by-step",  # Step-by-step instructions
    ]

    doc_score = sum(
        1 for pattern in doc_patterns if re.search(pattern, content_lower, re.MULTILINE)
    )

    # Check for news/announcement patterns (Issue #490)
    # News content should route to only 2 agents (trend_validator, tech_comparator)
    news_patterns = [
        r"\bannounced?\b|\bannouncing\b|\bannouncement\b",  # Announcement keywords
        r"\blaunched?\b|\blaunching\b|\blaunch\s+of\b",  # Launch keywords
        r"\bunveiled?\b|\bunveiling\b",  # Unveiling keywords
        r"\bintroduces?\b|\bintroducing\b|\bnow\s+introducing\b",  # Introduction keywords
        r"\bbreaking:?\s|\bbreaking\s+news\b",  # Breaking news
        r"\bpress\s+release\b|\bkeynote\b",  # Press/keynote
        r"\bnow\s+available\b|\bavailable\s+(now|today)\b",  # Availability announcements
        r"\bpartnership\b|\bacquisition\b|\bmerger\b",  # Business news
        r"\bnew\s+(feature|product|service|tool|model|version)\b",  # New product keywords
    ]

    news_score = sum(
        1 for pattern in news_patterns if re.search(pattern, content_lower, re.MULTILINE)
    )

    # Use hint if provided and matches patterns
    if content_type_hint:
        hint_lower = content_type_hint.lower()
        if hint_lower in ("code", "changelog", "documentation", "article", "news", "video", "repo"):
            # Validate hint matches patterns
            if hint_lower == "code" and code_score >= 2:  # noqa: PLR2004 - Score threshold for hint validation
                return "code"
            if hint_lower == "changelog" and changelog_score >= 2:  # noqa: PLR2004 - Score threshold for hint validation
                return "changelog"
            if hint_lower == "documentation" and doc_score >= 2:  # noqa: PLR2004 - Score threshold for hint validation
                return "documentation"
            if hint_lower == "news" and news_score >= 2:  # noqa: PLR2004 - Score threshold for hint validation
                return "news"
            if hint_lower in ("article", "video", "repo"):
                return hint_lower  # type: ignore[return-value]

    # Score-based detection
    if code_score >= 3:  # noqa: PLR2004 - Score threshold for content type detection
        return "code"
    if changelog_score >= 3:  # noqa: PLR2004 - Score threshold for content type detection
        return "changelog"
    if doc_score >= 2:  # noqa: PLR2004 - Lowered from 3 to 2 to better detect tutorials with code blocks
        return "documentation"

    # Check for news/announcement content BEFORE defaulting to article (Issue #490)
    # News requires: news patterns present AND low code/tutorial signals
    # This ensures technical content isn't misclassified as news
    if news_score >= 2 and code_score < 2 and doc_score < 2:  # noqa: PLR2004 - Score thresholds for news detection
        return "news"

    # Default to article for general text
    return "article"


# Agent capability mapping: which agents can process which content types
# NOTE: Technical articles often discuss security, performance, and implementation
# topics, so most analytical agents should be able to process "article" content.
# Only code_quality_critic is restricted to actual code since it performs
# structural analysis that requires parseable source code.
# dependency_mapper can extract dependency information from prose descriptions
# in tutorials and documentation (e.g., "Install with pip install fastapi").
#
# Issue #490: "news" content type is restricted to only trend_validator and
# tech_comparator (2 agents) since news/announcements don't need implementation
# analysis, security audits, or performance evaluation.
AGENT_CAPABILITIES: dict[str, list[ContentType]] = {
    "tech_comparator": [
        "code",
        "documentation",
        "article",
        "changelog",
        "news",
    ],  # News: industry context
    "security_auditor": ["code", "documentation", "article"],  # No news - no security to audit
    "implementation_planner": ["code", "documentation", "article"],  # No news - no impl details
    "performance_analyst": ["code", "documentation", "article"],  # No news - no benchmarks
    "code_quality_critic": ["code"],  # Only code - requires structural analysis
    "trend_validator": [
        "code",
        "documentation",
        "article",
        "changelog",
        "news",
    ],  # News: trend analysis
    "dependency_mapper": ["code", "documentation", "article"],  # No news - no dependencies
    "integration_feasibility": ["code", "documentation", "article"],  # No news - no integration
}


def can_agent_process_content(agent_name: str, content_type: ContentType) -> bool:
    """Check if agent can process this content type.

    Args:
        agent_name: Name of the agent (e.g., "code_quality_critic")
        content_type: Detected content type

    Returns:
        True if agent can process this content type, False otherwise

    """
    capabilities = AGENT_CAPABILITIES.get(agent_name, [])
    return content_type in capabilities


def filter_agents_by_content_type(
    agent_names: list[str], content_type: ContentType
) -> tuple[list[str], list[str]]:
    """Filter agents based on content type capabilities.

    Args:
        agent_names: List of agent names to filter
        content_type: Detected content type

    Returns:
        Tuple of (filtered_agents, skipped_agents)

    """
    filtered: list[str] = []
    skipped: list[str] = []

    for agent_name in agent_names:
        if can_agent_process_content(agent_name, content_type):
            filtered.append(agent_name)
        else:
            skipped.append(agent_name)
            logger.debug(
                "agent_skipped_content_type",
                agent_name=agent_name,
                content_type=content_type,
                reason="agent_cannot_process_content_type",
            )

    return filtered, skipped
