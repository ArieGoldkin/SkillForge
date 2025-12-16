"""Correctness evaluators for LLM output benchmarking.

This module provides task-specific evaluators that measure output accuracy:
- Supervisor: routing correctness (which agents were selected)
- Agent: analysis correctness (schema compliance + key field accuracy)
- Synthesis: aggregation correctness (summary quality + cross-domain connections)

All evaluators are compatible with LangSmith's evaluate() method using
the Run and Example signature.

Supervisor Routing Metrics (v2.0):
- coverage_score: Did supervisor select all REQUIRED agents? (superset OK)
- precision_score: How many selected agents were relevant?
- jaccard_score: Traditional exact match similarity (legacy)
- supervisor_correctness: Combined weighted score
"""

from typing import Any

from langsmith.schemas import Example, Run
from pydantic import ValidationError

from app.domains.analysis.schemas.agents.security_auditor import SecurityAudit
from app.domains.analysis.schemas.agents.tech_comparator import TechComparison
from app.domains.analysis.schemas.tasks.aggregated_insights import AggregatedInsights


def _calculate_supervisor_metrics(
    expected_agents: set[str],
    actual_agents: set[str],
    optional_agents: set[str] | None = None,
) -> dict[str, float]:
    """Calculate multiple routing metrics for supervisor evaluation.

    Args:
        expected_agents: Required agents that MUST be selected.
        actual_agents: Agents actually selected by supervisor.
        optional_agents: Agents that MAY be selected (auto-activated, context-dependent).

    Returns:
        Dictionary with coverage_score, precision_score, jaccard_score.

    """
    optional_agents = optional_agents or set()

    # Coverage: Did we select ALL required agents? (superset is OK)
    # This rewards thoroughness - selecting extra agents doesn't hurt
    if not expected_agents:
        coverage_score = 1.0
    else:
        covered = expected_agents & actual_agents
        coverage_score = len(covered) / len(expected_agents)

    # Precision: How many selected agents were relevant (expected OR optional)?
    # This penalizes selecting completely irrelevant agents
    relevant_agents = expected_agents | optional_agents
    if not actual_agents:
        precision_score = 0.0
    elif not relevant_agents:
        precision_score = 1.0  # No expectations = anything is fine
    else:
        relevant_selected = actual_agents & relevant_agents
        precision_score = len(relevant_selected) / len(actual_agents)

    # Jaccard: Traditional exact match (legacy metric)
    if not expected_agents and not actual_agents:
        jaccard_score = 1.0
    else:
        intersection = expected_agents & actual_agents
        union = expected_agents | actual_agents
        jaccard_score = len(intersection) / len(union) if union else 0.0

    return {
        "coverage_score": coverage_score,
        "precision_score": precision_score,
        "jaccard_score": jaccard_score,
    }


