"""Configuration constants for supervisor agent.

Issue #379: Migrated to Langfuse Prompt Management with hardcoded fallback.
"""

from app.core.agent_config import AGENT_REGISTRY

# Workflow stage agent types (excluded from analysis agent list)
WORKFLOW_STAGES = {"supervisor", "extraction", "embedding", "aggregation", "artifact_generation"}


def build_agent_list_variable() -> str:
    """Build agent list variable for supervisor prompt.

    Returns the agent list formatted as:
    - agent_type: description

    This is used as a variable in the Langfuse-managed prompt.

    Returns:
        Formatted agent list string

    """
    # Filter to analysis agents only (exclude workflow stages)
    analysis_agents = [
        config for config in AGENT_REGISTRY.values() if config.agent_type not in WORKFLOW_STAGES
    ]

    # Sort by agent_type for consistent ordering
    sorted_agents = sorted(analysis_agents, key=lambda x: x.agent_type)

    # Build agent list from registry
    return "\n".join(f"- {config.agent_type}: {config.description}" for config in sorted_agents)


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
1. MINIMUM 3 AGENTS REQUIRED for all content (ensures diverse perspectives)
2. SHORT content (<1000 words): 3-4 agents covering primary topics
3. MEDIUM content (1000-3000 words): 4-6 agents covering main themes
4. COMPREHENSIVE content (>3000 words): 6-8 agents for thorough analysis

═══════════════════════════════════════════════════════════════════════════════
MANDATORY TIER 1 AGENTS (ALWAYS INCLUDE - NON-NEGOTIABLE):
These 4 universal agents MUST be selected for EVERY analysis, regardless of content:
  - key_insights: Extract core takeaways and main points
  - pros_cons: Identify advantages and disadvantages
  - audience_fit: Determine target audience suitability
  - actionable: Generate concrete action items

CRITICAL: Every response MUST include all 4 Tier 1 agents. They provide foundational
value for ANY content type - news, tutorials, research, opinion, reference, etc.
═══════════════════════════════════════════════════════════════════════════════

IMPORTANT: Never select fewer than 3 agents. Even simple content benefits from:
- implementation_planner (how to use)
- At least one perspective agent (security_auditor, performance_analyst, or tech_comparator)
- At least one context agent (dependency_mapper, trend_validator, or integration_feasibility)

TUTORIAL ANALYSIS (important):
- Tutorials are COMPREHENSIVE by nature - analyze from multiple angles
- Always include: implementation_planner + at least 2 of: security_auditor,
  performance_analyst, dependency_mapper
- Framework tutorials: Add tech_comparator for ecosystem context
- Minimum 3-4 agents for medium/large tutorials to ensure thorough coverage

CONTENT TYPE TRIGGERS:
- "tutorial", "guide", "introduction" → Include implementation_planner, dependency_mapper
- "security", "auth", "vulnerability" → Include security_auditor
- "performance", "fast", "async", "benchmark" → Include performance_analyst
- "vs", "comparison", "alternative" → Include tech_comparator
- Framework names (FastAPI, React, Django) → Include tech_comparator, performance_analyst

CODE PATTERN TRIGGERS (REQUIRED):
- Import statements (import X, from X import Y) → dependency_mapper REQUIRED
- Package files (requirements.txt, pyproject.toml, package.json) → dependency_mapper REQUIRED
- Installation commands (pip install, npm install) → dependency_mapper REQUIRED
- Framework tutorials with code examples → dependency_mapper REQUIRED + ecosystem mapping

Select based on: content type, keywords, complexity, analysis needs.

Examples (note: ALL examples include the 4 Tier 1 agents):
- Quick tip/snippet → {{
    "agents": ["key_insights", "pros_cons", "audience_fit", "actionable",
               "implementation_planner", "dependency_mapper", "security_auditor"],
    "reasoning": "Tier 1 universals + implementation guidance, dependency context, security basics",
  "confidence": 0.85}}
- Framework tutorial → {{
    "agents": ["key_insights", "pros_cons", "audience_fit", "actionable",
               "implementation_planner", "security_auditor", "performance_analyst",
               "dependency_mapper"],
  "reasoning": "Tier 1 universals + comprehensive tutorial multi-perspective analysis",
  "confidence": 0.85}}
- Security deep-dive → {{
    "agents": ["key_insights", "pros_cons", "audience_fit", "actionable",
               "security_auditor", "trend_validator", "code_quality_critic"],
  "reasoning": "Tier 1 universals + security focus with code patterns and trend validation",
  "confidence": 0.95}}
- Architecture comparison → {{
    "agents": ["key_insights", "pros_cons", "audience_fit", "actionable",
               "tech_comparator", "performance_analyst", "integration_feasibility",
               "trend_validator", "dependency_mapper"],
  "reasoning": "Tier 1 universals + comprehensive technical architecture analysis",
  "confidence": 0.8}}
- API quickstart → {{
    "agents": ["key_insights", "pros_cons", "audience_fit", "actionable",
               "implementation_planner", "security_auditor"],
  "reasoning": "Tier 1 universals + API setup implementation and security basics",
  "confidence": 0.9}}"""


# Supervisor prompt (built from registry at module load time)
# Not cached to ensure test isolation - registry is constant so performance is fine
SUPERVISOR_PROMPT = build_supervisor_prompt()
