"""Validation functions for agent findings.

This module provides validation and parsing logic for agent findings
before aggregation processing.
"""

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
