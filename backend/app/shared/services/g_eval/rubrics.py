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
                1: "Missing comparison dimensions entirely, technologies not identified",
                2: "Only compares 1-2 dimensions superficially, major gaps in analysis",
                3: "Compares 3-4 dimensions (performance/scalability/DX/use cases) with basic detail",
                4: "Covers most dimensions with evidence-based analysis and trade-offs",
                5: "Comprehensive comparison across all dimensions with migration considerations",
            },
            "accuracy": {
                1: "Major factual errors about technologies, incorrect benchmarks or claims",
                2: "Some inaccuracies or outdated information, unsupported performance claims",
                3: "Generally accurate but lacks evidence from content or specificity",
                4: "Accurate with concrete examples, benchmarks, and evidence from content",
                5: "Highly accurate with authoritative references, version-specific details",
            },
            "balance": {
                1: "Heavily biased toward one technology, ignores strengths of alternatives",
                2: "Noticeable bias with weak counter-arguments or cherry-picked examples",
                3: "Attempts balance but missing trade-offs in some dimensions",
                4: "Fair treatment with clear pros/cons for each technology",
                5: "Perfectly balanced with nuanced trade-offs and scenario-based analysis",
            },
            "recommendation": {
                1: "No recommendation or completely unjustified choice",
                2: "Vague recommendation without scenario context or decision criteria",
                3: "Basic recommendation with some reasoning about use case fit",
                4: "Clear scenario-based recommendation with decision criteria explained",
                5: "Context-aware recommendation with migration/adoption considerations included",
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
                1: "Missing major security considerations, no threat model identified",
                2: "Only identifies obvious vulnerabilities (1-2 OWASP categories)",
                3: "Covers common security concerns (auth, input validation, data exposure)",
                4: "Thorough coverage across OWASP Top 10 with attack surface analysis",
                5: "Comprehensive audit including edge cases, dependencies, and configurations",
            },
            "severity_assessment": {
                1: "No severity ratings or completely wrong risk assessment",
                2: "Inconsistent ratings, missing likelihood or impact analysis",
                3: "Basic severity (High/Medium/Low) with some risk reasoning",
                4: "Well-calibrated severity with CVSS-like reasoning (severity x likelihood)",
                5: "Expert-level severity with impact analysis and exploitation probability",
            },
            "actionability": {
                1: "No remediation guidance or mitigation suggestions",
                2: "Vague or impractical recommendations without implementation details",
                3: "Basic fix suggestions with effort estimates",
                4: "Clear, specific remediation steps prioritized by risk",
                5: "Detailed fixes with code examples, compensating controls, and priorities",
            },
            "depth": {
                1: "Superficial checklist with no threat actor or entry point analysis",
                2: "Basic vulnerability listing without root cause understanding",
                3: "Moderate depth with some attack surface and risk analysis",
                4: "Good depth with threat modeling and exploitation scenarios",
                5: "Expert-level depth with systemic vulnerabilities and defense-in-depth",
            },
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
                1: "Plan is missing or severely incomplete, no scope defined",
                2: "Major gaps in implementation steps, missing key components or phases",
                3: "Covers main phases with architecture decisions and task breakdown",
                4: "Comprehensive plan with all phases, components, and milestones defined",
                5: "Exhaustive plan with dependencies, checkpoints, and decision points",
            },
            "feasibility": {
                1: "Unrealistic or technically impossible plan ignoring constraints",
                2: "Significant feasibility concerns unaddressed, missing prerequisites",
                3: "Generally feasible but assumptions or boundaries unclear",
                4: "Realistic plan with clear assumptions and complexity estimates",
                5: "Highly feasible with risk-adjusted estimates and prototyping needs",
            },
            "sequencing": {
                1: "No logical order, dependencies ignored, random task listing",
                2: "Poor sequencing with obvious circular dependencies or conflicts",
                3: "Basic dependency-based ordering with some parallelization missed",
                4: "Good sequencing with clear dependencies and milestone checkpoints",
                5: "Optimal sequencing with parallelization opportunities and critical path",
            },
            "risk_awareness": {
                1: "No risk consideration or challenge identification",
                2: "Only obvious risks mentioned without mitigation strategies",
                3: "Basic risk awareness with some unknowns identified",
                4: "Good risk identification with mitigation strategies and unknowns",
                5: "Comprehensive risk matrix with contingencies and investigation needs",
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
                1: "Research is missing or off-topic, no problem/question identified",
                2: "Only scratches surface, missing methodology or key findings",
                3: "Covers main concepts (problem, methodology, findings) but gaps exist",
                4: "Thorough coverage with limitations and practical applications discussed",
                5: "Comprehensive research with related work and future research directions",
            },
            "accuracy": {
                1: "Major factual errors, misrepresents findings or methodology",
                2: "Some inaccuracies or unsupported interpretations of results",
                3: "Generally accurate but conflates findings with interpretations",
                4: "Accurate with clear distinction between findings and interpretations",
                5: "Highly accurate with evidence strength noted and source verification",
            },
            "synthesis": {
                1: "No synthesis, just disconnected facts or data dump",
                2: "Minimal synthesis with weak connections between findings",
                3: "Basic synthesis of main themes and patterns identified",
                4: "Good synthesis with clear insights and practical implications",
                5: "Excellent synthesis revealing novel connections and actionable insights",
            },
            "depth": {
                1: "Superficial summary with no critical evaluation or limitations",
                2: "Basic coverage without assessing biases or generalizability",
                3: "Moderate depth with some critical evaluation of methodology",
                4: "Good depth with limitations, biases, and generalizability assessed",
                5: "Expert-level critical evaluation with field implications and future work",
            },
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
                1: "Analysis is missing or irrelevant, no baseline or targets identified",
                2: "Only surface-level metrics (1-2 dimensions), missing bottleneck analysis",
                3: "Basic coverage (latency, throughput, resources) with gap identification",
                4: "Thorough analysis across dimensions with profiling perspective",
                5: "Comprehensive multi-dimensional analysis with saturation and constraints",
            },
            "metrics_quality": {
                1: "No metrics or completely wrong metrics for the domain",
                2: "Metrics present but poorly chosen or lacking interpretation",
                3: "Standard metrics (p50/p95/p99, RPS) with basic interpretation",
                4: "Well-chosen metrics with good statistical analysis and baselines",
                5: "Expert metric selection with statistical rigor and SLA alignment",
            },
            "root_cause": {
                1: "No root cause analysis, symptoms only without investigation",
                2: "Superficial cause identification without evidence or profiling",
                3: "Basic cause analysis with some bottleneck identification",
                4: "Good root cause with profiling evidence and constraint analysis",
                5: "Deep root cause with systemic understanding and algorithmic insights",
            },
            "recommendations": {
                1: "No optimization recommendations or completely impractical",
                2: "Vague suggestions without ROI, effort, or trade-off analysis",
                3: "Basic optimization ideas with some priority indication",
                4: "Specific, actionable optimizations with effort and impact estimates",
                5: "Prioritized optimizations with expected impact and trade-off analysis",
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
                1: "Learning path is missing or empty, no clear topic defined",
                2: "Major topic gaps, missing 2+ core modules or prerequisites",
                3: "Covers core concepts with basic module structure",
                4: "Thorough coverage with all modules, resources, and time estimates",
                5: "Comprehensive curriculum with resources, milestones, and assessment",
            },
            "pedagogical_quality": {
                1: "No teaching structure, dump of topics with no learning objectives",
                2: "Poor learning flow, modules lack clear objectives or outcomes",
                3: "Basic educational structure with some learning objectives defined",
                4: "Good pedagogical approach with clear objectives and skill verification",
                5: "Expert instructional design with mastery indicators and checkpoints",
            },
            "progression": {
                1: "No skill progression, random topic ordering ignoring prerequisites",
                2: "Illogical skill ordering, advanced topics before fundamentals",
                3: "Basic beginner-to-advanced flow respecting major dependencies",
                4: "Clear skill tree with learning dependencies and logical sequencing",
                5: "Optimal learning progression with checkpoints and module build-up",
            },
            "practicality": {
                1: "No practical elements, purely theoretical content",
                2: "Minimal hands-on content, no projects or exercises",
                3: "Some practical exercises or examples included",
                4: "Good project-based learning with realistic time estimates",
                5: "Rich practical curriculum with real-world projects and skill assessment",
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
                1: "Review is empty or off-topic, no architecture or structure analysis",
                2: "Only catches obvious surface issues, misses structural problems",
                3: "Reviews main code paths, covers bugs/performance/security/style",
                4: "Thorough review across all categories with pattern evaluation",
                5: "Comprehensive review including edge cases and design simplification",
            },
            "issue_quality": {
                1: "No issues identified or all false positives, no categorization",
                2: "Issues poorly described without severity or specific code locations",
                3: "Basic issue descriptions with categories (bugs/style/performance)",
                4: "Clear, well-categorized issues with severity and code references",
                5: "Expert issue analysis with WHY explanation, impact, and priority",
            },
            "constructiveness": {
                1: "Unconstructive or hostile feedback without explanation",
                2: "Criticism without solutions or improvement suggestions",
                3: "Basic fix suggestions with some code examples",
                4: "Helpful feedback with alternatives and clear explanations of WHY",
                5: "Constructive mentorship with learning opportunities and concrete examples",
            },
            "accuracy": {
                1: "Major errors in review, misunderstands code behavior or intent",
                2: "Some inaccuracies or recommendations that would introduce bugs",
                3: "Generally accurate but missing context or edge case considerations",
                4: "Accurate analysis with good understanding of patterns and intent",
                5: "Highly accurate with deep understanding of architecture and trade-offs",
            },
        },
    },
    "artifact_generator": {
        "criteria": ["completeness", "coherence", "depth", "actionability"],
        "weights": {
            "completeness": 0.30,
            "coherence": 0.25,
            "depth": 0.25,
            "actionability": 0.20,
        },
        "rubrics": {
            "completeness": {
                1: "Artifact is empty or missing major sections, no structure or overview",
                2: "Major sections missing (>50% of expected content), thin or placeholder content",
                3: "Has core sections (overview, implementation steps, examples) but lacks depth",
                4: "All major sections present with detailed content and examples",
                5: "Comprehensive guide with all sections thoroughly developed, examples, and edge cases",
            },
            "coherence": {
                1: "Disorganized, contradictory sections, no logical flow between topics",
                2: "Poor organization with disconnected sections and confusing navigation",
                3: "Adequate structure with table of contents and section flow",
                4: "Well-organized with clear progression and cross-references between sections",
                5: "Excellent structure with seamless flow, clear navigation, and professional formatting",
            },
            "depth": {
                1: "Superficial treatment with no technical details or code examples",
                2: "Basic coverage without implementation details, architecture, or reasoning",
                3: "Moderate technical depth with some code examples and explanations",
                4: "Good technical depth with detailed implementation guidance and architecture",
                5: "Expert-level depth with comprehensive examples, trade-offs, and advanced considerations",
            },
            "actionability": {
                1: "No practical guidance, purely theoretical without implementation steps",
                2: "Vague guidance without specific commands, code samples, or next steps",
                3: "Basic implementation steps with some code snippets and setup instructions",
                4: "Clear step-by-step guidance with runnable code examples and verification steps",
                5: "Highly actionable with copy-paste ready code, CLI commands, and validation checklists",
            },
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
    rubrics: dict[str, dict[int, str]] = config.get("rubrics", DEFAULT_RUBRICS)

    if criterion in rubrics:
        return rubrics[criterion]

    # Fallback to default rubric for criterion
    fallback: dict[int, str] = DEFAULT_RUBRICS.get(criterion, DEFAULT_RUBRICS["completeness"])
    return fallback


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


# ============================================================================
# Validation Functions
# ============================================================================

# Weight validation tolerance (weights should sum to ~1.0)
_WEIGHT_MIN: Final[float] = 0.99
_WEIGHT_MAX: Final[float] = 1.01


def validate_rubric(agent_type: str, rubric_config: dict) -> list[str]:
    """Validate rubric configuration for completeness and correctness.

    Args:
        agent_type: The agent type being validated
        rubric_config: The rubric configuration dict

    Returns:
        List of validation errors (empty if valid)

    """
    errors: list[str] = []

    # Check required keys
    required_keys = {"criteria", "weights", "rubrics"}
    missing_keys = required_keys - set(rubric_config.keys())
    if missing_keys:
        errors.append(f"{agent_type}: Missing required keys: {missing_keys}")
        return errors  # Can't continue validation

    criteria = rubric_config["criteria"]
    weights = rubric_config["weights"]
    rubrics = rubric_config["rubrics"]

    # Check criteria and weights alignment
    if set(criteria) != set(weights.keys()):
        errors.append(
            f"{agent_type}: Criteria {criteria} doesn't match weight keys {list(weights.keys())}"
        )

    # Check weight sum (should be close to 1.0)
    weight_sum = sum(weights.values())
    if not (_WEIGHT_MIN <= weight_sum <= _WEIGHT_MAX):
        errors.append(f"{agent_type}: Weights sum to {weight_sum:.3f}, expected 1.0")

    # Check each criterion has a rubric
    for criterion in criteria:
        if criterion not in rubrics:
            errors.append(f"{agent_type}: Missing rubric for criterion '{criterion}'")
            continue

        rubric = rubrics[criterion]

        # Check rubric has all scores 1-5
        expected_scores = {1, 2, 3, 4, 5}
        actual_scores = set(rubric.keys())
        if actual_scores != expected_scores:
            errors.append(
                f"{agent_type}.{criterion}: Missing scores {expected_scores - actual_scores}"
            )

        # Check each score has a non-empty description
        for score in expected_scores:
            if score not in rubric:
                continue
            description = rubric[score]
            if not isinstance(description, str) or not description.strip():
                errors.append(f"{agent_type}.{criterion}: Score {score} has empty description")

    return errors


def validate_all_rubrics() -> dict[str, list[str]]:
    """Validate all agent rubrics for completeness and correctness.

    Returns:
        Dict mapping agent_type to list of validation errors

    """
    all_errors: dict[str, list[str]] = {}

    for agent_type, rubric_config in AGENT_RUBRICS.items():
        errors = validate_rubric(agent_type, rubric_config)
        if errors:
            all_errors[agent_type] = errors

    return all_errors


def get_all_agent_types() -> list[str]:
    """Get list of all agent types with specialized rubrics.

    Returns:
        List of agent type names

    """
    return list(AGENT_RUBRICS.keys())


def get_rubric_coverage() -> dict:
    """Get coverage statistics for all rubrics.

    Returns:
        Dict with coverage stats including:
        - total_agents: Number of agents with specialized rubrics
        - agents: List of agent types
        - validation_errors: Dict of validation errors by agent
        - is_valid: Boolean indicating if all rubrics are valid

    """
    errors = validate_all_rubrics()
    coverage: dict = {
        "total_agents": len(AGENT_RUBRICS),
        "agents": get_all_agent_types(),
        "validation_errors": errors,
        "is_valid": len(errors) == 0,
    }
    return coverage
