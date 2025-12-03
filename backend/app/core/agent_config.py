"""Agent configuration registry.

This module provides a centralized registry of agent configurations, including
the mapping between agent types (internal identifiers) and stage names
(external API contract for SSE events).

This is the single source of truth for agent-to-stage mapping, ensuring
consistency between backend implementation and frontend expectations.

Architecture:
- Agent Type: Internal identifier used in code (e.g., "tech_comparator")
- Stage Name: External API contract for SSE events (e.g., "tech_comparison")
- Agent Config: Metadata including both, plus display information

This separation allows:
- Internal code to use agent_type (implementation detail)
- External API to use stage_name (contract)
- Clear mapping in one place
"""

from dataclasses import dataclass
from typing import Literal

# Frontend stage names as defined in SSE_SCHEMA.md
# Includes both agent-specific stages and workflow-level stages
StageName = Literal[
    # Agent stages
    "extraction",
    "supervisor_routing",
    "tech_comparison",
    "security_audit",
    "implementation_planning",
    "performance_audit",
    "code_quality_audit",
    "trends_analysis",
    "dependencies_analysis",
    "aggregation",
    "artifact_generation",
    # Workflow-level stages (for error handling and metrics)
    "workflow",
    "pattern_comparison",
    "metrics",
]


@dataclass(frozen=True)
class AgentConfig:
    """Configuration for an analysis agent.

    Attributes:
        agent_type: Internal agent identifier (e.g., "tech_comparator")
        stage_name: External stage name for SSE events (e.g., "tech_comparison")
        display_name: Human-readable name for UI (e.g., "Tech Comparison")
        description: Brief description of agent purpose

    """

    agent_type: str
    stage_name: StageName
    display_name: str
    description: str = ""


# Centralized agent registry - single source of truth
AGENT_REGISTRY: dict[str, AgentConfig] = {
    # Analysis agents
    "tech_comparator": AgentConfig(
        agent_type="tech_comparator",
        stage_name="tech_comparison",
        display_name="Tech Comparison",
        description="Compare technology with modern alternatives",
    ),
    "security_auditor": AgentConfig(
        agent_type="security_auditor",
        stage_name="security_audit",
        display_name="Security Audit",
        description="Security risks and vulnerabilities analysis",
    ),
    "implementation_planner": AgentConfig(
        agent_type="implementation_planner",
        stage_name="implementation_planning",
        display_name="Implementation Planning",
        description="Step-by-step implementation guides and roadmaps",
    ),
    "performance_analyst": AgentConfig(
        agent_type="performance_analyst",
        stage_name="performance_audit",
        display_name="Performance Audit",
        description="Performance trade-offs, latency, and scaling analysis",
    ),
    "code_quality_critic": AgentConfig(
        agent_type="code_quality_critic",
        stage_name="code_quality_audit",
        display_name="Code Quality Audit",
        description="Code patterns, best practices, and maintainability analysis",
    ),
    "trend_validator": AgentConfig(
        agent_type="trend_validator",
        stage_name="trends_analysis",
        display_name="Trends Analysis",
        description="2025 trends vs legacy/outdated technology validation",
    ),
    "dependency_mapper": AgentConfig(
        agent_type="dependency_mapper",
        stage_name="dependencies_analysis",
        display_name="Dependencies Analysis",
        description="Dependencies, versions, and conflicts analysis",
    ),
    "integration_feasibility": AgentConfig(
        agent_type="integration_feasibility",
        stage_name="implementation_planning",  # Part of implementation planning
        display_name="Integration Feasibility",
        description="Modern stack integration assessment (Next.js, FastAPI)",
    ),
    # Workflow stages (not agents, but need stage names)
    "supervisor": AgentConfig(
        agent_type="supervisor",
        stage_name="supervisor_routing",
        display_name="Supervisor Routing",
        description="Agent selection and routing decision",
    ),
    "extraction": AgentConfig(
        agent_type="extraction",
        stage_name="extraction",
        display_name="Content Extraction",
        description="Extract content from URL",
    ),
    "embedding": AgentConfig(
        agent_type="embedding",
        stage_name="extraction",  # Part of extraction phase
        display_name="Embedding Generation",
        description="Generate semantic embeddings for content",
    ),
    "aggregation": AgentConfig(
        agent_type="aggregation",
        stage_name="aggregation",
        display_name="Aggregating Results",
        description="Aggregate findings from all agents",
    ),
    "artifact_generation": AgentConfig(
        agent_type="artifact_generation",
        stage_name="artifact_generation",
        display_name="Generating Report",
        description="Generate final analysis artifact",
    ),
}


def get_agent_config(agent_type: str) -> AgentConfig:
    """Get agent configuration by agent type.

    Args:
        agent_type: Internal agent identifier

    Returns:
        AgentConfig with agent_type, stage_name, display_name, description

    Raises:
        KeyError: If agent_type is not in registry

    Example:
        >>> config = get_agent_config("tech_comparator")
        >>> config.stage_name
        'tech_comparison'
        >>> config.display_name
        'Tech Comparison'

    """
    if agent_type not in AGENT_REGISTRY:
        from app.core.logging import get_logger

        logger = get_logger(__name__)
        available_agents_list = list(AGENT_REGISTRY.keys())
        logger.error(
            "unknown_agent_type",
            agent_type=agent_type,
            available_agents=available_agents_list,
        )
        error_msg = f"Unknown agent_type: {agent_type}. Available: {available_agents_list}"
        raise KeyError(error_msg)
    return AGENT_REGISTRY[agent_type]


def get_stage_name(agent_type: str) -> StageName:
    """Get stage name for agent type.

    Convenience function that returns just the stage_name.

    Args:
        agent_type: Internal agent identifier

    Returns:
        Stage name for SSE events

    Example:
        >>> get_stage_name("tech_comparator")
        'tech_comparison'

    """
    return get_agent_config(agent_type).stage_name