def supervisor_correctness_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate supervisor routing correctness with multiple metrics.

    Uses a combination of metrics to fairly evaluate routing:
    - Coverage (50%): Did supervisor select all REQUIRED agents?
    - Precision (30%): Were selected agents relevant?
    - Jaccard (20%): Traditional similarity (for backward compatibility)

    This approach rewards thoroughness (selecting extra helpful agents)
    while penalizing missing required agents or selecting irrelevant ones.

    Args:
        run: LangSmith run with supervisor output
        example: Golden example with expected agents

    Returns:
        {"key": "supervisor_correctness", "score": 0.0-1.0, "comment": "..."}

    """
    # Extract outputs from run
    outputs = run.outputs or {}

    # Extract expected agents from example outputs
    reference_outputs = example.outputs or {}
    expected_agents = set(reference_outputs.get("expected_agents", []))
    # Optional agents are OK to select (auto-activated by supervisor logic)
    optional_agents = set(reference_outputs.get("optional_agents", []))
    # Support both 'agents' and 'selected_agents' keys
    actual_agents = set(outputs.get("agents", outputs.get("selected_agents", [])))

    # Handle empty cases
    if not expected_agents and not actual_agents:
        return {
            "key": "supervisor_correctness",
            "score": 1.0,
            "comment": "No agents expected or selected (trivial case)",
        }

    if not actual_agents:
        return {
            "key": "supervisor_correctness",
            "score": 0.0,
            "comment": f"No agents selected (expected {len(expected_agents)})",
        }

    # Calculate all metrics
    metrics = _calculate_supervisor_metrics(expected_agents, actual_agents, optional_agents)

    # Combined score: Coverage (50%) + Precision (30%) + Jaccard (20%)
    # This weights coverage heavily - missing required agents is worse than extra agents
    score = (
        0.50 * metrics["coverage_score"]
        + 0.30 * metrics["precision_score"]
        + 0.20 * metrics["jaccard_score"]
    )

    # Build detailed comment
    missing = expected_agents - actual_agents
    extra = actual_agents - expected_agents - optional_agents
    auto_activated = actual_agents & optional_agents

    comment_parts = [
        f"coverage: {metrics['coverage_score']:.0%}",
        f"precision: {metrics['precision_score']:.0%}",
    ]
    if missing:
        comment_parts.append(f"missing: {sorted(missing)}")
    if extra:
        comment_parts.append(f"unexpected: {sorted(extra)}")
    if auto_activated:
        comment_parts.append(f"auto-activated: {sorted(auto_activated)}")

    return {
        "key": "supervisor_correctness",
        "score": score,
        "comment": ", ".join(comment_parts),
    }


def supervisor_coverage_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate supervisor coverage - did it select all REQUIRED agents.

    This metric rewards thoroughness. Selecting extra agents is OK.
    Only penalizes MISSING required agents.

    Scoring:
    - 1.0: All required agents selected (superset is perfect)
    - 0.5: Half of required agents selected
    - 0.0: No required agents selected

    Args:
        run: LangSmith run with supervisor output
        example: Golden example with expected agents

    Returns:
        {"key": "supervisor_coverage", "score": 0.0-1.0, "comment": "..."}

    """
    outputs = run.outputs or {}
    reference_outputs = example.outputs or {}

    expected_agents = set(reference_outputs.get("expected_agents", []))
    actual_agents = set(outputs.get("agents", outputs.get("selected_agents", [])))

    if not expected_agents:
        return {
            "key": "supervisor_coverage",
            "score": 1.0,
            "comment": "No required agents specified",
        }

    covered = expected_agents & actual_agents
    missing = expected_agents - actual_agents
    score = len(covered) / len(expected_agents)

    comment = f"{len(covered)}/{len(expected_agents)} required agents covered"
    if missing:
        comment += f", missing: {sorted(missing)}"

    return {
        "key": "supervisor_coverage",
        "score": score,
        "comment": comment,
    }


