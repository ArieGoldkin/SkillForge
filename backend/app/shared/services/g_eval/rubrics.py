"""G-Eval Rubrics for Agent-Specific Quality Evaluation.

This module defines evaluation rubrics tailored to each agent type,
enabling domain-aware quality assessment using LLM-as-Judge.

Each rubric follows the 1-5 scale from G-Eval research:
- 1: Completely fails to meet criterion
- 2: Major deficiencies
- 3: Meets basic expectations
- 4: Good quality with minor gaps
- 5: Excellent, comprehensive quality
"""

from __future__ import annotations

from typing import Final

# ============================================================================
# Supported Criteria (Core G-Eval Dimensions)
# ============================================================================

SUPPORTED_CRITERIA: Final[list[str]] = [
    "completeness",
    "accuracy",
    "coherence",
    "depth",
]

# ============================================================================
# Default Rubrics (Used when agent-specific rubrics not defined)
# ============================================================================

DEFAULT_RUBRICS: Final[dict[str, dict[int, str]]] = {
    "completeness": {
        1: "Output is empty, placeholder, or completely off-topic",
        2: "Missing most required elements (>50% absent or superficial)",
        3: "Has basic structure but missing key details or sections",
        4: "All major elements present but some lack depth or specificity",
        5: "Comprehensive output with all elements thoroughly addressed",
    },
    "accuracy": {
        1: "Contains major factual errors or contradictions",
        2: "Some inaccuracies or unsupported claims present",
        3: "Generally accurate but lacks verification or specificity",
        4: "Accurate with good supporting evidence",
        5: "Highly accurate, well-sourced, factually rigorous",
    },
    "coherence": {
        1: "Disorganized, contradictory, or incomprehensible",
        2: "Poor organization with unclear logical flow",
        3: "Adequate structure but some disconnected elements",
        4: "Well-organized with clear logical progression",
        5: "Excellent structure, seamless flow, highly readable",
    },
    "depth": {
        1: "Superficial treatment with no meaningful analysis",
        2: "Basic coverage without insight or analysis",
        3: "Moderate depth with some analytical elements",
        4: "Good depth with meaningful insights and analysis",
        5: "Exceptional depth, nuanced analysis, expert-level insight",
    },
}

# ============================================================================
# Agent-Specific Rubrics
# ============================================================================

