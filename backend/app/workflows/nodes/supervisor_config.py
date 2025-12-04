"""Configuration constants for supervisor agent."""

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

AGENT SELECTION GUIDELINES:
1. SHORT content (<1000 words): 1-2 agents focused on primary topic
2. MEDIUM content (1000-3000 words): 2-4 agents covering main themes
3. COMPREHENSIVE content (>3000 words): 4-6 agents for thorough analysis

TUTORIAL ANALYSIS (important):
- Tutorials are COMPREHENSIVE by nature - analyze from multiple angles
- Always include: implementation_planner + at least 2 of: security_auditor, performance_analyst, dependency_mapper
- Framework tutorials: Add tech_comparator for ecosystem context
- Minimum 3-4 agents for medium/large tutorials to ensure thorough coverage

CONTENT TYPE TRIGGERS:
- "tutorial", "guide", "introduction" → Include implementation_planner, dependency_mapper
- "security", "auth", "vulnerability" → Include security_auditor
- "performance", "fast", "async", "benchmark" → Include performance_analyst
- "vs", "comparison", "alternative" → Include tech_comparator
- Framework names (FastAPI, React, Django) → Include tech_comparator, performance_analyst

Select based on: content type, keywords, complexity, analysis needs.

Examples:
- Quick tip/snippet → {{"agents": ["implementation_planner"],
  "reasoning": "Simple how-to needs only implementation guidance",
  "confidence": 0.9}}
- Framework tutorial → {{"agents": ["implementation_planner", "security_auditor", "performance_analyst", "dependency_mapper"],
  "reasoning": "Comprehensive tutorial needs multi-perspective analysis",
  "confidence": 0.85}}
- Security deep-dive → {{"agents": ["security_auditor", "trend_validator", "code_quality_critic"],
  "reasoning": "Security focus with code patterns and trend validation",
  "confidence": 0.95}}
- Architecture comparison → {{"agents": ["tech_comparator", "performance_analyst", "integration_feasibility", "trend_validator", "dependency_mapper"],
  "reasoning": "Architecture decisions need comprehensive technical analysis",
  "confidence": 0.8}}
- API quickstart → {{"agents": ["implementation_planner", "security_auditor"],
  "reasoning": "API setup needs implementation and security basics",
  "confidence": 0.9}}"""


# Supervisor prompt (built from registry at module load time)
# Not cached to ensure test isolation - registry is constant so performance is fine
SUPERVISOR_PROMPT = build_supervisor_prompt()