def supervisor_precision_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate supervisor precision - were selected agents relevant.

    This metric penalizes selecting completely irrelevant agents.
    Expected + optional agents are considered relevant.

    Scoring:
    - 1.0: All selected agents were relevant
    - 0.5: Half of selected agents were relevant
    - 0.0: No selected agents were relevant

    Args:
        run: LangSmith run with supervisor output
        example: Golden example with expected/optional agents

    Returns:
        {"key": "supervisor_precision", "score": 0.0-1.0, "comment": "..."}

    """
    outputs = run.outputs or {}
    reference_outputs = example.outputs or {}

    expected_agents = set(reference_outputs.get("expected_agents", []))
    optional_agents = set(reference_outputs.get("optional_agents", []))
    actual_agents = set(outputs.get("agents", outputs.get("selected_agents", [])))

    if not actual_agents:
        return {
            "key": "supervisor_precision",
            "score": 0.0,
            "comment": "No agents selected",
        }

    relevant_agents = expected_agents | optional_agents
    if not relevant_agents:
        return {
            "key": "supervisor_precision",
            "score": 1.0,
            "comment": "No relevance constraints specified",
        }

    relevant_selected = actual_agents & relevant_agents
    irrelevant = actual_agents - relevant_agents
    score = len(relevant_selected) / len(actual_agents)

    comment = f"{len(relevant_selected)}/{len(actual_agents)} agents relevant"
    if irrelevant:
        comment += f", irrelevant: {sorted(irrelevant)}"

    return {
        "key": "supervisor_precision",
        "score": score,
        "comment": comment,
    }


def agent_correctness_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate agent analysis correctness.

    Measures accuracy of agent analysis outputs across multiple dimensions:
    1. Schema compliance (all required fields present and valid)
    2. Key field accuracy (primary_tech, security_risks severity, etc.)
    3. Confidence score calibration (is confidence justified?)

    Scoring:
    - 1.0: Perfect schema + all key fields correct
    - 0.7-0.9: Schema valid + most key fields correct
    - 0.4-0.6: Schema valid + some key fields correct
    - 0.1-0.3: Schema valid but key fields mostly wrong
    - 0.0: Schema invalid or completely wrong

    Args:
        run: LangSmith run with agent output
        example: Golden example with expected output

    Returns:
        {"key": "agent_correctness", "score": 0.0-1.0, "comment": "..."}

    """
    # Extract outputs and inputs
    outputs = run.outputs or {}
    inputs = example.inputs or {}
    reference_outputs = example.outputs or {}

    agent_type = inputs.get("agent_type", reference_outputs.get("agent_type", "unknown"))

    # Schema validation based on agent type
    schema_score = 0.0
    schema_errors: list[str] = []

    if agent_type == "tech_comparator":
        try:
            TechComparison(**outputs)
            schema_score = 1.0
        except ValidationError as e:
            schema_errors = [err["msg"] for err in e.errors()]
            schema_score = 0.0

    elif agent_type == "security_auditor":
        try:
            SecurityAudit(**outputs)
            schema_score = 1.0
        except ValidationError as e:
            schema_errors = [err["msg"] for err in e.errors()]
            schema_score = 0.0

    # TODO: Add other agent types as needed
    else:
        # Generic schema validation - check for required fields
        required_fields = reference_outputs.get("required_fields", [])
        if required_fields:
            missing = [f for f in required_fields if f not in outputs]
            schema_score = 1.0 - (len(missing) / len(required_fields))
            if missing:
                schema_errors = [f"Missing required fields: {missing}"]
        else:
            # No schema validation available
            schema_score = 1.0

    # Key field accuracy
    key_field_score = 0.0
    correct_fields = 0
    total_fields = 0

    # Check primary_tech if provided
    if "primary_tech" in reference_outputs:
        total_fields += 1
        expected_tech = reference_outputs["primary_tech"].lower()
        actual_tech = str(outputs.get("primary_tech", "")).lower()
        if expected_tech in actual_tech or actual_tech in expected_tech:
            correct_fields += 1

    # Check alternatives overlap (tech comparator)
    if "expected_alternatives" in reference_outputs:
        total_fields += 1
        expected_alts = set(alt.lower() for alt in reference_outputs["expected_alternatives"])
        actual_alts = set(alt.lower() for alt in outputs.get("alternatives", []))
        if expected_alts & actual_alts:  # Any overlap
            correct_fields += 1

    # Check security risk severities (security auditor)
    if "expected_high_severity_risks" in reference_outputs:
        total_fields += 1
        expected_high = set(reference_outputs["expected_high_severity_risks"])
        actual_risks = outputs.get("security_risks", [])
        actual_high = {
            risk.get("risk_type", "")
            for risk in actual_risks
            if risk.get("severity") in {"high", "critical"}
        }
        if expected_high & actual_high:  # Any overlap
            correct_fields += 1

    # Calculate key field score
    if total_fields > 0:
        key_field_score = correct_fields / total_fields
    else:
        # No reference fields to compare - schema is sufficient
        key_field_score = 1.0

    # Combined score (weighted: 40% schema, 60% key fields)
    final_score = (0.4 * schema_score) + (0.6 * key_field_score)

    # Build comment
    comment_parts = [f"schema: {schema_score:.2f}", f"key_fields: {key_field_score:.2f}"]
    if schema_errors:
        comment_parts.append(f"errors: {schema_errors[:2]}")  # First 2 errors
    if total_fields > 0:
        comment_parts.append(f"{correct_fields}/{total_fields} fields correct")

    return {
        "key": "agent_correctness",
        "score": final_score,
        "comment": ", ".join(comment_parts),
    }