AGENT_RUBRICS: Final[dict[str, dict]] = {
    "tech_comparator": {
        "criteria": ["completeness", "accuracy", "balance", "recommendation"],
        "weights": {
            "completeness": 0.25,
            "accuracy": 0.30,
            "balance": 0.25,
            "recommendation": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Missing comparison dimensions entirely",
                2: "Only compares 1-2 dimensions superficially",
                3: "Compares 3-4 dimensions with basic detail",
                4: "Covers most dimensions (performance, ecosystem, learning curve)",
                5: "Comprehensive comparison across all relevant dimensions",
            },
            "accuracy": {
                1: "Major factual errors about technologies",
                2: "Some inaccuracies or outdated information",
                3: "Generally accurate but lacks specificity",
                4: "Accurate with concrete examples and evidence",
                5: "Highly accurate, current, with authoritative references",
            },
            "balance": {
                1: "Heavily biased toward one technology",
                2: "Noticeable bias with weak counter-arguments",
                3: "Attempts balance but some bias present",
                4: "Fair treatment with pros/cons for each",
                5: "Perfectly balanced with nuanced trade-offs",
            },
            "recommendation": {
                1: "No recommendation or completely unjustified",
                2: "Vague recommendation without context",
                3: "Basic recommendation with some reasoning",
                4: "Clear recommendation with good justification",
                5: "Context-aware recommendation with decision criteria",
            },
        },
    },
    "security_auditor": {
        "criteria": ["completeness", "severity_assessment", "actionability", "depth"],
        "weights": {
            "completeness": 0.25,
            "severity_assessment": 0.30,
            "actionability": 0.25,
            "depth": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Missing major security considerations",
                2: "Only identifies obvious vulnerabilities",
                3: "Covers common security concerns",
                4: "Thorough coverage of security landscape",
                5: "Comprehensive audit including edge cases",
            },
            "severity_assessment": {
                1: "No severity ratings or completely wrong",
                2: "Inconsistent or poorly justified ratings",
                3: "Basic severity assessment present",
                4: "Well-calibrated severity with CVSS-like reasoning",
                5: "Expert-level severity assessment with impact analysis",
            },
            "actionability": {
                1: "No remediation guidance",
                2: "Vague or impractical recommendations",
                3: "Basic fix suggestions",
                4: "Clear, specific remediation steps",
                5: "Detailed fixes with code examples and priorities",
            },
            "depth": DEFAULT_RUBRICS["depth"],
        },
    },
    "implementation_planner": {
        "criteria": ["completeness", "feasibility", "sequencing", "risk_awareness"],
        "weights": {
            "completeness": 0.30,
            "feasibility": 0.25,
            "sequencing": 0.25,
            "risk_awareness": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Plan is missing or severely incomplete",
                2: "Major gaps in implementation steps",
                3: "Covers main phases but lacks detail",
                4: "Comprehensive plan with most steps defined",
                5: "Exhaustive plan with all phases, dependencies, milestones",
            },
            "feasibility": {
                1: "Unrealistic or technically impossible plan",
                2: "Significant feasibility concerns unaddressed",
                3: "Generally feasible but assumptions unclear",
                4: "Realistic plan with clear assumptions",
                5: "Highly feasible with risk-adjusted estimates",
            },
            "sequencing": {
                1: "No logical order or dependencies",
                2: "Poor sequencing with obvious conflicts",
                3: "Basic ordering but some dependency issues",
                4: "Good sequencing with clear dependencies",
                5: "Optimal sequencing with parallelization opportunities",
            },
            "risk_awareness": {
                1: "No risk consideration",
                2: "Only obvious risks mentioned",
                3: "Basic risk awareness",
                4: "Good risk identification with mitigations",
                5: "Comprehensive risk matrix with contingencies",
            },
        },
    },
    "research_analyst": {
        "criteria": ["completeness", "accuracy", "synthesis", "depth"],
        "weights": {
            "completeness": 0.25,
            "accuracy": 0.30,
            "synthesis": 0.25,
            "depth": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Research is missing or off-topic",
                2: "Only scratches surface of the topic",
                3: "Covers main concepts but gaps exist",
                4: "Thorough coverage of research area",
                5: "Comprehensive research with related work",
            },
            "accuracy": DEFAULT_RUBRICS["accuracy"],
            "synthesis": {
                1: "No synthesis, just disconnected facts",
                2: "Minimal synthesis with weak connections",
                3: "Basic synthesis of main themes",
                4: "Good synthesis with clear insights",
                5: "Excellent synthesis revealing novel connections",
            },
            "depth": DEFAULT_RUBRICS["depth"],
        },
    },
    "performance_analyst": {
        "criteria": ["completeness", "metrics_quality", "root_cause", "recommendations"],
        "weights": {
            "completeness": 0.25,
            "metrics_quality": 0.25,
            "root_cause": 0.30,
            "recommendations": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Analysis is missing or irrelevant",
                2: "Only surface-level metrics",
                3: "Basic performance coverage",
                4: "Thorough performance analysis",
                5: "Comprehensive multi-dimensional analysis",
            },
            "metrics_quality": {
                1: "No metrics or wrong metrics",
                2: "Metrics present but poorly chosen",
                3: "Standard metrics with basic interpretation",
                4: "Well-chosen metrics with good analysis",
                5: "Expert metric selection with statistical rigor",
            },
            "root_cause": {
                1: "No root cause analysis",
                2: "Superficial cause identification",
                3: "Basic cause analysis",
                4: "Good root cause with evidence",
                5: "Deep root cause with systemic understanding",
            },
            "recommendations": {
                1: "No optimization recommendations",
                2: "Vague or impractical suggestions",
                3: "Basic optimization ideas",
                4: "Specific, actionable optimizations",
                5: "Prioritized optimizations with expected impact",
            },
        },
    },
    "learning_path": {
        "criteria": ["completeness", "pedagogical_quality", "progression", "practicality"],
        "weights": {
            "completeness": 0.25,
            "pedagogical_quality": 0.30,
            "progression": 0.25,
            "practicality": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Learning path is missing or empty",
                2: "Major topic gaps",
                3: "Covers core concepts",
                4: "Thorough coverage with context",
                5: "Comprehensive curriculum with resources",
            },
            "pedagogical_quality": {
                1: "No teaching structure",
                2: "Poor learning flow",
                3: "Basic educational structure",
                4: "Good pedagogical approach",
                5: "Expert-level instructional design",
            },
            "progression": {
                1: "No skill progression",
                2: "Illogical skill ordering",
                3: "Basic beginner-to-advanced flow",
                4: "Clear skill tree with dependencies",
                5: "Optimal learning progression with checkpoints",
            },
            "practicality": {
                1: "No practical elements",
                2: "Minimal hands-on content",
                3: "Some practical exercises",
                4: "Good project-based learning",
                5: "Rich practical curriculum with real-world projects",
            },
        },
    },
    "code_reviewer": {
        "criteria": ["completeness", "issue_quality", "constructiveness", "accuracy"],
        "weights": {
            "completeness": 0.25,
            "issue_quality": 0.30,
            "constructiveness": 0.25,
            "accuracy": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Review is empty or off-topic",
                2: "Only catches obvious issues",
                3: "Reviews main code paths",
                4: "Thorough code review",
                5: "Comprehensive review including edge cases",
            },
            "issue_quality": {
                1: "No issues identified or all false positives",
                2: "Issues poorly described",
                3: "Basic issue descriptions",
                4: "Clear, well-categorized issues",
                5: "Expert issue analysis with severity and impact",
            },
            "constructiveness": {
                1: "Unconstructive or hostile feedback",
                2: "Criticism without solutions",
                3: "Basic fix suggestions",
                4: "Helpful feedback with alternatives",
                5: "Constructive mentorship with learning opportunities",
            },
            "accuracy": DEFAULT_RUBRICS["accuracy"],
        },
    },
}

