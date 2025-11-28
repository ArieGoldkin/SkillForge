"""Fallback logic for aggregation when LLM synthesis fails."""

import time
from typing import Any


def create_empty_aggregated_insights(start_time: float) -> dict[str, Any]:
    """Create empty aggregated insights when no findings are available.

    Args:
        start_time: Start time for processing time calculation

    Returns:
        Empty aggregated insights dictionary

    """
    return {
        "executive_summary": "No agent findings available for synthesis.",
        "key_findings": [],
        "synthesis": {
            "technical_analysis": "No analysis available.",
            "implementation_guidance": "No guidance available.",
            "risk_assessment": "No risk assessment available.",
            "recommendations": "No recommendations available.",
        },
        "conflicts_resolved": [],
        "metadata": {
            "total_agents": 0,
            "agents_executed": [],
            "confidence_avg": 0.0,
            "confidence_min": 0.0,
            "confidence_max": 0.0,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
        },
    }


def create_fallback_aggregated_insights(
    validated_findings: list[dict[str, Any]],
    agent_types: list[str],
    confidence_scores: dict[str, float],
    conflicts: list[dict[str, str]],
    start_time: float,
) -> dict[str, Any]:
    """Create fallback aggregated insights when LLM synthesis fails.

    Args:
        validated_findings: List of validated agent findings
        agent_types: List of agent type names
        confidence_scores: Dictionary of confidence scores
        conflicts: List of detected conflicts
        start_time: Start time for processing time calculation

    Returns:
        Fallback aggregated insights dictionary

    """
    confidence_values = list(confidence_scores.values())

    return {
        "executive_summary": (
            f"Synthesized findings from {len(validated_findings)} agents. "
            f"Analysis includes technical comparison, security assessment, "
            f"and implementation guidance."
        ),
        "key_findings": [
            f"Analysis completed by {len(validated_findings)} specialized agents",
            "Findings available in detailed agent outputs",
            "Review individual agent findings for specific insights",
        ],
        "synthesis": {
            "technical_analysis": "Technical analysis completed by multiple specialized agents.",
            "implementation_guidance": "See individual agent findings for implementation details.",
            "risk_assessment": "Security and risk assessment completed by security auditor agent.",
            "recommendations": "See individual agent recommendations for specific guidance.",
        },
        "conflicts_resolved": [],
        "metadata": {
            "total_agents": len(validated_findings),
            "agents_executed": agent_types,
            "confidence_avg": (
                sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
            ),
            "confidence_min": (min(confidence_values) if confidence_values else 0.0),
            "confidence_max": (max(confidence_values) if confidence_values else 0.0),
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": 0,
            "llm_synthesis_failed": True,
            "fallback_used": True,
        },
    }
