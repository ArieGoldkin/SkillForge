"""Tier aggregate nodes for Sequential Tier Learning (Issue #588).

This module contains lightweight aggregation nodes that run after each tier
of agents completes. These nodes compress agent findings into tier summaries
that are passed as context to later-tier agents.

The aggregation nodes use pure Python extraction (no LLM calls) to:
1. Filter agent_findings for the current tier
2. Extract key insights, risks, and recommendations
3. Build a TierSummary (500-800 tokens) for the next tier

This enables later-tier agents to build on earlier insights without
overwhelming context windows with redundant information.
"""

from app.core.logging import get_logger
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.aggregation.tier_summary_builder import (
    build_tier_summary,
)
from app.domains.analysis.workflows.tier_types import (
    TIER_1_AGENTS,
    TIER_2_AGENTS,
    TierSummary,
)
from app.shared.types.workflow_types import AgentFinding

logger = get_logger(__name__)


def _filter_findings_by_tier(
    agent_findings: list[AgentFinding],
    tier_agents: list[str],
) -> list[AgentFinding]:
    """Filter agent findings to only those from a specific tier.

    Args:
        agent_findings: All agent findings from the workflow
        tier_agents: List of agent names in this tier

    Returns:
        Filtered list of findings from tier agents only

    Example:
        >>> findings = [
        ...     {"agent_type": "key_insights", "findings": {}},
        ...     {"agent_type": "security_auditor", "findings": {}},
        ... ]
        >>> tier1_findings = _filter_findings_by_tier(findings, TIER_1_AGENTS)
        >>> len(tier1_findings)
        1
        >>> tier1_findings[0]["agent_type"]
        'key_insights'

    """
    return [finding for finding in agent_findings if finding.get("agent_type") in tier_agents]


async def tier1_aggregate(state: AnalysisState) -> dict:
    """Aggregate findings from Tier 1 agents (foundational analysis).

    This node runs after all Tier 1 agents complete. It extracts key insights,
    risks, and recommendations from Tier 1 findings and compresses them into
    a ~500 token summary for Tier 2 agents.

    Tier 1 agents (foundational analysis):
    - key_insights: Main themes and technical concepts
    - pros_cons: Strengths and weaknesses
    - audience_fit: Target audience and prerequisites
    - actionable: Practical applications

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Dictionary with tier1_summary field

    Example:
        >>> state = {
        ...     "analysis_id": "123",
        ...     "agent_findings": [
        ...         {
        ...             "agent_type": "key_insights",
        ...             "findings": {"key_points": ["RAG tutorial", "LangGraph patterns"]},
        ...         },
        ...     ],
        ... }
        >>> result = await tier1_aggregate(state)
        >>> "tier1_summary" in result
        True
        >>> result["tier1_summary"]["token_estimate"] <= 500
        True

    """
    analysis_id = state.get("analysis_id", "unknown")
    agent_findings = state.get("agent_findings", [])

    logger.info(
        "tier1_aggregate_started",
        analysis_id=analysis_id,
        total_findings=len(agent_findings),
    )

    # Filter for Tier 1 agents only
    tier1_findings = _filter_findings_by_tier(agent_findings, TIER_1_AGENTS)

    logger.debug(
        "tier1_findings_filtered",
        analysis_id=analysis_id,
        tier1_findings_count=len(tier1_findings),
        tier1_agents=TIER_1_AGENTS,
    )

    # Handle empty findings gracefully
    if not tier1_findings:
        logger.warning(
            "tier1_no_findings",
            analysis_id=analysis_id,
            expected_agents=TIER_1_AGENTS,
        )
        # Return empty TierSummary
        empty_summary: TierSummary = {
            "key_findings": [],
            "risks_identified": [],
            "recommendations": [],
            "agent_sources": [],
            "token_estimate": 0,
        }
        return {"tier1_summary": empty_summary}

    # Build tier summary using pure Python extraction
    summary = build_tier_summary(
        findings=tier1_findings,
        tier=1,
        max_tokens=500,  # Tier 1 budget: 500 tokens for foundational context
    )

    logger.info(
        "tier1_aggregate_complete",
        analysis_id=analysis_id,
        tier1_findings_count=len(tier1_findings),
        key_findings_count=len(summary["key_findings"]),
        risks_count=len(summary["risks_identified"]),
        recommendations_count=len(summary["recommendations"]),
        token_estimate=summary["token_estimate"],
    )

    return {"tier1_summary": summary}


async def tier2_aggregate(state: AnalysisState) -> dict:
    """Aggregate findings from Tier 2 agents (technical deep-dive).

    This node runs after all Tier 2 agents complete. It extracts technical
    insights, security risks, and implementation recommendations from Tier 2
    findings and compresses them into a ~800 token summary for Tier 3 agents.

    Tier 2 agents (technical deep-dive):
    - tech_comparator: Technology comparisons and alternatives
    - security_auditor: Security vulnerabilities and best practices
    - impl_planner: Implementation steps and architecture
    - performance_analyst: Performance bottlenecks and optimizations
    - code_quality_critic: Code quality patterns and anti-patterns
    - trend_validator: Technology trends and adoption signals
    - dependency_mapper: Dependencies and compatibility issues
    - integration_feasibility: Integration complexity and challenges

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Dictionary with tier2_summary field

    Example:
        >>> state = {
        ...     "analysis_id": "123",
        ...     "agent_findings": [
        ...         {
        ...             "agent_type": "security_auditor",
        ...             "findings": {"risks": ["SQL injection vulnerability"]},
        ...         },
        ...     ],
        ... }
        >>> result = await tier2_aggregate(state)
        >>> "tier2_summary" in result
        True
        >>> result["tier2_summary"]["token_estimate"] <= 800
        True

    """
    analysis_id = state.get("analysis_id", "unknown")
    agent_findings = state.get("agent_findings", [])

    logger.info(
        "tier2_aggregate_started",
        analysis_id=analysis_id,
        total_findings=len(agent_findings),
    )

    # Filter for Tier 2 agents only
    tier2_findings = _filter_findings_by_tier(agent_findings, TIER_2_AGENTS)

    logger.debug(
        "tier2_findings_filtered",
        analysis_id=analysis_id,
        tier2_findings_count=len(tier2_findings),
        tier2_agents=TIER_2_AGENTS,
    )

    # Handle empty findings gracefully
    if not tier2_findings:
        logger.warning(
            "tier2_no_findings",
            analysis_id=analysis_id,
            expected_agents=TIER_2_AGENTS,
        )
        # Return empty TierSummary
        empty_summary: TierSummary = {
            "key_findings": [],
            "risks_identified": [],
            "recommendations": [],
            "agent_sources": [],
            "token_estimate": 0,
        }
        return {"tier2_summary": empty_summary}

    # Build tier summary using pure Python extraction
    summary = build_tier_summary(
        findings=tier2_findings,
        tier=2,
        max_tokens=800,  # Tier 2 budget: 800 tokens for technical context
    )

    logger.info(
        "tier2_aggregate_complete",
        analysis_id=analysis_id,
        tier2_findings_count=len(tier2_findings),
        key_findings_count=len(summary["key_findings"]),
        risks_count=len(summary["risks_identified"]),
        recommendations_count=len(summary["recommendations"]),
        token_estimate=summary["token_estimate"],
    )

    return {"tier2_summary": summary}
