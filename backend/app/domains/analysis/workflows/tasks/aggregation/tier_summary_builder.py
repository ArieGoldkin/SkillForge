"""Tier summary builder for Sequential Tier Learning (Issue #588).

This module compresses agent findings into lightweight tier summaries
that can be passed as context to later-tier agents. This reduces LLM
context overhead while preserving key insights.

No LLM calls - uses pure Python extraction and compression patterns
similar to compress_findings.py.
"""

from app.core.logging import get_logger
from app.domains.analysis.workflows.tier_types import TierSummary
from app.shared.types.workflow_types import AgentFinding

logger = get_logger(__name__)

# Token budget constraints (chars / 4 approximation)
MAX_TIER_SUMMARY_TOKENS = 800  # Maximum tokens for a tier summary
CHARS_PER_TOKEN = 4  # Rough approximation for English text
MAX_TIER_SUMMARY_CHARS = MAX_TIER_SUMMARY_TOKENS * CHARS_PER_TOKEN

# Content limits to prevent over-compression
MAX_FINDINGS_PER_AGENT = 3  # Extract up to 3 key findings per agent
MAX_RISKS_PER_AGENT = 2  # Extract up to 2 risks per agent
MAX_RECOMMENDATIONS_PER_AGENT = 2  # Extract up to 2 recommendations per agent
MAX_ITEM_LENGTH = 200  # Maximum characters per individual item
MIN_MEANINGFUL_TEXT_LENGTH = 20  # Minimum characters for meaningful text truncation


def _estimate_tokens(text: str) -> int:
    """Estimate token count for a string.

    Uses rough approximation of 1 token ≈ 4 characters for English text.
    This is conservative - actual tokenization may differ.

    Args:
        text: Input text to estimate

    Returns:
        Estimated token count

    Example:
        >>> _estimate_tokens("Hello world")
        2
        >>> _estimate_tokens("A" * 100)
        25

    """
    return len(text) // CHARS_PER_TOKEN


def _extract_from_list(value: list, max_items: int) -> list[str]:
    """Extract text items from a list value.

    Args:
        value: List to extract from
        max_items: Maximum items to extract

    Returns:
        List of extracted strings

    """
    results: list[str] = []
    for item in value[:max_items]:
        if isinstance(item, str):
            results.append(item[:MAX_ITEM_LENGTH])
        elif isinstance(item, dict):
            # Extract first string value from dict
            for v in item.values():
                if isinstance(v, str):
                    results.append(v[:MAX_ITEM_LENGTH])
                    break
    return results


def _extract_from_findings_dict(
    findings_data: dict, search_keys: list[str], max_items: int
) -> list[str]:
    """Extract items from findings dictionary using search keys.

    Args:
        findings_data: Dictionary to search
        search_keys: List of keys to look for
        max_items: Maximum items to extract

    Returns:
        List of extracted strings

    """
    for key in search_keys:
        if key not in findings_data:
            continue

        value = findings_data[key]
        if isinstance(value, list):
            results = _extract_from_list(value, max_items)
            if results:
                return results
        elif isinstance(value, str):
            return [value[:MAX_ITEM_LENGTH]]

    return []


def _extract_key_insights(finding: AgentFinding) -> list[str]:
    """Extract key insights from an agent finding.

    Looks for common insight patterns in agent findings:
    - Top-level keys that suggest insights (e.g., "key_points", "insights")
    - Nested findings with actionable information
    - Summary or overview fields

    Args:
        finding: Agent finding dictionary

    Returns:
        List of key insight strings (up to MAX_FINDINGS_PER_AGENT)

    Example:
        >>> finding = {
        ...     "agent_type": "key_insights",
        ...     "findings": {
        ...         "main_topics": ["RAG", "LangGraph"],
        ...         "key_points": ["Detailed RAG tutorial", "Production patterns"],
        ...     },
        ... }
        >>> insights = _extract_key_insights(finding)
        >>> len(insights) <= 3
        True

    """
    findings_data = finding.get("findings", {})

    if not findings_data or not isinstance(findings_data, dict):
        return []

    # Common keys that contain insights
    insight_keys = [
        "key_points",
        "insights",
        "key_insights",
        "main_findings",
        "summary",
        "overview",
        "main_topics",
        "highlights",
    ]

    # Extract from known insight keys
    insights = _extract_from_findings_dict(findings_data, insight_keys, MAX_FINDINGS_PER_AGENT)

    # Fallback: extract from top-level findings if no insights found
    if not insights:
        for key, value in list(findings_data.items())[:MAX_FINDINGS_PER_AGENT]:
            if isinstance(value, str) and len(value) > 0:
                insights.append(f"{key}: {value[:MAX_ITEM_LENGTH]}")
            elif isinstance(value, list) and len(value) > 0:
                insights.append(f"{key}: {len(value)} items found")
            elif isinstance(value, dict) and len(value) > 0:
                insights.append(f"{key}: {len(value)} fields analyzed")

    return insights[:MAX_FINDINGS_PER_AGENT]


