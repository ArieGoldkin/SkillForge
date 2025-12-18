"""Aggregate agent findings into coherent results.

This module handles the fan-in pattern for collecting and synthesizing
results from parallel agent execution using LLM synthesis.

Issue #269: Stores agent findings as memories after aggregation for
the Context Engineering feedback loop.
"""

import time
from uuid import UUID

from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.db.models.agent_memory import MemoryType
from app.db.session import get_session_factory
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.state_accessors import (
    get_agent_findings,
    get_supervisor_decision,
)
from app.domains.analysis.workflows.tasks.aggregation import (
    calculate_aggregation_metadata,
    emit_aggregation_complete,
    emit_aggregation_detecting_conflicts,
    emit_aggregation_failed,
    emit_aggregation_started,
    emit_aggregation_synthesizing,
    extract_metadata_for_logging,
    extract_quick_reference,
    extract_sse_metadata,
    synthesize_with_llm,
    validate_and_parse_findings,
)
from app.domains.analysis.workflows.tasks.aggregation_fallback import (
    create_empty_aggregated_insights,
)
from app.domains.analysis.workflows.tasks.aggregation_helpers import (
    calculate_coverage_score,
    detect_conflicts,
    detect_coverage_gaps,
)
from app.domains.analysis.workflows.tasks.aggregation_postprocessing import (
    validate_and_format_aggregated_insights,
)
from app.shared.services.memory.agent_memory_service import AgentMemoryService

logger = get_logger(__name__)


# Agent type to memory type mapping for storing findings
AGENT_MEMORY_TYPE_MAP: dict[str, MemoryType] = {
    "security_auditor": MemoryType.VULNERABILITY_PATTERN,
    "code_quality_critic": MemoryType.BEST_PRACTICE,
    "tech_comparator": MemoryType.ANALYSIS_SUMMARY,
    "implementation_planner": MemoryType.BEST_PRACTICE,
    "performance_analyst": MemoryType.BEST_PRACTICE,
    "dependency_mapper": MemoryType.ANALYSIS_SUMMARY,
    "trend_validator": MemoryType.ANALYSIS_SUMMARY,
    "integration_feasibility": MemoryType.BEST_PRACTICE,
}


