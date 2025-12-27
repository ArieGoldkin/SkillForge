"""Result processing and persistence for agent execution.

This module handles saving agent results to the database and emitting
SSE events for completion, cancellation, and errors.
"""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.tracing import traced_tool, update_current_observation
from app.core.types import AnalysisID
from app.core.utils import normalize_analysis_id_to_uuid
from app.domains.analysis.workflows.agents.base import emit_agent_progress, save_agent_finding
from app.domains.analysis.workflows.agents.validation import score_agent_output
from app.domains.analysis.workflows.agents.validation.specificity_scorer import (
    LOW_SPECIFICITY_WARNING_THRESHOLD,
)

logger = get_logger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT_COUNTABLE_FIELDS: Single Source of Truth for Schema Field Names
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2025 Best Practice: Centralized mapping prevents key mismatch bugs (Issue #584)
# These field names MUST match the Pydantic v2 schema definitions exactly.
# Run `pytest tests/unit/workflows/agents/test_schema_alignment.py -v` to verify.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AGENT_COUNTABLE_FIELDS: dict[str, list[str]] = {
    # Content Analysis Agents (Tier 0)
    "tech_comparator": ["alternatives"],
    "security_auditor": ["security_risks", "best_practices", "compliance_notes"],
    "implementation_planner": ["steps"],
    "performance_analyst": ["bottlenecks", "optimization_opportunities"],
    "code_quality_critic": ["code_issues", "best_practices"],
    "trend_validator": ["trend_assessments"],
    "dependency_mapper": ["required_dependencies", "optional_dependencies", "core_dependencies"],
    "integration_feasibility": ["integration_steps", "breaking_changes"],
    # Tier 1: Universal Agents
    "actionable": ["immediate_actions", "follow_up_actions", "resources"],
    "key_insights": ["insights"],
    "pros_cons": ["pros", "cons"],
    "audience_fit": ["secondary_audiences", "prerequisites", "not_suitable_for"],
}

# Quality assessment thresholds
MIN_INSIGHTS_COMPREHENSIVE = 5
MIN_SPECIFICITY_COMPREHENSIVE = 0.7
MIN_INSIGHTS_PARTIAL = 2
MAX_KEY_INSIGHTS = 3


