"""Data sufficiency calculation for synthesis quality control.

This module analyzes agent findings to determine overall data coverage
and recommends synthesis modes based on available data.

Issue #487 - Prevents hallucinations by detecting low-coverage scenarios
and recommending appropriate fallback modes.
"""

from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


# Weight factors for data availability levels
DATA_AVAILABILITY_WEIGHTS: dict[str, float] = {
    "sufficient": 1.0,
    "limited": 0.5,
    "insufficient": 0.1,
    "unknown": 0.3,  # Conservative default for missing data
}

# Thresholds for synthesis mode recommendations
NORMAL_SYNTHESIS_THRESHOLD: float = 0.5  # >= 50% coverage for full synthesis
FALLBACK_THRESHOLD: float = 0.3  # < 30% triggers trend-summary fallback

# Expected agents (used for calculating total possible coverage)
EXPECTED_AGENTS: list[str] = [
    "tech_comparator",
    "security_auditor",
    "implementation_planner",
    "integration_feasibility",
    "performance_analyst",
    "code_quality_critic",
    "trend_validator",
    "dependency_mapper",
]


@dataclass
class CoverageGapInfo:
    """Information about a coverage gap for an agent."""

    agent_name: str
    data_availability: str
    note: str
    impact: str


@dataclass
class DataSufficiencyResult:
    """Result of data sufficiency analysis."""

    coverage_score: float  # 0.0-1.0, weighted score based on data availability
    agents_with_data: int  # Number of agents that contributed
    total_agents: int  # Total number of expected agents
    coverage_gaps: list[CoverageGapInfo]  # Agents with insufficient/limited data
    recommended_mode: str  # "normal", "limited", or "fallback"
    recommendation_reason: str  # Why this mode was recommended


def calculate_data_sufficiency(
    findings: list[dict[str, object]],
) -> DataSufficiencyResult:
    """Calculate data sufficiency from agent findings.

    Analyzes each agent's data_availability field to compute:
    1. Weighted coverage score (sufficient=1.0, limited=0.5, insufficient=0.1)
    2. List of coverage gaps for agents with limited/insufficient data
    3. Recommended synthesis mode based on coverage thresholds

    Args:
        findings: List of agent finding dictionaries, each containing:
            - agent_name: str
            - data_availability: "sufficient" | "limited" | "insufficient"
            - data_availability_note: str (optional explanation)

    Returns:
        DataSufficiencyResult with coverage metrics and recommendations

    """
    if not findings:
        logger.warning("No agent findings provided for sufficiency calculation")
        return DataSufficiencyResult(
            coverage_score=0.0,
            agents_with_data=0,
            total_agents=len(EXPECTED_AGENTS),
            coverage_gaps=[],
            recommended_mode="fallback",
            recommendation_reason="No agent findings available",
        )

    # Track which agents contributed and their data availability
    agent_scores: dict[str, float] = {}
    coverage_gaps: list[CoverageGapInfo] = []

    for finding in findings:
        agent_name = str(finding.get("agent_name", "unknown"))
        data_availability = str(finding.get("data_availability", "unknown"))
        data_note = str(finding.get("data_availability_note", ""))

        # Get weight for this availability level
        weight = DATA_AVAILABILITY_WEIGHTS.get(data_availability, 0.3)
        agent_scores[agent_name] = weight

        # Track coverage gaps
        if data_availability in ("limited", "insufficient"):
            impact = _determine_impact(agent_name, data_availability)
            coverage_gaps.append(
                CoverageGapInfo(
                    agent_name=agent_name,
                    data_availability=data_availability,
                    note=data_note or f"Agent reported {data_availability} data",
                    impact=impact,
                )
            )

    # Calculate weighted coverage score
    if agent_scores:
        total_weight = sum(agent_scores.values())
        max_possible_weight = len(EXPECTED_AGENTS) * 1.0  # All agents with sufficient
        coverage_score = total_weight / max_possible_weight
    else:
        coverage_score = 0.0

    # Clamp to valid range
    coverage_score = max(0.0, min(1.0, coverage_score))

    # Determine recommended synthesis mode
    recommended_mode, recommendation_reason = _determine_synthesis_mode(
        coverage_score=coverage_score,
        agents_with_data=len(agent_scores),
        total_gaps=len(coverage_gaps),
    )

    logger.info(
        "data_sufficiency_calculated",
        coverage_score=f"{coverage_score:.2%}",
        agents_with_data=len(agent_scores),
        coverage_gaps=len(coverage_gaps),
        recommended_mode=recommended_mode,
    )

    return DataSufficiencyResult(
        coverage_score=coverage_score,
        agents_with_data=len(agent_scores),
        total_agents=len(EXPECTED_AGENTS),
        coverage_gaps=coverage_gaps,
        recommended_mode=recommended_mode,
        recommendation_reason=recommendation_reason,
    )