async def _store_findings_as_memories(
    analysis_id: str,
    agent_findings: list[dict[str, object]],
) -> int:
    """Store agent findings as memories for future proactive recall.

    Issue #269: Closes the Context Engineering feedback loop by storing
    findings from each agent as searchable memories with embeddings.

    Args:
        analysis_id: The analysis that produced these findings
        agent_findings: List of validated agent findings

    Returns:
        Number of memories successfully stored

    Note:
        Failures are logged but don't raise - memory storage should never
        break the aggregation flow.

    """
    if not agent_findings:
        return 0

    stored_count = 0

    try:
        # Get database session
        session_factory = get_session_factory()
        async with session_factory() as session:
            memory_service = AgentMemoryService(session)

            for finding in agent_findings:
                agent_type = finding.get("agent_type")
                finding_data = finding.get("findings", {})

                if not agent_type or not finding_data:
                    continue

                # Ensure agent_type is a string
                agent_type_str = str(agent_type)

                # Get appropriate memory type for this agent
                memory_type = AGENT_MEMORY_TYPE_MAP.get(agent_type_str, MemoryType.AGENT_FINDING)

                # Create content string from findings
                content = _extract_finding_content(agent_type_str, finding_data)

                if not content:
                    continue

                try:
                    # Parse analysis_id to UUID
                    analysis_uuid = UUID(analysis_id)

                    # Extract confidence score if available
                    confidence = finding.get("confidence_score", 1.0)
                    relevance_score = (
                        float(confidence) if isinstance(confidence, (int, float)) else 1.0
                    )

                    # Store the memory
                    await memory_service.store(
                        content=content,
                        memory_type=memory_type,
                        analysis_id=analysis_uuid,
                        agent_type=agent_type_str,
                        metadata={
                            "source": "aggregation",
                            "finding_keys": list(finding_data.keys())
                            if isinstance(finding_data, dict)
                            else [],
                        },
                        relevance_score=relevance_score,
                    )

                    stored_count += 1

                    logger.debug(
                        "finding_stored_as_memory",
                        analysis_id=analysis_id,
                        agent_type=agent_type_str,
                        memory_type=memory_type.value,
                        content_length=len(content),
                    )

                except Exception as e:  # noqa: BLE001
                    # Log but don't fail - individual memory failures shouldn't break flow
                    logger.warning(
                        "finding_memory_store_error",
                        analysis_id=analysis_id,
                        agent_type=agent_type_str,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

    except Exception as e:  # noqa: BLE001
        # Database connection or session errors
        logger.warning(
            "findings_memory_store_session_error",
            analysis_id=analysis_id,
            error=str(e),
            error_type=type(e).__name__,
            fallback="continuing_without_memory_storage",
        )
        return 0

    logger.info(
        "findings_stored_as_memories",
        analysis_id=analysis_id,
        total_findings=len(agent_findings),
        stored_count=stored_count,
    )

    return stored_count


def _extract_finding_content(agent_type: str, finding_data: object) -> str:
    """Extract meaningful content string from agent finding data.

    Args:
        agent_type: Type of agent that produced the finding
        finding_data: The findings dictionary or object

    Returns:
        Formatted content string suitable for embedding

    """
    if not finding_data:
        return ""

    if not isinstance(finding_data, dict):
        return str(finding_data)[:2000]

    # Build content from key finding fields based on agent type
    parts = _extract_common_fields(finding_data)
    parts.extend(_extract_agent_specific_fields(agent_type, finding_data))

    # If no specific fields found, create general summary
    if not parts:
        parts = _extract_fallback_summary(finding_data)

    # Join all parts and truncate if too long
    content = "\n".join(parts)
    return content[:2000]  # Max 2000 chars for embedding


def _extract_common_fields(finding_data: dict) -> list[str]:
    """Extract common fields present in most findings."""
    parts = []
    if "recommendation" in finding_data:
        parts.append(f"Recommendation: {finding_data['recommendation']}")
    if "summary" in finding_data:
        parts.append(f"Summary: {finding_data['summary']}")
    return parts


def _extract_agent_specific_fields(agent_type: str, finding_data: dict) -> list[str]:
    """Extract agent-specific fields based on agent type."""
    extractors = {
        "security_auditor": _extract_security_fields,
        "tech_comparator": _extract_tech_fields,
        "implementation_planner": _extract_implementation_fields,
        "performance_analyst": _extract_performance_fields,
        "code_quality_critic": _extract_quality_fields,
    }
    extractor = extractors.get(agent_type)
    return extractor(finding_data) if extractor else []


def _extract_security_fields(finding_data: dict) -> list[str]:
    """Extract security auditor specific fields."""
    parts = []
    risks = finding_data.get("security_risks")
    if risks and isinstance(risks, list):
        risk_strs = [
            f"{r.get('risk_type', 'unknown')}: {r.get('description', '')}"
            for r in risks[:5]
            if isinstance(r, dict)
        ]
        if risk_strs:
            parts.append(f"Security Risks: {'; '.join(risk_strs)}")
    return parts


def _extract_tech_fields(finding_data: dict) -> list[str]:
    """Extract tech comparator specific fields."""
    parts = []
    if "primary_tech" in finding_data:
        parts.append(f"Primary Technology: {finding_data['primary_tech']}")
    alts = finding_data.get("alternatives")
    if alts and isinstance(alts, list):
        parts.append(f"Alternatives: {', '.join(str(a) for a in alts[:5])}")
    return parts


def _extract_implementation_fields(finding_data: dict) -> list[str]:
    """Extract implementation planner specific fields."""
    parts = []
    prereqs = finding_data.get("prerequisites")
    if prereqs and isinstance(prereqs, list):
        parts.append(f"Prerequisites: {', '.join(str(p) for p in prereqs[:5])}")
    return parts


def _extract_performance_fields(finding_data: dict) -> list[str]:
    """Extract performance analyst specific fields."""
    parts = []
    if "performance_concerns" in finding_data:
        parts.append(f"Performance Concerns: {finding_data['performance_concerns']}")
    return parts


def _extract_quality_fields(finding_data: dict) -> list[str]:
    """Extract code quality critic specific fields."""
    parts = []
    issues = finding_data.get("quality_issues")
    if issues and isinstance(issues, list):
        parts.append(f"Quality Issues: {'; '.join(str(i) for i in issues[:5])}")
    return parts


def _extract_fallback_summary(finding_data: dict) -> list[str]:
    """Extract fallback summary when no specific fields found."""
    summary_parts = []
    for key, value in list(finding_data.items())[:5]:
        if isinstance(value, (str, int, float, bool)):
            summary_parts.append(f"{key}: {value}")
        elif isinstance(value, list):
            summary_parts.append(f"{key}: {len(value)} items")
    return ["; ".join(summary_parts)] if summary_parts else []


async def _aggregate_findings_impl(  # noqa: PLR0915 - Complex aggregation logic requires many statements
    state: AnalysisState,
) -> dict[str, object]:
    """Aggregate agent findings implementation.

    This function contains the actual implementation logic.
    GeneratorExit handling is managed by the robust_traceable wrapper.

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Dictionary with aggregated_insights field (to avoid LangGraph concurrent update errors)

    """
    analysis_id = state["analysis_id"]
    agent_findings = get_agent_findings(state)
    start_time = time.time()

    # Emit SSE event: aggregation started
    await emit_aggregation_started(analysis_id, len(agent_findings))

    logger.info(
        "workflow_aggregation_started",
        analysis_id=analysis_id,
        findings_count=len(agent_findings),
    )

    try:
        # Extract selected_agents from supervisor_decision
        supervisor_decision = get_supervisor_decision(state)
        selected_agents_raw = supervisor_decision.get("agents", [])
        selected_agents: list[str] = (
            selected_agents_raw if isinstance(selected_agents_raw, list) else []
        )

        # Step 1: Validate and parse findings
        validated_findings, agent_types, confidence_scores = validate_and_parse_findings(
            agent_findings
        )

        # Build agent_statuses dict: compare selected_agents vs agent_types
        agent_statuses: dict[str, str] = {}
        for agent_type in selected_agents:
            if agent_type in agent_types:
                agent_statuses[agent_type] = "success"
            else:
                # Selected but no findings = failed
                agent_statuses[agent_type] = "failed"
        # Note: Skipped agents (not in selected_agents) are not included in agent_statuses

        if not validated_findings:
            logger.warning(
                "workflow_aggregation_no_findings",
                analysis_id=analysis_id,
            )
            # Return basic structure with no findings, but include agent_statuses
            empty_insights = create_empty_aggregated_insights(start_time)
            empty_insights["agent_statuses"] = agent_statuses
            return {"aggregated_insights": empty_insights}

        # Step 1.5: Detect coverage gaps and calculate coverage score
        # Issue #299-304: Pass validated_findings to detect data availability gaps
        # Fix: Pass selected_agents to only check selected agents, not all agents
        coverage_gaps = detect_coverage_gaps(
            contributing_agents=agent_types,
            agent_findings=validated_findings,
            selected_agents=selected_agents if selected_agents else None,
        )
        coverage_score = calculate_coverage_score(agent_types)

        logger.debug(
            "workflow_coverage_analysis",
            analysis_id=analysis_id,
            contributing_agents=len(agent_types),
            coverage_score=coverage_score,
            gaps_detected=len(coverage_gaps),
        )

        # Step 2: Extract Quick Reference (before LLM synthesis for efficiency)
        quick_reference = extract_quick_reference(agent_findings)
        if quick_reference:
            logger.info(
                "workflow_quick_reference_extracted",
                analysis_id=analysis_id,
                primary_technology=quick_reference.primary_technology,
            )

        # Step 3: Detect conflicts
        await emit_aggregation_detecting_conflicts(analysis_id, len(validated_findings))

        conflicts = detect_conflicts(validated_findings)

        # Step 4: LLM Synthesis
        await emit_aggregation_synthesizing(analysis_id, len(validated_findings), len(conflicts))

        logger.info(
            "workflow_aggregation_synthesizing",
            analysis_id=analysis_id,
            findings_count=len(validated_findings),
            conflicts_detected=len(conflicts),
        )

        # Step 5: LLM Synthesis with tiered fallback chain (Issue #299-304)
        # The new synthesize_with_llm NEVER raises exceptions - it falls back
        # through tiers (FULL -> REDUCED -> MINIMAL -> STATIC) until one succeeds.
        # Static fallback extracts content from findings, so it always completes.
        aggregated_insights_dict = await synthesize_with_llm(
            validated_findings=validated_findings,
            conflicts=conflicts,
            confidence_scores=confidence_scores,
            analysis_id=analysis_id,
        )

        # Step 6: Post-processing and validation
        aggregated_insights_dict = validate_and_format_aggregated_insights(aggregated_insights_dict)

        # Step 7: Add quick_reference to aggregated insights
        if quick_reference:
            aggregated_insights_dict["quick_reference"] = quick_reference.model_dump()

        # Step 7.5: Add coverage gaps, coverage score, and agent_statuses
        aggregated_insights_dict["coverage_gaps"] = coverage_gaps
        aggregated_insights_dict["coverage_score"] = coverage_score
        aggregated_insights_dict["agent_statuses"] = agent_statuses

        # Step 8: Calculate metadata using extracted function
        aggregated_insights_dict = calculate_aggregation_metadata(
            validated_findings=validated_findings,
            agent_types=agent_types,
            confidence_scores=confidence_scores,
            conflicts=conflicts,
            aggregated_insights_dict=aggregated_insights_dict,
            start_time=start_time,
        )

        # Emit SSE event: aggregation complete
        conflicts_resolved_count, key_findings_count = extract_sse_metadata(
            aggregated_insights_dict
        )
        await emit_aggregation_complete(
            analysis_id, len(validated_findings), conflicts_resolved_count, key_findings_count
        )

        # Log completion
        conflicts_resolved_for_log = extract_metadata_for_logging(aggregated_insights_dict)
        logger.info(
            "workflow_aggregation_complete",
            analysis_id=analysis_id,
            findings_count=len(validated_findings),
            conflicts_resolved=conflicts_resolved_for_log,
        )

        # Step 9: Store findings as memories for future recall (Issue #269)
        # This enables the Context Engineering feedback loop
        stored_memories = await _store_findings_as_memories(
            analysis_id=analysis_id,
            agent_findings=validated_findings,
        )

        # Add memory storage and synthesis status metadata to insights
        metadata: dict[str, object] = dict(aggregated_insights_dict.get("metadata", {}))  # type: ignore[arg-type]
        metadata["memories_stored"] = stored_memories
        # Issue #299-304: Track synthesis status for debugging
        if "synthesis_status" not in metadata:
            metadata["synthesis_status"] = "success"
        aggregated_insights_dict["metadata"] = metadata

        # Return only updated fields, not entire state
        return {"aggregated_insights": aggregated_insights_dict}

    except Exception as e:
        # Issue #299-304: Error State Pattern - capture errors in state, don't propagate
        # This ensures the workflow ALWAYS reaches a terminal state
        await emit_aggregation_failed(analysis_id, str(e))

        logger.error(
            "workflow_aggregation_failed_with_fallback",
            analysis_id=analysis_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
            fallback="returning_empty_insights_to_prevent_hang",
        )

        # Build a meaningful executive summary with agent count if available
        # This provides better context for the fallback response
        try:
            agent_count = len(agent_types) if agent_types else 0
        except (NameError, UnboundLocalError):
            agent_count = 0

        if agent_count > 0:
            exec_summary = f"Synthesized findings from {agent_count} agents. LLM synthesis failed but basic findings are available."
        else:
            exec_summary = f"Analysis could not be completed due to error: {type(e).__name__}"

        # Return empty insights with error metadata instead of raising
        # This allows the workflow to continue to artifact generation (which will handle empty insights)
        return {
            "aggregated_insights": {
                "executive_summary": exec_summary,
                "key_findings": ["Analysis encountered an error during synthesis"],
                "synthesis": "Unable to synthesize findings due to processing error.",
                "metadata": {
                    "synthesis_status": "failed",
                    "synthesis_error": str(e),
                    "error_type": type(e).__name__,
                    "processing_time_ms": int((time.time() - start_time) * 1000),
                    "fallback_used": True,
                    "llm_synthesis_failed": True,
                    "total_agents": agent_count,
                },
                "coverage_gaps": [],
                "coverage_score": 0.0,
            }
        }


@robust_traceable(
    name="aggregate_findings",
    run_type="chain",
    tags=["workflow", "node", "aggregation"],
)
async def aggregate_findings(
    state: AnalysisState,
) -> dict[str, object]:
    """Aggregate agent findings into coherent results using LLM synthesis.

    GeneratorExit handling is managed by the robust_traceable wrapper,
    which intercepts cleanup exceptions before LangSmith captures them.

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Dictionary with aggregated_insights field (to avoid LangGraph concurrent update errors)

    """
    return await _aggregate_findings_impl(state)