def _extract_findings_summary(findings: dict[str, object], agent_type: str) -> str:  # noqa: PLR0911, PLR0912, PLR0915 - Multiple returns/branches/statements needed for agent-specific extraction logic
    """Extract human-readable summary from findings.

    Args:
        findings: Agent findings dictionary
        agent_type: Type of agent

    Returns:
        Human-readable summary string

    """
    if agent_type == "tech_comparator":
        primary = findings.get("primary_tech", "Unknown")
        alternatives = findings.get("alternatives", [])
        if isinstance(alternatives, list) and alternatives:
            alt_str = ", ".join(str(alt) for alt in alternatives[:2])
            return f"Compared {primary} vs {alt_str}"
        return f"Identified {primary} as primary technology"

    if agent_type == "security_auditor":
        # Schema uses security_risks, best_practices, compliance_notes
        security_risks = findings.get("security_risks", [])
        best_practices = findings.get("best_practices", [])
        compliance_notes = findings.get("compliance_notes", [])
        risk_count = len(security_risks) if isinstance(security_risks, list) else 0
        bp_count = len(best_practices) if isinstance(best_practices, list) else 0
        cn_count = len(compliance_notes) if isinstance(compliance_notes, list) else 0
        return f"Found {risk_count} security risks, {bp_count + cn_count} recommendations"

    if agent_type == "implementation_planner":
        # Schema uses 'steps' field, not 'implementation_steps'
        steps = findings.get("steps", [])
        step_count = len(steps) if isinstance(steps, list) else 0
        return f"Planned {step_count} implementation steps"

    if agent_type == "performance_analyst":
        # Schema uses 'optimization_opportunities', not 'optimizations'
        bottlenecks = findings.get("bottlenecks", [])
        optimizations = findings.get("optimization_opportunities", [])
        bottleneck_count = len(bottlenecks) if isinstance(bottlenecks, list) else 0
        opt_count = len(optimizations) if isinstance(optimizations, list) else 0
        if bottleneck_count > 0 or opt_count > 0:
            return f"Identified {bottleneck_count} bottlenecks, {opt_count} optimizations"
        return "Performance analysis complete"

    if agent_type == "code_quality_critic":
        issues = findings.get("code_issues", [])
        best_practices = findings.get("best_practices", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        bp_count = len(best_practices) if isinstance(best_practices, list) else 0
        if issue_count > 0 or bp_count > 0:
            return f"Found {issue_count} issues, {bp_count} best practices"
        return "Code quality review complete"

    if agent_type == "trend_validator":
        # Schema uses 'trend_assessments', not 'trends'
        trends = findings.get("trend_assessments", [])
        trend_count = len(trends) if isinstance(trends, list) else 0
        if trend_count > 0:
            return f"Validated {trend_count} technology trends"
        return "Trends analysis complete"

    if agent_type == "dependency_mapper":
        # Schema uses required_dependencies, optional_dependencies, core_dependencies
        required = findings.get("required_dependencies", [])
        optional = findings.get("optional_dependencies", [])
        core = findings.get("core_dependencies", [])
        req_count = len(required) if isinstance(required, list) else 0
        opt_count = len(optional) if isinstance(optional, list) else 0
        core_count = len(core) if isinstance(core, list) else 0
        total = req_count + opt_count + core_count
        if total > 0:
            return f"Mapped {total} dependencies ({req_count} required, {opt_count} optional)"
        return "Dependencies analysis complete"

    if agent_type == "integration_feasibility":
        # Schema uses 'integration_steps', not 'integration_points'
        integration_steps = findings.get("integration_steps", [])
        breaking_changes = findings.get("breaking_changes", [])
        is_count = len(integration_steps) if isinstance(integration_steps, list) else 0
        bc_count = len(breaking_changes) if isinstance(breaking_changes, list) else 0
        if is_count > 0 or bc_count > 0:
            return f"Identified {is_count} integration steps, {bc_count} breaking changes"
        return "Integration feasibility analysis complete"

    # Tier 1: Universal Agents
    if agent_type == "actionable":
        immediate = findings.get("immediate_actions", [])
        follow_up = findings.get("follow_up_actions", [])
        resources = findings.get("resources", [])
        imm_count = len(immediate) if isinstance(immediate, list) else 0
        fu_count = len(follow_up) if isinstance(follow_up, list) else 0
        res_count = len(resources) if isinstance(resources, list) else 0
        return f"Extracted {imm_count} immediate actions, {fu_count} follow-ups, {res_count} resources"

    if agent_type == "key_insights":
        insights = findings.get("insights", [])
        insight_count = len(insights) if isinstance(insights, list) else 0
        return f"Identified {insight_count} key insights"

    if agent_type == "pros_cons":
        pros = findings.get("pros", [])
        cons = findings.get("cons", [])
        pro_count = len(pros) if isinstance(pros, list) else 0
        con_count = len(cons) if isinstance(cons, list) else 0
        return f"Found {pro_count} pros, {con_count} cons"

    if agent_type == "audience_fit":
        prereqs = findings.get("prerequisites", [])
        secondary = findings.get("secondary_audiences", [])
        prereq_count = len(prereqs) if isinstance(prereqs, list) else 0
        sec_count = len(secondary) if isinstance(secondary, list) else 0
        return f"Identified {sec_count + 1} audiences, {prereq_count} prerequisites"

    # Generic fallback
    return "Analysis complete"


def _count_insights(findings: dict[str, object], agent_type: str) -> int:  # noqa: PLR0911, PLR0912, PLR0915 - Multiple returns/branches/statements needed for agent-specific insight counting
    """Count number of insights in findings.

    Args:
        findings: Agent findings dictionary
        agent_type: Type of agent

    Returns:
        Number of insights found

    """
    if agent_type == "tech_comparator":
        alternatives = findings.get("alternatives", [])
        return len(alternatives) if isinstance(alternatives, list) else 0

    if agent_type == "security_auditor":
        # Schema uses security_risks, best_practices, compliance_notes
        security_risks = findings.get("security_risks", [])
        best_practices = findings.get("best_practices", [])
        compliance_notes = findings.get("compliance_notes", [])
        risk_count = len(security_risks) if isinstance(security_risks, list) else 0
        bp_count = len(best_practices) if isinstance(best_practices, list) else 0
        cn_count = len(compliance_notes) if isinstance(compliance_notes, list) else 0
        return risk_count + bp_count + cn_count

    if agent_type == "implementation_planner":
        # Schema uses 'steps' field, not 'implementation_steps'
        steps = findings.get("steps", [])
        return len(steps) if isinstance(steps, list) else 0

    if agent_type == "performance_analyst":
        # Schema uses 'optimization_opportunities', not 'optimizations'
        bottlenecks = findings.get("bottlenecks", [])
        optimizations = findings.get("optimization_opportunities", [])
        bottleneck_count = len(bottlenecks) if isinstance(bottlenecks, list) else 0
        opt_count = len(optimizations) if isinstance(optimizations, list) else 0
        return bottleneck_count + opt_count

    if agent_type == "code_quality_critic":
        issues = findings.get("code_issues", [])
        best_practices = findings.get("best_practices", [])
        issue_count = len(issues) if isinstance(issues, list) else 0
        bp_count = len(best_practices) if isinstance(best_practices, list) else 0
        return issue_count + bp_count

    if agent_type == "trend_validator":
        # Schema uses 'trend_assessments', not 'trends'
        trends = findings.get("trend_assessments", [])
        return len(trends) if isinstance(trends, list) else 0

    if agent_type == "dependency_mapper":
        # Schema uses required_dependencies, optional_dependencies, core_dependencies
        required = findings.get("required_dependencies", [])
        optional = findings.get("optional_dependencies", [])
        core = findings.get("core_dependencies", [])
        req_count = len(required) if isinstance(required, list) else 0
        opt_count = len(optional) if isinstance(optional, list) else 0
        core_count = len(core) if isinstance(core, list) else 0
        return req_count + opt_count + core_count

    if agent_type == "integration_feasibility":
        # Schema uses 'integration_steps' and 'breaking_changes'
        integration_steps = findings.get("integration_steps", [])
        breaking_changes = findings.get("breaking_changes", [])
        is_count = len(integration_steps) if isinstance(integration_steps, list) else 0
        bc_count = len(breaking_changes) if isinstance(breaking_changes, list) else 0
        return is_count + bc_count

    # Tier 1: Universal Agents
    if agent_type == "actionable":
        immediate = findings.get("immediate_actions", [])
        follow_up = findings.get("follow_up_actions", [])
        resources = findings.get("resources", [])
        imm_count = len(immediate) if isinstance(immediate, list) else 0
        fu_count = len(follow_up) if isinstance(follow_up, list) else 0
        res_count = len(resources) if isinstance(resources, list) else 0
        return imm_count + fu_count + res_count

    if agent_type == "key_insights":
        insights = findings.get("insights", [])
        return len(insights) if isinstance(insights, list) else 0

    if agent_type == "pros_cons":
        pros = findings.get("pros", [])
        cons = findings.get("cons", [])
        pro_count = len(pros) if isinstance(pros, list) else 0
        con_count = len(cons) if isinstance(cons, list) else 0
        return pro_count + con_count

    if agent_type == "audience_fit":
        prereqs = findings.get("prerequisites", [])
        secondary = findings.get("secondary_audiences", [])
        not_suitable = findings.get("not_suitable_for", [])
        prereq_count = len(prereqs) if isinstance(prereqs, list) else 0
        sec_count = len(secondary) if isinstance(secondary, list) else 0
        not_count = len(not_suitable) if isinstance(not_suitable, list) else 0
        return prereq_count + sec_count + not_count

    # Generic fallback: count top-level list/dict items
    count = 0
    for value in findings.values():
        if isinstance(value, (list, dict)):
            count += len(value)
    return count if count > 0 else 1  # At least 1 if findings exist


@traced_tool("process_agent_result", tags=["result_processing"])
async def process_agent_result(  # noqa: PLR0912 - Multiple branches needed for comprehensive result processing
    findings: dict[str, object],
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    start_time: float,
) -> dict[str, object]:
    """Process and persist successful agent result.

    Args:
        findings: Extracted findings from structured response
        analysis_id: UUID of the analysis
        agent_type: Type of agent
        session: Database session
        start_time: Start time for processing time calculation

    Returns:
        Result dictionary with agent_type, findings, processing_time_ms

    """
    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Extract confidence_score from findings if present
    # This allows agents to include confidence in their response without breaking existing code
    confidence_score: float | None = None
    findings_clean: dict[str, object] = findings
    if isinstance(findings, dict):
        confidence_value = findings.get("confidence_score")
        if isinstance(confidence_value, (int, float)):
            confidence_score = float(confidence_value)
        # Remove confidence_score from findings to avoid duplication in database
        findings_clean = {k: v for k, v in findings.items() if k != "confidence_score"}

    # Validate specificity of output (post-agent, pre-persistence)
    # This runs AFTER agent execution but BEFORE database save
    specificity_score = score_agent_output(findings, agent_type=agent_type)

    # Log specificity metrics for monitoring
    logger.info(
        "agent_specificity_score",
        agent_type=agent_type,
        analysis_id=analysis_id,
        specificity_score=specificity_score.overall_score,
        quality_level=specificity_score.quality_level,
        numeric_count=specificity_score.numeric_value_count,
        vague_count=specificity_score.vague_phrase_count,
        numeric_compliance=specificity_score.numeric_field_compliance,
    )

    # Update Langfuse observation with specificity metadata
    update_current_observation(
        metadata={
            "agent_type": agent_type,
            "specificity_score": specificity_score.overall_score,
            "quality_level": specificity_score.quality_level,
            "insights_count": _count_insights(findings, agent_type),
        }
    )

    # Flag low-specificity outputs
    if specificity_score.overall_score < LOW_SPECIFICITY_WARNING_THRESHOLD:
        logger.warning(
            "low_specificity_output",
            agent_type=agent_type,
            analysis_id=analysis_id,
            specificity_score=specificity_score.overall_score,
            quality_level=specificity_score.quality_level,
            vague_phrases=specificity_score.vague_phrase_count,
            numeric_values=specificity_score.numeric_value_count,
            expected_numeric_count=specificity_score.expected_numeric_count,
            # Include sample vague phrases for debugging
            sample_vague_phrases=[vp.phrase for vp in specificity_score.vague_phrases[:3]],
        )

    # Save to database
    # Normalize analysis_id to UUID (handles strings, UUID objects, and non-UUID strings)
    analysis_uuid = normalize_analysis_id_to_uuid(analysis_id)

    await save_agent_finding(
        session=session,
        analysis_id=analysis_uuid,
        agent_type=agent_type,
        findings=findings_clean,
        confidence_score=confidence_score,
        processing_time_ms=processing_time_ms,
    )

    # Extract rich details for SSE event
    findings_summary = _extract_findings_summary(findings, agent_type)
    insights_count = _count_insights(findings, agent_type)

    # Determine success metrics based on specificity score and insights
    quality_level = specificity_score.quality_level  # "high", "medium", "low"
    findings_quality = (
        "high" if quality_level == "high" else ("medium" if quality_level == "medium" else "low")
    )

    # Determine coverage based on insights count and specificity
    if (
        insights_count >= MIN_INSIGHTS_COMPREHENSIVE
        and specificity_score.overall_score >= MIN_SPECIFICITY_COMPREHENSIVE
    ):
        coverage = "comprehensive"
    elif insights_count >= MIN_INSIGHTS_PARTIAL:
        coverage = "partial"
    else:
        coverage = "minimal"

    # Extract key insights from findings (first 3 most important)
    key_insights: list[str] = []
    if agent_type == "tech_comparator":
        primary = findings.get("primary_tech")
        if primary:
            key_insights.append(f"Primary technology: {primary}")
    elif agent_type == "security_auditor":
        # Schema uses 'security_risks', not 'vulnerabilities'
        security_risks = findings.get("security_risks", [])
        if isinstance(security_risks, list) and security_risks:
            key_insights.append(f"Found {len(security_risks)} security risks")
    elif agent_type == "implementation_planner":
        # Schema uses 'steps', not 'implementation_steps'
        steps = findings.get("steps", [])
        if isinstance(steps, list) and steps:
            key_insights.append(f"Planned {len(steps)} implementation steps")
    # Add findings_summary as a key insight if available
    if findings_summary and len(key_insights) < MAX_KEY_INSIGHTS:
        key_insights.append(findings_summary)

    # Build success metrics
    success_metrics = {
        "findings_quality": findings_quality,
        "coverage": coverage,
        "key_insights": key_insights[:3],  # Limit to 3 insights
    }

    # Emit SSE event: agent complete with rich details
    await emit_agent_progress(
        analysis_id,
        agent_type,
        "complete",
        processing_time_ms=processing_time_ms,
        findings_summary=findings_summary,
        insights_count=insights_count,
        confidence_score=confidence_score,
        success_metrics=success_metrics,
    )

    logger.info(
        "agent_complete",
        agent_type=agent_type,
        analysis_id=analysis_id,
        processing_time_ms=processing_time_ms,
    )

    return {
        "agent_type": agent_type,
        "findings": findings,
        "confidence_score": confidence_score,  # Include at top level for template/validation
        "processing_time_ms": processing_time_ms,
        "specificity_score": specificity_score.overall_score,  # Include for monitoring
    }


async def handle_agent_cancellation(
    analysis_id: AnalysisID,
    agent_type: str,
    start_time: float,
) -> None:
    """Handle agent cancellation (GeneratorExit).

    Args:
        analysis_id: UUID of the analysis
        agent_type: Type of agent
        start_time: Start time for processing time calculation

    """
    processing_time_ms = int((time.time() - start_time) * 1000)
    logger.warning(
        "agent_generator_closed",
        agent_type=agent_type,
        analysis_id=analysis_id,
        processing_time_ms=processing_time_ms,
    )
    # Emit SSE event for cancellation
    await emit_agent_progress(
        analysis_id,
        agent_type,
        "cancelled",
        error="Agent execution was interrupted",
        error_code=f"{agent_type.upper()}_CANCELLED",
    )


async def handle_agent_error(
    error: Exception,
    analysis_id: AnalysisID,
    agent_type: str,
    start_time: float,
) -> None:
    """Handle agent execution error.

    Args:
        error: Exception that occurred
        analysis_id: UUID of the analysis
        agent_type: Type of agent
        start_time: Start time for processing time calculation

    """
    processing_time_ms = int((time.time() - start_time) * 1000)

    # Emit SSE event: agent failed
    await emit_agent_progress(
        analysis_id,
        agent_type,
        "failed",
        error=str(error),
        error_code=f"{agent_type.upper()}_FAILED",
    )

    logger.exception(
        "agent_failed",
        agent_type=agent_type,
        analysis_id=analysis_id,
        error=str(error),
        processing_time_ms=processing_time_ms,
    )