def _determine_impact(agent_name: str, data_availability: str) -> str:
    """Determine the impact of a coverage gap based on agent type.

    Args:
        agent_name: Name of the agent with limited/insufficient data
        data_availability: The availability level ("limited" or "insufficient")

    Returns:
        Human-readable impact description

    """
    impact_map = {
        "tech_comparator": "Technology comparison may be incomplete",
        "security_auditor": "Security analysis may miss important risks",
        "implementation_planner": "Implementation steps may be generic",
        "integration_feasibility": "Integration guidance may be limited",
        "performance_analyst": "Performance recommendations may be vague",
        "code_quality_critic": "Best practices guidance may be incomplete",
        "trend_validator": "Trend alignment analysis may be limited",
        "dependency_mapper": "Dependency analysis may miss requirements",
    }

    base_impact = impact_map.get(agent_name, f"Analysis from {agent_name} is limited")

    if data_availability == "insufficient":
        return f"{base_impact} - minimal data found"
    return base_impact


def _determine_synthesis_mode(
    coverage_score: float,
    agents_with_data: int,
    total_gaps: int,
) -> tuple[str, str]:
    """Determine recommended synthesis mode based on coverage metrics.

    Args:
        coverage_score: Weighted coverage score (0.0-1.0)
        agents_with_data: Number of agents that contributed findings
        total_gaps: Number of agents with limited/insufficient data

    Returns:
        Tuple of (mode, reason) where mode is "normal", "limited", or "fallback"

    """
    # Fallback mode: Very low coverage
    if coverage_score < FALLBACK_THRESHOLD:
        return (
            "fallback",
            f"Coverage score ({coverage_score:.0%}) below threshold "
            f"({FALLBACK_THRESHOLD:.0%}). Recommend trend-summary fallback mode.",
        )

    # Limited mode: Moderate coverage with gaps
    if coverage_score < NORMAL_SYNTHESIS_THRESHOLD:
        return (
            "limited",
            f"Coverage score ({coverage_score:.0%}) is moderate. "
            f"{total_gaps} agents have limited data. "
            f"Synthesis will acknowledge coverage gaps.",
        )

    # Normal mode: Good coverage
    if total_gaps > 0:
        return (
            "normal",
            f"Coverage score ({coverage_score:.0%}) is good. "
            f"{agents_with_data} agents contributed, {total_gaps} with partial data.",
        )

    return (
        "normal",
        f"Coverage score ({coverage_score:.0%}) is excellent. "
        f"All {agents_with_data} contributing agents have sufficient data.",
    )


def format_coverage_gaps_for_synthesis(
    gaps: list[CoverageGapInfo],
) -> list[dict[str, str]]:
    """Format coverage gaps for inclusion in synthesis output.

    Converts internal CoverageGapInfo objects to dictionary format
    matching the CoverageGap schema in aggregated_insights.py.

    Args:
        gaps: List of CoverageGapInfo objects from sufficiency calculation

    Returns:
        List of dicts with missing_agent, missing_perspective, impact keys

    """
    return [
        {
            "missing_agent": gap.agent_name,
            "missing_perspective": gap.note,
            "impact": gap.impact,
        }
        for gap in gaps
    ]
