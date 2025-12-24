"""Agent registry with tier metadata.

Manages agent tier classification for mode-based selection.
Tier 1 (Universal) agents always run, Tier 2 (Validation) adds tool-enabled
agents for Standard mode, Tier 3 (Research) includes memory-enabled deep
analysis for Deep Dive mode.

Issue #498: https://github.com/ArieGoldkin/SkillForge/issues/498
Depends on: #490 (Content-Type Routing)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class AgentTier(IntEnum):
    """Agent execution tier based on analysis mode.

    Tiers are cumulative - higher modes include all lower tier agents.

    Attributes:
        UNIVERSAL: Always run on ALL content (Quick mode+)
        VALIDATION: Tool-enabled agents (Standard mode+)
        RESEARCH: Deep dive only, memory-enabled (Deep Dive mode)

    """

    UNIVERSAL = 1
    VALIDATION = 2
    RESEARCH = 3


class AnalysisMode(str, Enum):
    """Analysis depth modes for agent selection."""

    QUICK = "quick"
    STANDARD = "standard"
    DEEP_DIVE = "deep_dive"


@dataclass(frozen=True)
class AgentMetadata:
    """Metadata for an analysis agent.

    Attributes:
        name: Agent display name (e.g., "KEY_INSIGHTS")
        tier: Execution tier (UNIVERSAL, VALIDATION, RESEARCH)
        tools: Optional list of MCP tool capabilities
        requires_memory: Whether agent needs memory injection

    """

    name: str
    tier: AgentTier
    tools: list[str] = field(default_factory=list)
    requires_memory: bool = False


# Agent Registry - Single source of truth for tier metadata
# Based on Issue #498 specification
AGENT_REGISTRY: dict[str, AgentMetadata] = {
    # ═══════════════════════════════════════════════════════════════════
    # TIER 1: UNIVERSAL - Always run on ALL content
    # ═══════════════════════════════════════════════════════════════════
    "key_insights": AgentMetadata(
        name="KEY_INSIGHTS",
        tier=AgentTier.UNIVERSAL,
    ),
    "pros_cons": AgentMetadata(
        name="PROS_CONS",
        tier=AgentTier.UNIVERSAL,
    ),
    "audience_fit": AgentMetadata(
        name="AUDIENCE_FIT",
        tier=AgentTier.UNIVERSAL,
    ),
    "actionable": AgentMetadata(
        name="ACTIONABLE",
        tier=AgentTier.UNIVERSAL,
    ),
    # ═══════════════════════════════════════════════════════════════════
    # TIER 2: VALIDATION - Tool-enabled, run on Standard+
    # ═══════════════════════════════════════════════════════════════════
    "fact_validator": AgentMetadata(
        name="FACT_VALIDATOR",
        tier=AgentTier.VALIDATION,
        tools=["tavily_search"],
    ),
    "source_credibility": AgentMetadata(
        name="SOURCE_CREDIBILITY",
        tier=AgentTier.VALIDATION,
    ),
    "freshness_checker": AgentMetadata(
        name="FRESHNESS_CHECKER",
        tier=AgentTier.VALIDATION,
        tools=["github_api", "npm_api"],
    ),
    "alternatives_finder": AgentMetadata(
        name="ALTERNATIVES_FINDER",
        tier=AgentTier.VALIDATION,
        tools=["tavily_search"],
    ),
    # ═══════════════════════════════════════════════════════════════════
    # TIER 3: RESEARCH - Deep dive only, memory-enabled
    # ═══════════════════════════════════════════════════════════════════
    "deep_researcher": AgentMetadata(
        name="DEEP_RESEARCHER",
        tier=AgentTier.RESEARCH,
        tools=["tavily_search"],
        requires_memory=True,
    ),
    "community_pulse": AgentMetadata(
        name="COMMUNITY_PULSE",
        tier=AgentTier.RESEARCH,
    ),
    "knowledge_curator": AgentMetadata(
        name="KNOWLEDGE_CURATOR",
        tier=AgentTier.RESEARCH,
        requires_memory=True,
    ),
    "learning_path_advisor": AgentMetadata(
        name="LEARNING_PATH_ADVISOR",
        tier=AgentTier.RESEARCH,
        requires_memory=True,
    ),
}


def get_agents_for_mode(mode: str | AnalysisMode) -> list[str]:
    """Return agent names based on analysis mode.

    Args:
        mode: Analysis depth mode (quick, standard, deep_dive)

    Returns:
        List of agent names available for this mode

    Raises:
        ValueError: If mode is not a valid AnalysisMode value

    Example:
        >>> get_agents_for_mode("quick")
        ['key_insights', 'pros_cons', 'audience_fit', 'actionable']
        >>> len(get_agents_for_mode("standard"))
        8
        >>> len(get_agents_for_mode("deep_dive"))
        12
        >>> get_agents_for_mode("invalid")
        Traceback (most recent call last):
            ...
        ValueError: Invalid analysis mode: 'invalid'. Valid modes: quick, standard, deep_dive

    """
    # Normalize to string for comparison
    mode_str = mode.value if isinstance(mode, AnalysisMode) else mode

    mode_to_tier = {
        AnalysisMode.QUICK.value: AgentTier.UNIVERSAL,
        AnalysisMode.STANDARD.value: AgentTier.VALIDATION,
        AnalysisMode.DEEP_DIVE.value: AgentTier.RESEARCH,
    }

    if mode_str not in mode_to_tier:
        valid_modes = ", ".join(m.value for m in AnalysisMode)
        msg = f"Invalid analysis mode: '{mode_str}'. Valid modes: {valid_modes}"
        raise ValueError(msg)

    max_tier = mode_to_tier[mode_str]
    return [name for name, meta in AGENT_REGISTRY.items() if meta.tier <= max_tier]


def get_agent_metadata(agent_name: str) -> AgentMetadata | None:
    """Get metadata for a specific agent.

    Args:
        agent_name: Agent identifier (e.g., "key_insights")

    Returns:
        AgentMetadata if found, None otherwise

    """
    return AGENT_REGISTRY.get(agent_name)


def get_tool_enabled_agents() -> list[str]:
    """Return agents that have MCP tool capabilities."""
    return [name for name, meta in AGENT_REGISTRY.items() if meta.tools]


def get_memory_enabled_agents() -> list[str]:
    """Return agents that require memory injection."""
    return [name for name, meta in AGENT_REGISTRY.items() if meta.requires_memory]


def get_agents_by_tier(tier: AgentTier) -> list[str]:
    """Return agents for a specific tier only.

    Args:
        tier: The specific tier to filter by

    Returns:
        List of agent names in that tier

    """
    return [name for name, meta in AGENT_REGISTRY.items() if meta.tier == tier]
