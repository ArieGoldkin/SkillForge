"""Configuration constants for supervisor agent."""

from functools import lru_cache

from app.core.agent_config import AGENT_REGISTRY

# Workflow stage agent types (excluded from analysis agent list)
WORKFLOW_STAGES = {"supervisor", "extraction", "embedding", "aggregation", "artifact_generation"}


def build_supervisor_prompt() -> str:
    """Build supervisor prompt from agent registry (single source of truth).

    This function builds the supervisor prompt dynamically from AGENT_REGISTRY,
    ensuring the prompt always reflects the current agent configuration without
    manual updates.

    Returns:
        Supervisor system prompt string

    Note:
        This function is not cached to ensure tests can run in isolation.
        The prompt is built from a constant registry, so performance impact is minimal.

    """
    # Filter to analysis agents only (exclude workflow stages)
    analysis_agents = [
        config for config in AGENT_REGISTRY.values() if config.agent_type not in WORKFLOW_STAGES
    ]

    # Sort by agent_type for consistent ordering
    sorted_agents = sorted(analysis_agents, key=lambda x: x.agent_type)

    # Build agent list from registry
    agent_list = "\n".join(
        f"- {config.agent_type}: {config.description}" for config in sorted_agents
    )

    return f"""Analyze content and select relevant agents. Output JSON:
{{"agents": ["agent1", "agent2"], "reasoning": "brief", "confidence": 0.0-1.0}}

Agents:
{agent_list}

Select based on: content type, keywords, complexity, analysis needs.

Examples:
- React tutorial → {{"agents": ["implementation_planner", "code_quality_critic"],
  "reasoning": "Tutorial needs implementation guide and code review",
  "confidence": 0.9}}
- Security guide → {{"agents": ["security_auditor", "trend_validator"],
  "reasoning": "Security content needs audit and trend validation",
  "confidence": 0.95}}
- API comparison → {{"agents": ["tech_comparator", "performance_analyst"],
  "reasoning": "Comparison needs tech analysis and performance evaluation",
  "confidence": 0.85}}"""


# Supervisor prompt (built from registry at module load time)
# Not cached to ensure test isolation - registry is constant so performance is fine
SUPERVISOR_PROMPT = build_supervisor_prompt()
