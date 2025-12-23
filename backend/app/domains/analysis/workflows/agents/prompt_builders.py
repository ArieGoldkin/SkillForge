"""Prompt building utilities for agents.

All prompt builders are pure functions for easy testing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.shared.workflows.utils.content_signals import ContentSignals


def build_agent_user_prompt(
    content: str,
    content_type: str,
    max_length: int = 12000,
    proactive_context: str = "",
) -> str:
    """Build user prompt for agent analysis.

    Issue #300: Supports proactive memory recall context injection.
    If proactive_context is provided, it is prepended to the content.

    Args:
        content: Full content text
        content_type: Type of content (article, video, repo)
        max_length: Maximum content length to include
        proactive_context: Formatted memory context from past analyses (optional)

    Returns:
        Formatted user prompt string with optional memory context

    """
    content_preview = content[:max_length] if len(content) > max_length else content
    base_prompt = f"Content Type: {content_type}\n\nContent:\n{content_preview}"

    # Prepend proactive context if available
    if proactive_context:
        return f"{proactive_context}\n---\n\n{base_prompt}"

    return base_prompt


def format_content_signals_for_prompt(signals: ContentSignals) -> str:
    """Format content signals as a readable summary for the supervisor LLM.

    Args:
        signals: ContentSignals dataclass with pre-computed signal detection

    Returns:
        Formatted string describing content signals and genre-specific routing guidelines

    """
    # Collect active boolean signals
    active_signals = []
    if signals.has_code_patterns:
        active_signals.append("code_patterns")
    if signals.has_benchmarks:
        active_signals.append("benchmarks")
    if signals.has_security_patterns:
        active_signals.append("security")
    if signals.has_architecture:
        active_signals.append("architecture")
    if signals.has_dependencies:
        active_signals.append("dependencies")
    if signals.has_comparisons:
        active_signals.append("comparisons")
    if signals.has_tutorials:
        active_signals.append("tutorials")

    # Build signals summary
    signals_str = ", ".join(active_signals) if active_signals else "none"

    # Genre-specific routing guidelines
    genre_guidelines = """
ROUTING GUIDELINES BY GENRE:
- RESEARCH: Expect concepts, not metrics. Agents should use OPPORTUNISTIC expectations.
  → Prefer: trend_validator, tech_comparator (2 agents minimum)
  → Avoid: Full implementation/security analysis unless explicitly present

- TUTORIAL: Expect code, steps, implementation. Full analysis appropriate.
  → Prefer: implementation_planner, dependency_mapper, security_auditor, performance_analyst
  → Minimum: 4 agents for comprehensive coverage

- OPINION: Expect subjective analysis. Focus on trends and comparisons.
  → Prefer: trend_validator, tech_comparator
  → Minimum: 1 agent sufficient (trend validation)

- REFERENCE: API docs, specifications. Standard coverage.
  → Prefer: implementation_planner, dependency_mapper, security_auditor
  → Minimum: 3 agents

- QUICKSTART: Getting started guides. Implementation focus.
  → Prefer: implementation_planner, dependency_mapper, trend_validator
  → Minimum: 3 agents

- CHANGELOG: Release notes, version history. Trend and comparison focus.
  → Prefer: trend_validator, tech_comparator
  → Minimum: 2 agents

- UNKNOWN: Default to standard routing.
  → Minimum: 3 agents"""

    return f"""
CONTENT ANALYSIS (pre-computed in <50ms via regex):
- Genre: {signals.detected_genre.value}
- Richness Score: {signals.content_richness_score:.1f}/10
- Word Count: {signals.word_count}
- Active Signals: {signals_str}
- Conceptual Only: {signals.has_conceptual_only}

{genre_guidelines}

NOTE: These signals were detected through fast regex patterns. Use them to guide your
routing decisions rather than re-analyzing the content for the same patterns.
"""


def build_supervisor_user_prompt(
    system_prompt: str,
    content: str,
    content_type: str,
    content_signals: ContentSignals | None = None,
) -> str:
    """Build user prompt for supervisor routing.

    Args:
        system_prompt: Supervisor system prompt
        content: Sized content for supervisor
        content_type: Type of content
        content_signals: Pre-computed content signals (optional, recommended)

    Returns:
        Formatted user prompt string with optional content signals summary

    """
    # Build base prompt
    base_prompt = f"{system_prompt}\n\nContent Type: {content_type}"

    # Add content signals summary if available
    if content_signals:
        signals_summary = format_content_signals_for_prompt(content_signals)
        base_prompt += f"\n{signals_summary}"

    # Add content at the end
    return f"{base_prompt}\n\nContent:\n{content}"
