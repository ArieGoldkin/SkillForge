"""Agent tools for supervisor routing.

This module defines the 8 stub tools that represent agent selections.
Each tool corresponds to one of the specialized analysis agents.

Tools are placeholders - actual agents will be implemented in Issue #42.
"""

from langchain_core.tools import tool

# Map tool names to agent names
TOOL_TO_AGENT_MAP: dict[str, str] = {
    "tech_comparator_tool": "tech_comparator",
    "security_auditor_tool": "security_auditor",
    "integration_feasibility_tool": "integration_feasibility",
    "implementation_planner_tool": "implementation_planner",
    "performance_analyst_tool": "performance_analyst",
    "code_quality_critic_tool": "code_quality_critic",
    "trend_validator_tool": "trend_validator",
    "dependency_mapper_tool": "dependency_mapper",
}


@tool
def tech_comparator_tool(content: str) -> str:
    """Select tech_comparator agent to analyze and compare technologies in content."""
    return "tech_comparator selected"


@tool
def security_auditor_tool(content: str) -> str:
    """Select security_auditor agent to identify security implications and risks."""
    return "security_auditor selected"


@tool
def integration_feasibility_tool(content: str) -> str:
    """Select integration_feasibility agent to assess integration with modern stacks."""
    return "integration_feasibility selected"


@tool
def implementation_planner_tool(content: str) -> str:
    """Select implementation_planner agent to create step-by-step implementation guides."""
    return "implementation_planner selected"


@tool
def performance_analyst_tool(content: str) -> str:
    """Select performance_analyst agent to evaluate performance trade-offs and scaling."""
    return "performance_analyst selected"


@tool
def code_quality_critic_tool(content: str) -> str:
    """Select code_quality_critic agent to review code patterns and best practices."""
    return "code_quality_critic selected"


@tool
def trend_validator_tool(content: str) -> str:
    """Select trend_validator agent to assess if tech aligns with 2025 trends."""
    return "trend_validator selected"


@tool
def dependency_mapper_tool(content: str) -> str:
    """Select dependency_mapper agent to map dependencies and version requirements."""
    return "dependency_mapper selected"


# All agent tools in a list for supervisor agent configuration
AGENT_TOOLS = [
    tech_comparator_tool,
    security_auditor_tool,
    integration_feasibility_tool,
    implementation_planner_tool,
    performance_analyst_tool,
    code_quality_critic_tool,
    trend_validator_tool,
    dependency_mapper_tool,
]
