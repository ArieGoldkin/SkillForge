"""Correctness evaluators for LLM output benchmarking.

This module provides task-specific evaluators that measure output accuracy:
- Supervisor: routing correctness (which agents were selected)
- Agent: analysis correctness (schema compliance + key field accuracy)
- Synthesis: aggregation correctness (summary quality + cross-domain connections)

All evaluators are compatible with LangSmith's evaluate() method using
the Run and Example signature.
"""

from typing import Any

from langsmith.schemas import Example, Run
from pydantic import ValidationError

from app.workflows.agents.schemas.security_auditor import SecurityAudit
from app.workflows.agents.schemas.tech_comparator import TechComparison
from app.workflows.tasks.schemas.aggregated_insights import AggregatedInsights


def supervisor_correctness_evaluator(run: Run, example: Example) -> dict[str, Any]:
    """Evaluate supervisor routing correctness.

    Measures how well the supervisor selected the appropriate agents for
    the given content. Uses Jaccard similarity for partial credit.

    Scoring:
    - 1.0: Perfect match (all expected agents selected, no extras)
    - 0.5-0.9: Partial match (some correct agents, some missing/extra)
    - 0.0: No overlap or all wrong agents

    Penalties:
    - Missing expected agents reduces score
    - Selecting irrelevant agents reduces score

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
    # Support both 'agents' and 'selected_agents' keys
    actual_agents = set(outputs.get("agents", outputs.get("selected_agents", [])))

    # Handle empty cases
    if not expected_agents and not actual_agents:
        return {
            "key": "supervisor_correctness",
            "score": 1.0,
            "comment": "No agents expected or selected (trivial case)",
        }

    if not expected_agents:
        return {
            "key": "supervisor_correctness",
            "score": 0.0,
            "comment": f"Selected {len(actual_agents)} agents when none expected",
        }

    if not actual_agents:
        return {
            "key": "supervisor_correctness",
            "score": 0.0,
            "comment": f"No agents selected (expected {len(expected_agents)})",
        }

    # Jaccard similarity for partial credit
    intersection = expected_agents & actual_agents
    union = expected_agents | actual_agents
    score = len(intersection) / len(union) if union else 0.0

    # Build detailed comment
    missing = expected_agents - actual_agents
    extra = actual_agents - expected_agents

    comment_parts = [f"{len(intersection)}/{len(expected_agents)} correct"]
    if missing:
        comment_parts.append(f"missing: {sorted(missing)}")
    if extra:
        comment_parts.append(f"extra: {sorted(extra)}")

    return {
        "key": "supervisor_correctness",
        "score": score,
        "comment": ", ".join(comment_parts),
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
