"""Helper functions for aggregation processing."""

from typing import Any

from app.core.agent_config import AGENT_REGISTRY
from app.core.logging import get_logger
from app.core.template_utils import render_jinja_template
from app.domains.analysis.workflows.nodes.supervisor_config import WORKFLOW_STAGES

logger = get_logger(__name__)

# All analysis agents (exclude workflow stages)
ALL_ANALYSIS_AGENTS = {
    agent_type: config.description
    for agent_type, config in AGENT_REGISTRY.items()
    if config.agent_type not in WORKFLOW_STAGES
}


def detect_conflicts(
    agent_findings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Detect conflicts between agent recommendations.

    Basic conflict detection: looks for direct contradictions in recommendations.

    Args:
        agent_findings: List of validated agent findings

    Returns:
        List of conflict dictionaries

    """
    conflicts = []
    recommendations: dict[str, str] = {}

    # Extract recommendations from each agent
    for finding in agent_findings:
        agent_type = finding.get("agent_type", "")
        findings_data = finding.get("findings", {})
        if not findings_data:
            continue

        # Try to extract recommendation from various possible fields
        recommendation = findings_data.get("recommendation") or findings_data.get("summary")
        if recommendation and isinstance(recommendation, str):
            recommendations[agent_type] = recommendation

    # Simple conflict detection: look for contradictory keywords
    # This is basic - full implementation would use semantic similarity
    tech_agents = [
        "tech_comparator",
        "integration_feasibility",
        "trend_validator",
    ]
    security_agents = ["security_auditor"]

    # Check for tech vs security conflicts
    for tech_agent in tech_agents:
        if tech_agent not in recommendations:
            continue
        tech_rec = recommendations[tech_agent].lower()

        for sec_agent in security_agents:
            if sec_agent not in recommendations:
                continue
            sec_rec = recommendations[sec_agent].lower()

            # Basic contradiction detection
            if any(word in tech_rec for word in ["recommend", "use", "adopt", "implement"]) and any(
                word in sec_rec for word in ["avoid", "risk", "vulnerability", "warning", "danger"]
            ):
                conflicts.append(
                    {
                        "agent_1": tech_agent,
                        "agent_2": sec_agent,
                        "conflict": (
                            f"{tech_agent} recommends adoption, "
                            f"{sec_agent} raises security concerns"
                        ),
                    }
                )

    return conflicts


def format_findings_for_llm(
    agent_findings: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
) -> str:
    """Format agent findings for LLM synthesis prompt using Jinja2 template.

    Args:
        agent_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores

    Returns:
        Formatted string for LLM prompt

    """
    # Precompute all data for template
    context = {
        "agent_findings": agent_findings,
        "conflicts": conflicts,
        "confidence_scores": confidence_scores,
    }

    # Render using Jinja2 template
    return render_jinja_template("aggregation_findings.j2", context)


def detect_coverage_gaps(
    contributing_agents: list[str],
    agent_findings: list[dict[str, Any]] | None = None,
    selected_agents: list[str] | None = None,
) -> list[dict[str, str]]:
    """Identify missing analysis perspectives.

    Issue #299-304: Now also considers data_availability from agent findings.
    Agents that contributed but with "limited" or "insufficient" data are
    treated as partial coverage gaps.

    If selected_agents is provided, only compares against selected agents instead
    of all possible agents. This correctly identifies agents that were selected
    but failed to produce findings.

    Args:
        contributing_agents: List of agent types that contributed findings
        agent_findings: Optional list of agent findings with data_availability
        selected_agents: Optional list of agents selected by supervisor.
            If provided, only compares against these agents instead of ALL_ANALYSIS_AGENTS

    Returns:
        List of coverage gap dictionaries with missing_agent, missing_perspective, impact

    """
    gaps = []

    # Build a map of data availability from findings
    data_availability_map: dict[str, tuple[str, str]] = {}
    if agent_findings:
        for finding in agent_findings:
            agent_type = finding.get("agent_type", "")
            findings_data = finding.get("findings", {})
            if isinstance(findings_data, dict):
                da = findings_data.get("data_availability", "sufficient")
                da_note = findings_data.get("data_availability_note", "")
                data_availability_map[agent_type] = (da, da_note)

    # Determine which agents to check against
    if selected_agents:
        # Only check selected agents (fixes coverage gap calculation)
        agents_to_check = {agent: ALL_ANALYSIS_AGENTS.get(agent, "") for agent in selected_agents}
    else:
        # Fallback to checking all agents (backward compatibility)
        agents_to_check = ALL_ANALYSIS_AGENTS

    # Check for missing agents
    for agent_type, description in agents_to_check.items():
        if not description:
            # Skip if agent not in ALL_ANALYSIS_AGENTS (shouldn't happen, but safe)
            continue
        if agent_type not in contributing_agents:
            gaps.append(
                {
                    "missing_agent": agent_type,
                    "missing_perspective": description,
                    "impact": (
                        f"Analysis incomplete without {agent_type.replace('_', ' ')} perspective"
                    ),
                }
            )
        elif agent_type in data_availability_map:
            # Issue #299-304: Check if agent had limited/insufficient data
            da, da_note = data_availability_map[agent_type]
            if da in ("limited", "insufficient"):
                gaps.append(
                    {
                        "missing_agent": agent_type,
                        "missing_perspective": da_note or f"Limited data for {agent_type}",
                        "impact": (
                            f"Partial analysis from {agent_type.replace('_', ' ')} "
                            f"due to {da} data availability"
                        ),
                    }
                )

    return gaps


def calculate_coverage_score(contributing_agents: list[str]) -> float:
    """Calculate coverage as percentage of potential agents.

    Args:
        contributing_agents: List of agent types that contributed findings

    Returns:
        Coverage score between 0.0 and 1.0 (agents_used / total_agents)

    """
    total_agents = len(ALL_ANALYSIS_AGENTS)
    return len(contributing_agents) / total_agents if total_agents > 0 else 0.0
