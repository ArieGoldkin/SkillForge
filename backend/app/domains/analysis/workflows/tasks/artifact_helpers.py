"""Helper functions for artifact generation.

This module provides utility functions for extracting metadata, generating
filenames, and building Claude Code prompts for artifacts.
"""

import re
from collections.abc import Mapping
from typing import Any

from app.core.logging import get_logger
from app.core.tech_keywords import TECH_KEYWORDS
from app.domains.analysis.workflows.state_types import AggregatedInsights
from app.shared.types import AgentFinding

logger = get_logger(__name__)

# Complexity calculation constants
MIN_AGENTS_FOR_ADVANCED = 6
MIN_CONFIDENCE_FOR_ADVANCED = 0.85
MAX_AGENTS_FOR_SIMPLE = 5
MIN_CONFIDENCE_FOR_SIMPLE = 0.7
MAX_FILENAME_LENGTH = 100


def extract_artifact_metadata(
    aggregated_insights: AggregatedInsights | Mapping[str, Any],
    agent_findings: list[AgentFinding] | list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Extract topics and complexity from aggregated insights.

    Extracts topics from key_findings using simple keyword extraction.
    Calculates complexity based on agent count and confidence scores.

    Args:
        aggregated_insights: Aggregated insights dictionary
        agent_findings: List of agent finding dictionaries

    Returns:
        Dictionary with topics (list[str]) and complexity (str)

    """
    topics: list[str] = []
    complexity = "intermediate"

    # Extract topics from key_findings
    key_findings = aggregated_insights.get("key_findings", [])
    if isinstance(key_findings, list):
        for finding in key_findings:
            if isinstance(finding, str):
                # Simple keyword extraction: capitalize first word, extract tech names
                # Look for common tech keywords from centralized config
                finding_lower = finding.lower()
                for keyword in TECH_KEYWORDS:
                    if keyword in finding_lower and keyword.title() not in topics:
                        topics.append(keyword.title())

    # Limit topics to 5
    topics = topics[:5] if topics else ["General"]

    # Calculate complexity based on agent count and confidence
    agent_count = len(agent_findings)
    confidence_scores: list[float] = []
    for f in agent_findings:
        if isinstance(f, dict) and f.get("confidence_score") is not None:
            score = f.get("confidence_score", 0.0) or 0.0
            confidence_scores.append(float(score) if isinstance(score, (int, float, str)) else 0.0)
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

    # Complexity logic:
    # - Simple: <MAX_AGENTS_FOR_SIMPLE agents or avg_confidence <MIN_CONFIDENCE_FOR_SIMPLE
    # - Advanced: >MIN_AGENTS_FOR_ADVANCED agents and avg_confidence >MIN_CONFIDENCE_FOR_ADVANCED
    # - Intermediate: everything else
    if agent_count < MAX_AGENTS_FOR_SIMPLE or avg_confidence < MIN_CONFIDENCE_FOR_SIMPLE:
        complexity = "simple"
    elif agent_count > MIN_AGENTS_FOR_ADVANCED and avg_confidence > MIN_CONFIDENCE_FOR_ADVANCED:
        complexity = "advanced"
    else:
        complexity = "intermediate"

    return {
        "topics": topics,
        "complexity": complexity,
        "agent_count": agent_count,
        "avg_confidence": round(avg_confidence, 2),
    }


def generate_filename(title: str | None, analysis_id: str) -> str:
    """Generate filename from title or analysis ID.

    Slugifies the title by:
    - Converting to lowercase
    - Replacing spaces with hyphens
    - Removing special characters (keeping alphanumeric, hyphens, underscores)
    - Limiting length to 100 characters

    Args:
        title: Title string (can be None)
        analysis_id: Analysis ID as fallback

    Returns:
        Filename string ending in .md

    """
    if title:
        # Convert to lowercase
        slug = title.lower()

        # Replace spaces and special chars with hyphens
        slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special chars
        slug = re.sub(r"[-\s]+", "-", slug)  # Replace spaces/multiple hyphens with single hyphen
        slug = slug.strip("-")  # Remove leading/trailing hyphens

        # Limit length to MAX_FILENAME_LENGTH chars
        slug = slug[:MAX_FILENAME_LENGTH] if len(slug) > MAX_FILENAME_LENGTH else slug

        if slug:  # Only use if slug is not empty after processing
            return f"{slug}.md"

    # Fallback to analysis ID (first 8 chars)
    return f"analysis-{analysis_id[:8]}.md"


def build_claude_code_prompt(
    aggregated_insights: AggregatedInsights | Mapping[str, Any],
    analysis_metadata: Mapping[str, Any],
) -> str:
    """Build Claude Code prompt section from aggregated insights.

    Creates a copyable prompt that can be used with Claude Code or other
    AI coding assistants to implement the analyzed technology.

    Args:
        aggregated_insights: Aggregated insights dictionary
        analysis_metadata: Analysis metadata (url, title, etc.)

    Returns:
        Formatted prompt string

    """
    title = analysis_metadata.get("title", "this technology")
    url = analysis_metadata.get("url", "N/A")
    exec_summary = aggregated_insights.get("executive_summary", "")
    key_findings = aggregated_insights.get("key_findings", [])
    # ty can't chain .get() calls properly on TypedDict
    synthesis: dict[str, Any] = aggregated_insights.get("synthesis", {})  # type: ignore[assignment]
    implementation = (
        synthesis.get("implementation_guidance", "") if isinstance(synthesis, dict) else ""
    )  # type: ignore[union-attr]

    prompt_parts = [
        f"# Implementation Guide: {title}",
        "",
        f"**Source:** {url}",
        "",
        "## Summary",
        exec_summary or "No summary available.",
        "",
    ]

    if key_findings:
        prompt_parts.append("## Key Findings")
        for finding in key_findings[:5]:  # Limit to top 5
            if isinstance(finding, str):
                prompt_parts.append(f"- {finding}")  # noqa: PERF401
        prompt_parts.append("")

    if implementation:
        prompt_parts.append("## Implementation Guidance")
        prompt_parts.append(implementation)
        prompt_parts.append("")

    prompt_parts.append("## Task")
    prompt_parts.append("Implement this technology following the guidance above.")
    prompt_parts.append("")

    return "\n".join(prompt_parts)
