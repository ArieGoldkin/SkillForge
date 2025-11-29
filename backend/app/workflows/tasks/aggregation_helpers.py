"""Helper functions for aggregation processing."""

from typing import Any

from app.core.logging import get_logger
from app.core.template_utils import render_jinja_template

logger = get_logger(__name__)


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
