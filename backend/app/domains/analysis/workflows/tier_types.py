"""Type definitions for Sequential Tier Learning (Issue #588).

This module defines types for inter-tier context passing, enabling
agents in later tiers to receive compressed findings from earlier tiers.

The tiered execution model reduces LLM context overhead by:
1. Running Tier 1 agents first (foundational analysis)
2. Summarizing their findings to ~500-800 tokens
3. Passing summaries to Tier 2/3 agents instead of raw content

This enables later-tier agents to build on earlier insights without
overwhelming context windows with redundant information.
"""

from typing import TypedDict


class TierSummary(TypedDict, total=False):
    """Compressed findings from a tier of agents.

    This structure contains synthesized insights from all agents in a tier,
    compressed to ~500-800 tokens for efficient context passing to later tiers.

    Attributes:
        key_findings: List of key findings from this tier
        risks_identified: Security, performance, or technical risks identified
        recommendations: Actionable recommendations from this tier
        agent_sources: Names of agents that contributed to this summary
        token_estimate: Estimated token count of this summary

    Example:
        >>> tier1_summary: TierSummary = {
        ...     "key_findings": [
        ...         "Content focuses on RAG with LangGraph",
        ...         "Requires intermediate Python knowledge",
        ...     ],
        ...     "risks_identified": ["Vector database complexity"],
        ...     "recommendations": ["Start with simple retrieval patterns"],
        ...     "agent_sources": ["key_insights", "audience_fit"],
        ...     "token_estimate": 650,
        ... }

    """

    key_findings: list[str]
    risks_identified: list[str]
    recommendations: list[str]
    agent_sources: list[str]
    token_estimate: int


# Tier assignment constants
# Tier 1: Foundational analysis - general insights, audience fit, actionability
TIER_1_AGENTS = ["key_insights", "pros_cons", "audience_fit", "actionable"]

# Tier 2: Technical deep-dive - security, performance, implementation details
TIER_2_AGENTS = [
    "tech_comparator",
    "security_auditor",
    "implementation_planner",
    "performance_analyst",
    "code_quality_critic",
    "trend_validator",
    "dependency_mapper",
    "integration_feasibility",
]

# Tier 3: Strategic context - research depth, community insights, learning paths
TIER_3_AGENTS = [
    "deep_researcher",
    "community_pulse",
    "knowledge_curator",
    "learning_path_advisor",
]

# Master tier assignment mapping
TIER_ASSIGNMENTS: dict[str, int] = {
    # Tier 1: Foundational analysis
    "key_insights": 1,
    "pros_cons": 1,
    "audience_fit": 1,
    "actionable": 1,
    # Tier 2: Technical deep-dive
    "tech_comparator": 2,
    "security_auditor": 2,
    "implementation_planner": 2,
    "performance_analyst": 2,
    "code_quality_critic": 2,
    "trend_validator": 2,
    "dependency_mapper": 2,
    "integration_feasibility": 2,
    # Tier 3: Strategic context
    "deep_researcher": 3,
    "community_pulse": 3,
    "knowledge_curator": 3,
    "learning_path_advisor": 3,
}


def get_agent_tier(agent_name: str) -> int | None:
    """Get the tier number for a given agent.

    Args:
        agent_name: Name of the agent

    Returns:
        Tier number (1, 2, or 3) if agent is assigned, None otherwise

    Example:
        >>> get_agent_tier("key_insights")
        1
        >>> get_agent_tier("security_auditor")
        2
        >>> get_agent_tier("unknown_agent")
        None

    """
    return TIER_ASSIGNMENTS.get(agent_name)


def get_agents_for_tier(tier: int) -> list[str]:
    """Get all agents assigned to a specific tier.

    Args:
        tier: Tier number (1, 2, or 3)

    Returns:
        List of agent names assigned to this tier

    Example:
        >>> get_agents_for_tier(1)
        ['key_insights', 'pros_cons', 'audience_fit', 'actionable']

    """
    tier_map: dict[int, list[str]] = {
        1: TIER_1_AGENTS,
        2: TIER_2_AGENTS,
        3: TIER_3_AGENTS,
    }
    return tier_map.get(tier, [])