# ============================================================================
# API Functions
# ============================================================================


def get_agent_rubrics(agent_type: str) -> dict:
    """Get rubrics configuration for an agent type.

    Returns agent-specific rubrics if available, otherwise defaults.

    Args:
        agent_type: The agent type (e.g., 'tech_comparator')

    Returns:
        Dict with 'criteria', 'weights', and 'rubrics' keys

    """
    if agent_type in AGENT_RUBRICS:
        return AGENT_RUBRICS[agent_type]

    # Return default configuration
    return {
        "criteria": SUPPORTED_CRITERIA,
        "weights": {c: 1.0 / len(SUPPORTED_CRITERIA) for c in SUPPORTED_CRITERIA},
        "rubrics": DEFAULT_RUBRICS,
    }


def get_criterion_rubric(agent_type: str, criterion: str) -> dict[int, str]:
    """Get the rubric for a specific criterion.

    Args:
        agent_type: The agent type
        criterion: The criterion name (e.g., 'completeness')

    Returns:
        Dict mapping score (1-5) to description

    """
    config = get_agent_rubrics(agent_type)
    rubrics = config.get("rubrics", DEFAULT_RUBRICS)

    if criterion in rubrics:
        return rubrics[criterion]

    # Fallback to default rubric for criterion
    return DEFAULT_RUBRICS.get(criterion, DEFAULT_RUBRICS["completeness"])


def format_rubric_for_prompt(agent_type: str, criterion: str) -> str:
    """Format rubric as text for LLM prompt injection.

    Args:
        agent_type: The agent type
        criterion: The criterion name

    Returns:
        Formatted string with score descriptions

    """
    rubric = get_criterion_rubric(agent_type, criterion)
    lines = [f"Score {score}: {description}" for score, description in sorted(rubric.items())]
    return "\n".join(lines)