def _extract_risks(finding: AgentFinding) -> list[str]:
    """Extract risks from an agent finding.

    Looks for security, performance, technical, or operational risks
    in agent findings.

    Args:
        finding: Agent finding dictionary

    Returns:
        List of risk strings (up to MAX_RISKS_PER_AGENT)

    Example:
        >>> finding = {
        ...     "agent_type": "security_auditor",
        ...     "findings": {
        ...         "risks": ["SQL injection vulnerability", "Weak authentication"],
        ...         "warnings": ["Deprecated API usage"],
        ...     },
        ... }
        >>> risks = _extract_risks(finding)
        >>> len(risks) <= 2
        True

    """
    findings_data = finding.get("findings", {})

    if not findings_data or not isinstance(findings_data, dict):
        return []

    # Common keys that contain risks
    risk_keys = [
        "risks",
        "security_risks",
        "vulnerabilities",
        "warnings",
        "concerns",
        "issues",
        "problems",
        "threats",
        "weaknesses",
    ]

    # Extract from known risk keys
    return _extract_from_findings_dict(findings_data, risk_keys, MAX_RISKS_PER_AGENT)


def _extract_recommendations(finding: AgentFinding) -> list[str]:
    """Extract recommendations from an agent finding.

    Looks for actionable recommendations, best practices, or
    suggested improvements.

    Args:
        finding: Agent finding dictionary

    Returns:
        List of recommendation strings (up to MAX_RECOMMENDATIONS_PER_AGENT)

    Example:
        >>> finding = {
        ...     "agent_type": "impl_planner",
        ...     "findings": {
        ...         "recommendations": ["Use async/await", "Add caching layer"],
        ...         "best_practices": ["Type hints", "Error handling"],
        ...     },
        ... }
        >>> recs = _extract_recommendations(finding)
        >>> len(recs) <= 2
        True

    """
    findings_data = finding.get("findings", {})

    if not findings_data or not isinstance(findings_data, dict):
        return []

    # Common keys that contain recommendations
    rec_keys = [
        "recommendations",
        "suggestions",
        "best_practices",
        "action_items",
        "next_steps",
        "improvements",
        "advice",
        "tips",
    ]

    # Extract from known recommendation keys
    return _extract_from_findings_dict(findings_data, rec_keys, MAX_RECOMMENDATIONS_PER_AGENT)


def build_tier_summary(
    findings: list[AgentFinding],
    tier: int,
    max_tokens: int = MAX_TIER_SUMMARY_TOKENS,
) -> TierSummary:
    """Build a compressed summary of findings from a tier of agents.

    Extracts key insights, risks, and recommendations from all agent
    findings in a tier, compressing them to fit within the token budget.

    This function performs pure extraction without LLM calls, following
    patterns from compress_findings.py.

    Args:
        findings: List of agent findings from this tier
        tier: Tier number (1, 2, or 3)
        max_tokens: Maximum token budget for the summary (default: 800)

    Returns:
        TierSummary with compressed findings

    Example:
        >>> findings = [
        ...     {
        ...         "agent_type": "key_insights",
        ...         "findings": {"key_points": ["RAG tutorial", "LangGraph patterns"]},
        ...     },
        ...     {"agent_type": "security_auditor", "findings": {"risks": ["SQL injection risk"]}},
        ... ]
        >>> summary = build_tier_summary(findings, tier=1, max_tokens=500)
        >>> summary["token_estimate"] <= 500
        True
        >>> "key_insights" in summary["agent_sources"]
        True

    """
    logger.debug(
        "building_tier_summary",
        tier=tier,
        finding_count=len(findings),
        max_tokens=max_tokens,
    )

    # Initialize summary structure
    all_key_findings: list[str] = []
    all_risks: list[str] = []
    all_recommendations: list[str] = []
    agent_sources: list[str] = []

    # Extract from each finding
    for finding in findings:
        if not finding or not isinstance(finding, dict):
            continue

        agent_type = finding.get("agent_type", "unknown")
        agent_sources.append(agent_type)

        # Extract key insights
        insights = _extract_key_insights(finding)
        all_key_findings.extend(insights)

        # Extract risks
        risks = _extract_risks(finding)
        all_risks.extend(risks)

        # Extract recommendations
        recommendations = _extract_recommendations(finding)
        all_recommendations.extend(recommendations)

    # Build summary and check token budget
    max_chars = max_tokens * CHARS_PER_TOKEN
    summary: TierSummary = {
        "key_findings": all_key_findings,
        "risks_identified": all_risks,
        "recommendations": all_recommendations,
        "agent_sources": agent_sources,
        "token_estimate": 0,
    }

    # Calculate current token estimate
    total_text = (
        " ".join(all_key_findings)
        + " ".join(all_risks)
        + " ".join(all_recommendations)
        + " ".join(agent_sources)
    )
    current_tokens = _estimate_tokens(total_text)

    # Compress if over budget
    if current_tokens > max_tokens:
        logger.info(
            "tier_summary_over_budget",
            tier=tier,
            current_tokens=current_tokens,
            max_tokens=max_tokens,
            compression_needed=True,
        )

        # Truncate each section proportionally
        # Allocate 50% to findings, 25% to risks, 25% to recommendations
        finding_budget = int(max_chars * 0.50)
        risk_budget = int(max_chars * 0.25)
        rec_budget = int(max_chars * 0.25)

        summary["key_findings"] = _truncate_to_budget(all_key_findings, finding_budget)
        summary["risks_identified"] = _truncate_to_budget(all_risks, risk_budget)
        summary["recommendations"] = _truncate_to_budget(all_recommendations, rec_budget)

        # Recalculate token estimate
        total_text = (
            " ".join(summary["key_findings"])
            + " ".join(summary["risks_identified"])
            + " ".join(summary["recommendations"])
            + " ".join(agent_sources)
        )
        current_tokens = _estimate_tokens(total_text)

    summary["token_estimate"] = current_tokens

    logger.info(
        "tier_summary_built",
        tier=tier,
        finding_count=len(findings),
        key_findings_count=len(summary["key_findings"]),
        risks_count=len(summary["risks_identified"]),
        recommendations_count=len(summary["recommendations"]),
        agent_count=len(agent_sources),
        token_estimate=current_tokens,
    )

    return summary


