"""Helper functions for aggregation processing."""

import json
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_and_parse_findings(
    agent_findings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], dict[str, float]]:
    """Validate and parse agent findings.

    Args:
        agent_findings: List of agent finding dictionaries

    Returns:
        Tuple of (validated_findings, agent_types, confidence_scores)

    """
    validated_findings = []
    agent_types = []
    confidence_scores: dict[str, float] = {}

    for finding in agent_findings:
        if not isinstance(finding, dict):
            logger.warning(
                "aggregation_invalid_finding",
                finding_type=type(finding).__name__,
            )
            continue

        agent_type = finding.get("agent_type")
        if not agent_type:
            logger.warning("aggregation_missing_agent_type", finding=finding)
            continue

        findings_data = finding.get("findings", {})
        if not findings_data:
            logger.warning(
                "aggregation_empty_findings",
                agent_type=agent_type,
            )
            # Still include it, but mark as empty
            validated_findings.append(finding)
            agent_types.append(agent_type)
            confidence_scores[agent_type] = finding.get("confidence_score", 0.0) or 0.0
            continue

        validated_findings.append(finding)
        agent_types.append(agent_type)
        confidence_scores[agent_type] = finding.get("confidence_score", 0.0) or 0.0

    return validated_findings, agent_types, confidence_scores


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
                        "conflict": f"{tech_agent} recommends adoption, {sec_agent} raises security concerns",
                    }
                )

    return conflicts


def format_findings_for_llm(
    agent_findings: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
) -> str:
    """Format agent findings for LLM synthesis prompt.

    Args:
        agent_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores

    Returns:
        Formatted string for LLM prompt

    """
    formatted = "AGENT FINDINGS:\n\n"

    for finding in agent_findings:
        agent_type = finding.get("agent_type", "unknown")
        findings_data = finding.get("findings", {})
        confidence = confidence_scores.get(agent_type, 0.0)

        formatted += f"--- {agent_type.upper().replace('_', ' ')} ---\n"
        formatted += f"Confidence: {confidence:.2f}\n"
        formatted += f"Findings: {json.dumps(findings_data, indent=2)}\n\n"

    if conflicts:
        formatted += "\nCONFLICTS DETECTED:\n"
        for conflict in conflicts:
            formatted += f"- {conflict['conflict']}\n"
            formatted += f"  Agents: {conflict['agent_1']} vs {conflict['agent_2']}\n"

    formatted += "\nCONFIDENCE SCORES:\n"
    for agent_type, score in sorted(confidence_scores.items(), key=lambda x: x[1], reverse=True):
        formatted += f"- {agent_type}: {score:.2f}\n"

    return formatted