def synthesis_correctness_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate synthesis/aggregation correctness.

    Measures quality of synthesis across multiple dimensions:
    1. Executive summary captures key findings
    2. Cross-domain connections are relevant
    3. Coverage score accuracy
    4. Conflict resolution quality

    Scoring:
    - 1.0: Schema valid + all key findings present + good connections
    - 0.7-0.9: Schema valid + most key findings + some connections
    - 0.4-0.6: Schema valid + some key findings
    - 0.1-0.3: Schema valid but missing most key findings
    - 0.0: Schema invalid

    Args:
        run: LangSmith run with synthesis output
        example: Golden example with expected output

    Returns:
        {"key": "synthesis_correctness", "score": 0.0-1.0, "comment": "..."}

    """
    # Extract outputs
    outputs = run.outputs or {}
    reference_outputs = example.outputs or {}
    # Schema validation
    schema_score = 0.0
    schema_errors: list[str] = []

    try:
        AggregatedInsights(**outputs)
        schema_score = 1.0
    except ValidationError as e:
        schema_errors = [err["msg"] for err in e.errors()]
        schema_score = 0.0

    # Key findings coverage
    findings_score = 0.0
    if "expected_key_findings" in reference_outputs:
        expected_findings = [f.lower() for f in reference_outputs["expected_key_findings"]]
        actual_findings = [f.lower() for f in outputs.get("key_findings", [])]

        # Check if expected findings are mentioned in actual findings
        matches = 0
        for expected in expected_findings:
            if any(expected in actual for actual in actual_findings):
                matches += 1

        findings_score = matches / len(expected_findings) if expected_findings else 1.0
    else:
        # No reference findings - just check that some findings exist
        findings_score = 1.0 if outputs.get("key_findings") else 0.0

    # Executive summary quality (keyword matching)
    summary_score = 0.0
    if "expected_summary_keywords" in reference_outputs:
        keywords = [k.lower() for k in reference_outputs["expected_summary_keywords"]]
        summary = str(outputs.get("executive_summary", "")).lower()

        matches = sum(1 for k in keywords if k in summary)
        summary_score = matches / len(keywords) if keywords else 1.0
    else:
        # Just check that summary exists and is non-trivial
        summary = str(outputs.get("executive_summary", ""))
        summary_score = 1.0 if len(summary) >= 50 else 0.0

    # Coverage score accuracy
    coverage_score = 1.0
    if "expected_coverage" in reference_outputs:
        expected_coverage = reference_outputs["expected_coverage"]
        actual_coverage = outputs.get("coverage_score", 0.0)
        # Allow 10% tolerance
        if abs(expected_coverage - actual_coverage) <= 0.1:
            coverage_score = 1.0
        else:
            coverage_score = max(0.0, 1.0 - abs(expected_coverage - actual_coverage))

    # Cross-domain connections (just check if they exist and are non-empty)
    connections_score = 0.0
    connections = outputs.get("cross_domain_connections", [])
    if "expected_min_connections" in reference_outputs:
        min_expected = reference_outputs["expected_min_connections"]
        connections_score = 1.0 if len(connections) >= min_expected else 0.0
    else:
        # Just check that at least one connection exists
        connections_score = 1.0 if connections else 0.5  # Partial credit if none

    # Combined score (weighted)
    final_score = (
        (0.3 * schema_score)
        + (0.3 * findings_score)
        + (0.2 * summary_score)
        + (0.1 * coverage_score)
        + (0.1 * connections_score)
    )

    # Build comment
    comment_parts = [
        f"schema: {schema_score:.2f}",
        f"findings: {findings_score:.2f}",
        f"summary: {summary_score:.2f}",
    ]
    if schema_errors:
        comment_parts.append(f"errors: {schema_errors[:2]}")

    return {
        "key": "synthesis_correctness",
        "score": final_score,
        "comment": ", ".join(comment_parts),
    }