def _truncate_to_budget(items: list[str], char_budget: int) -> list[str]:
    """Truncate a list of items to fit within a character budget.

    Takes items from the list until the budget is exceeded,
    then truncates the last item to fit.

    Args:
        items: List of strings to truncate
        char_budget: Maximum total characters allowed

    Returns:
        Truncated list of items

    Example:
        >>> items = ["First finding", "Second finding", "Third finding"]
        >>> truncated = _truncate_to_budget(items, 30)
        >>> len(" ".join(truncated)) <= 30
        True

    """
    if not items:
        return []

    result: list[str] = []
    current_chars = 0

    for item in items:
        item_len = len(item)

        # Check if adding this item would exceed budget
        if current_chars + item_len + len(result) > char_budget:  # +len(result) for spaces
            # Try to fit a truncated version
            remaining_budget = char_budget - current_chars - len(result)
            if (
                remaining_budget > MIN_MEANINGFUL_TEXT_LENGTH
            ):  # Only add if we can fit meaningful text
                truncated = item[: remaining_budget - 3] + "..."
                result.append(truncated)
            break

        result.append(item)
        current_chars += item_len

    return result


def format_tier_context(
    tier1_summary: TierSummary | None = None,
    tier2_summary: TierSummary | None = None,
) -> str:
    """Format tier summaries as narrative context for injection into agent prompts.

    Converts structured tier summaries into a readable narrative format
    that can be prepended to later-tier agent prompts.

    Args:
        tier1_summary: Optional summary from Tier 1 agents
        tier2_summary: Optional summary from Tier 2 agents

    Returns:
        Formatted context string (empty if no summaries available)

    Example:
        >>> tier1 = {
        ...     "key_findings": ["RAG tutorial", "Intermediate level"],
        ...     "risks_identified": ["Complex vector DB setup"],
        ...     "recommendations": ["Start with simple patterns"],
        ...     "agent_sources": ["key_insights"],
        ...     "token_estimate": 500,
        ... }
        >>> context = format_tier_context(tier1_summary=tier1)
        >>> "Previous analysis identified" in context
        True
        >>> "RAG tutorial" in context
        True

    """
    if not tier1_summary and not tier2_summary:
        return ""

    sections: list[str] = []
    sections.append("## Previous Analysis Context\n")

    # Format Tier 1 summary if available
    if tier1_summary:
        sections.append("### Foundational Analysis (Tier 1)\n")

        if tier1_summary.get("key_findings"):
            sections.append("**Key Insights:**")
            sections.extend(f"- {finding}" for finding in tier1_summary["key_findings"])
            sections.append("")

        if tier1_summary.get("risks_identified"):
            sections.append("**Risks Identified:**")
            sections.extend(f"- {risk}" for risk in tier1_summary["risks_identified"])
            sections.append("")

        if tier1_summary.get("recommendations"):
            sections.append("**Recommendations:**")
            sections.extend(f"- {rec}" for rec in tier1_summary["recommendations"])
            sections.append("")

    # Format Tier 2 summary if available
    if tier2_summary:
        sections.append("### Technical Analysis (Tier 2)\n")

        if tier2_summary.get("key_findings"):
            sections.append("**Technical Insights:**")
            sections.extend(f"- {finding}" for finding in tier2_summary["key_findings"])
            sections.append("")

        if tier2_summary.get("risks_identified"):
            sections.append("**Technical Risks:**")
            sections.extend(f"- {risk}" for risk in tier2_summary["risks_identified"])
            sections.append("")

        if tier2_summary.get("recommendations"):
            sections.append("**Technical Recommendations:**")
            sections.extend(f"- {rec}" for rec in tier2_summary["recommendations"])
            sections.append("")

    sections.append(
        "**Note:** Use this context to inform your analysis. "
        "Build upon these insights rather than duplicating them.\n"
    )

    return "\n".join(sections)
