"""Aggregate agent findings into coherent results.

This module handles the fan-in pattern for collecting and synthesizing
results from parallel agent execution using LLM synthesis.

Issue #269: Stores agent findings as memories after aggregation for
the Context Engineering feedback loop.
"""

import time
from typing import Any, cast
from uuid import UUID

from app.core.exceptions import WorkflowStageError
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.core.types import AnalysisID
from app.db.models.agent_memory import MemoryType
from app.db.session import get_session_factory
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.state_accessors import (
    get_agent_findings,
    get_extraction_metadata,
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
from app.domains.analysis.workflows.tasks.aggregation.data_sufficiency import (
    calculate_data_sufficiency,
    format_coverage_gaps_for_synthesis,
)
from app.domains.analysis.workflows.tasks.aggregation.grounding_validator import (
    validate_grounding,
)
from app.domains.analysis.workflows.tasks.aggregation.source_content_extractor import (
    extract_source_summary,
)
from app.domains.analysis.workflows.tasks.aggregation_fallback import (
    create_empty_aggregated_insights,
    synthesize_trend_summary,
)
from app.domains.analysis.workflows.tasks.aggregation_helpers import (
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


async def _build_agent_statuses(
    analysis_id: AnalysisID,
    selected_agents: list[str],
    agent_types: list[str],
) -> dict[str, str]:
    """Build agent statuses dict and emit error events for failed agents.

    Args:
        analysis_id: UUID of the analysis
        selected_agents: List of agent types selected by supervisor
        agent_types: List of agent types that produced findings

    Returns:
        Dictionary mapping agent_type to "success" or "failed"

    """
    from app.core.agent_config import get_stage_name
    from app.shared.services.messaging.sse_helpers import emit_error_event

    agent_statuses: dict[str, str] = {}
    for agent_type in selected_agents:
        if agent_type in agent_types:
            agent_statuses[agent_type] = "success"
        else:
            # Selected but no findings = failed
            agent_statuses[agent_type] = "failed"
            # Emit error event for agent failure
            await emit_error_event(
                analysis_id=analysis_id,
                stage=get_stage_name(agent_type),
                error=f"Agent {agent_type} was selected but produced no findings",
                error_code="AGENT_FAILED",
                agent_type=agent_type,
            )
    # Note: Skipped agents (not in selected_agents) are not included in agent_statuses
    return agent_statuses


async def _handle_aggregation_error(
    analysis_id: AnalysisID,
    error: Exception,
    start_time: float,
    agent_types: list[str] | None,
) -> dict[str, object]:
    """Handle aggregation errors by wrapping with WorkflowStageError.

    Args:
        analysis_id: UUID of the analysis
        error: Exception that occurred during aggregation
        start_time: Start time for calculating processing duration
        agent_types: List of agent types that produced findings (may be None)

    Raises:
        WorkflowStageError: Wrapped exception with stage context

    """
    # Record error to database FIRST to make failure visible
    from app.domains.analysis.constants.error_codes import AGGREGATION_FAILED
    from app.domains.analysis.services.persistence.error_recorder import error_recorder

    try:
        await error_recorder.record(
            analysis_id=str(analysis_id),
            error_code=AGGREGATION_FAILED,
            error_message=str(error),
            stage="aggregate_findings",
        )
    except Exception:  # noqa: S110, BLE001 - Graceful degradation for error recording failures
        # Don't fail if error recording fails (e.g., invalid UUID in tests)
        pass

    await emit_aggregation_failed(analysis_id, str(error))

    # Build a meaningful error message with agent count if available
    try:
        agent_count = len(agent_types) if agent_types else 0
    except (NameError, UnboundLocalError):
        agent_count = 0

    if agent_count > 0:
        error_message = f"Aggregation failed after processing {agent_count} agents: {error}"
    else:
        error_message = f"Aggregation failed: {error}"

    logger.error(
        "workflow_aggregation_failed",
        analysis_id=analysis_id,
        error=str(error),
        error_type=type(error).__name__,
        exc_info=error,
        agent_count=agent_count,
        processing_time_ms=int((time.time() - start_time) * 1000),
    )

    # Wrap with WorkflowStageError to provide stage context
    raise WorkflowStageError(
        stage="aggregation",
        original_exception=error,
        message=error_message,
    ) from error


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

                except Exception as e:  # noqa: BLE001 - Graceful degradation: individual memory storage failures
                    # Log but don't fail - individual memory failures shouldn't break flow
                    logger.warning(
                        "finding_memory_store_error",
                        analysis_id=analysis_id,
                        agent_type=agent_type_str,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

    except Exception as e:  # noqa: BLE001 - Graceful degradation: memory storage is optional
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


async def _aggregate_findings_impl(  # noqa: PLR0912, PLR0915 - Complex aggregation logic requires many branches and statements
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
    # Issue #441: Skip if workflow is aborting
    from app.domains.analysis.workflows.utils.abort_helpers import check_should_abort

    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}

    analysis_id = state["analysis_id"]
    agent_findings = get_agent_findings(state)
    start_time = time.time()

    # Runtime metadata updates for Langfuse
    try:
        from app.core.tracing import update_current_trace

        update_current_trace(
            metadata={"analysis_id": str(analysis_id)},
            session_id=f"analysis-{analysis_id}",
            user_id="anonymous",
        )
    except Exception:  # noqa: S110, BLE001 - Langfuse may not be available
        pass

    # Emit SSE event: aggregation started
    await emit_aggregation_started(analysis_id, len(agent_findings))

    logger.info(
        "workflow_aggregation_started",
        analysis_id=analysis_id,
        findings_count=len(agent_findings),
    )

    # Initialize agent_types to None for error handling (will be set in try block)
    agent_types: list[str] | None = None

    try:
        # Extract selected_agents from supervisor_decision
        supervisor_decision = get_supervisor_decision(state)
        selected_agents_raw = supervisor_decision.get("agents", [])
        selected_agents: list[str] = (
            selected_agents_raw if isinstance(selected_agents_raw, list) else []
        )

        # Issue #547 (GAP 4): Extract expected_agent_count for fan-in validation
        # This allows us to detect when agents were selected but didn't run
        expected_agent_count = supervisor_decision.get("expected_agent_count", len(selected_agents))

        # Step 1: Validate and parse findings
        validated_findings, agent_types, confidence_scores = validate_and_parse_findings(
            agent_findings
        )

        # Issue #547 (GAP 4): Log fan-in validation for debugging stuck aggregation
        actual_agent_count = len(agent_types) if agent_types else 0
        if actual_agent_count != expected_agent_count:
            logger.warning(
                "workflow_aggregation_agent_count_mismatch",
                analysis_id=analysis_id,
                expected_agent_count=expected_agent_count,
                actual_agent_count=actual_agent_count,
                selected_agents=selected_agents,
                agents_with_findings=agent_types,
                missing_agents=[a for a in selected_agents if a not in (agent_types or [])],
            )
        else:
            logger.info(
                "workflow_aggregation_fan_in_complete",
                analysis_id=analysis_id,
                expected_agent_count=expected_agent_count,
                actual_agent_count=actual_agent_count,
            )

        # Build agent_statuses dict: compare selected_agents vs agent_types
        # Emit error events for agents that were selected but produced no findings
        agent_statuses = await _build_agent_statuses(
            analysis_id=analysis_id,
            selected_agents=selected_agents,
            agent_types=agent_types,
        )

        if not validated_findings:
            logger.warning(
                "workflow_aggregation_no_findings",
                analysis_id=analysis_id,
            )
            # Return basic structure with no findings, but include agent_statuses
            empty_insights = create_empty_aggregated_insights(start_time)
            empty_insights["agent_statuses"] = agent_statuses
            return {"aggregated_insights": empty_insights}

        # Issue #487: Abort if ALL agents report insufficient data
        # Prevents hallucination when source has no implementable content (e.g., news articles)
        all_insufficient = all(
            finding.get("findings", {}).get("data_availability") == "insufficient"
            for finding in validated_findings
        )
        if all_insufficient:
            logger.error(
                "workflow_all_agents_insufficient_data",
                analysis_id=analysis_id,
                agent_count=len(validated_findings),
            )
            msg = (
                "Cannot generate implementation guide: Source content contains no "
                "implementable code or technical patterns. All agents reported "
                "insufficient data for analysis. Consider analyzing content with "
                "code examples, architectural diagrams, or technical specifications."
            )
            raise ValueError(msg)

        # Step 1.5: Calculate data sufficiency using weighted scoring (Issue #487)
        # This provides more nuanced coverage analysis based on data_availability levels
        # and recommends synthesis mode (normal/limited/fallback)
        data_sufficiency_result = calculate_data_sufficiency(validated_findings)

        # Use weighted coverage score and properly formatted gaps
        coverage_score = data_sufficiency_result.coverage_score
        coverage_gaps = format_coverage_gaps_for_synthesis(data_sufficiency_result.coverage_gaps)

        # Also detect gaps for agents that didn't contribute at all
        # (handles agents that were selected but produced no findings)
        missing_agent_gaps = detect_coverage_gaps(
            contributing_agents=agent_types,
            agent_findings=validated_findings,
            selected_agents=selected_agents if selected_agents else None,
        )
        # Combine gaps from data_sufficiency (limited/insufficient) with missing agent gaps
        coverage_gaps.extend(missing_agent_gaps)

        logger.debug(
            "workflow_coverage_analysis",
            analysis_id=analysis_id,
            contributing_agents=len(agent_types),
            coverage_score=f"{coverage_score:.2%}",
            gaps_detected=len(coverage_gaps),
            recommended_mode=data_sufficiency_result.recommended_mode,
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

        # Step 5: Extract source context for LLM grounding (Issue #487 - Hallucination Prevention)
        # This provides the LLM with actual source content to prevent fabrication
        source_context = None
        raw_content = state.get("raw_content", "")
        if raw_content:
            extraction_metadata = get_extraction_metadata(state)
            source_context = extract_source_summary(
                raw_content=raw_content,
                extraction_metadata=cast("dict[str, Any]", extraction_metadata),
                max_chars=2000,  # Sufficient context without overwhelming token budget
            )
            logger.debug(
                "source_context_extracted_for_grounding",
                analysis_id=analysis_id,
                title=source_context.get("title", "N/A"),
                summary_length=len(source_context.get("summary", "")),
                key_terms_count=len(source_context.get("key_terms", [])),
            )

        # Step 6: LLM Synthesis - choose mode based on data sufficiency (Issue #487)
        # If recommended_mode is "fallback", use trend-summary synthesis instead
        # of normal synthesis to prevent hallucinating implementation details
        if data_sufficiency_result.recommended_mode == "fallback":
            logger.info(
                "workflow_using_trend_summary_synthesis",
                analysis_id=analysis_id,
                coverage_score=f"{coverage_score:.2%}",
                reason=data_sufficiency_result.recommendation_reason,
            )
            # Use trend-summary synthesis for low-coverage content
            aggregated_insights_dict = await synthesize_trend_summary(
                validated_findings=validated_findings,
                analysis_id=analysis_id,
                coverage_score=coverage_score,
                source_context=source_context,
            )
        else:
            # Normal synthesis with tiered fallback chain (Issue #299-304)
            # The synthesize_with_llm NEVER raises exceptions - it falls back
            # through tiers (FULL -> REDUCED -> MINIMAL -> STATIC) until one succeeds.
            # Issue #487: Now includes source_context to prevent hallucinations
            aggregated_insights_dict = await synthesize_with_llm(
                validated_findings=validated_findings,
                conflicts=conflicts,
                confidence_scores=confidence_scores,
                analysis_id=analysis_id,
                source_context=source_context,
            )

        # Step 7: Post-processing and validation
        aggregated_insights_dict = validate_and_format_aggregated_insights(aggregated_insights_dict)

        # Step 7.5: Validate grounding to prevent hallucinations (Issue #487)
        # Check if generated content is grounded in source material
        if source_context and aggregated_insights_dict:
            # Combine source title and summary for grounding check
            source_text = source_context.get("summary", "") + " " + source_context.get("title", "")
            generated_text = aggregated_insights_dict.get("executive_summary", "")

            if source_text.strip() and generated_text.strip():
                is_grounded, grounding_score, warnings = validate_grounding(
                    source_content=source_text,
                    generated_content=generated_text,
                    min_overlap=0.15,  # 15% minimum overlap threshold
                )

                # Store grounding validation results in metadata for observability
                grounding_metadata = {
                    "is_grounded": is_grounded,
                    "grounding_score": grounding_score,
                    "warnings": warnings,
                }

                # Add to aggregated insights metadata
                existing_metadata = cast(
                    "dict[str, object]", aggregated_insights_dict.get("metadata", {})
                )
                existing_metadata["grounding_validation"] = grounding_metadata
                aggregated_insights_dict["metadata"] = existing_metadata

                # Issue #487: BLOCK hallucinated content when grounding fails
                if not is_grounded:
                    logger.warning(
                        "hallucination_blocked",
                        grounding_score=grounding_score,
                        analysis_id=str(analysis_id),
                        warnings=warnings,
                        action="replacing_with_source_grounded_content",
                    )

                    # Replace hallucinated executive_summary with source-grounded version
                    source_title = source_context.get("title", "this content")
                    source_summary = source_context.get("summary", "")

                    # Create safe executive summary from source
                    if source_summary:
                        safe_summary = (
                            f"This analysis covers {source_title}. {source_summary[:500]}"
                        )
                    else:
                        safe_summary = (
                            f"This analysis covers {source_title}. "
                            "Due to limited technical content in the source material, "
                            "detailed implementation guidance is not available."
                        )
                    aggregated_insights_dict["executive_summary"] = safe_summary

                    # Replace key_findings with honest acknowledgment
                    aggregated_insights_dict["key_findings"] = [
                        f"Source: {source_title}",
                        "Limited technical implementation details available in source content.",
                        "This appears to be news/announcement content rather than technical documentation.",
                    ]

                    # Mark synthesis as replaced due to hallucination
                    existing_metadata["hallucination_blocked"] = True
                    existing_metadata["original_grounding_score"] = grounding_score
                    aggregated_insights_dict["metadata"] = existing_metadata

                    logger.info(
                        "hallucination_replaced_with_safe_content",
                        analysis_id=str(analysis_id),
                        source_title=source_title,
                    )
                else:
                    logger.info(
                        "grounding_validation_passed",
                        grounding_score=grounding_score,
                        analysis_id=str(analysis_id),
                    )

        # Step 8: Add quick_reference to aggregated insights
        if quick_reference:
            aggregated_insights_dict["quick_reference"] = quick_reference.model_dump()

        # Step 8.5: Add coverage gaps, coverage score, and agent_statuses
        aggregated_insights_dict["coverage_gaps"] = coverage_gaps
        aggregated_insights_dict["coverage_score"] = coverage_score
        aggregated_insights_dict["agent_statuses"] = agent_statuses

        # Step 9: Calculate metadata using extracted function
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

        # Step 10: Store findings as memories for future recall (Issue #269)
        # This enables the Context Engineering feedback loop
        stored_memories = await _store_findings_as_memories(
            analysis_id=analysis_id,
            agent_findings=validated_findings,
        )

        # Add memory storage and synthesis status metadata to insights
        metadata: dict[str, object] = dict(aggregated_insights_dict.get("metadata", {}))  # type: ignore[call-overload]
        metadata["memories_stored"] = stored_memories
        # Issue #299-304: Track synthesis status for debugging
        if "synthesis_status" not in metadata:
            metadata["synthesis_status"] = "success"
        # Issue #487: Store data sufficiency recommendation for fallback logic
        metadata["data_sufficiency"] = {
            "coverage_score": data_sufficiency_result.coverage_score,
            "recommended_mode": data_sufficiency_result.recommended_mode,
            "recommendation_reason": data_sufficiency_result.recommendation_reason,
            "agents_with_data": data_sufficiency_result.agents_with_data,
            "total_agents": data_sufficiency_result.total_agents,
        }
        aggregated_insights_dict["metadata"] = metadata

        # Return only updated fields, not entire state
        return {"aggregated_insights": aggregated_insights_dict}

    except Exception as e:
        # Handle and wrap error with WorkflowStageError for proper stage context
        await _handle_aggregation_error(
            analysis_id=analysis_id,
            error=e,
            start_time=start_time,
            agent_types=agent_types,
        )
        # This line is never reached - _handle_aggregation_error always raises
        raise  # pragma: no cover


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
    which intercepts cleanup exceptions before Langfuse captures them.

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Dictionary with aggregated_insights field (to avoid LangGraph concurrent update errors)

    """
    return await _aggregate_findings_impl(state)
