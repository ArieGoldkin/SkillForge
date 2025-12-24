"""Agent registry and tier metadata.

Issue #498: Agent Registry with Tier Metadata
"""

from app.domains.analysis.agents.registry import (
    AGENT_REGISTRY,
    AgentMetadata,
    AgentTier,
    AnalysisMode,
    get_agent_metadata,
    get_agents_by_tier,
    get_agents_for_mode,
    get_memory_enabled_agents,
    get_tool_enabled_agents,
)

__all__ = [
    "AGENT_REGISTRY",
    "AgentMetadata",
    "AgentTier",
    "AnalysisMode",
    "get_agent_metadata",
    "get_agents_by_tier",
    "get_agents_for_mode",
    "get_memory_enabled_agents",
    "get_tool_enabled_agents",
]
