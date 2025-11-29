"""Aggregate agent findings into coherent results.

This module handles the fan-in pattern for collecting and synthesizing
results from parallel agent execution using LLM synthesis.
"""

import time

from langsmith import traceable

from app.core.logging import get_logger
from app.core.timeout_config import SYNTHESIS_TIMEOUT
from app.workflows.state import AnalysisState
from app.workflows.tasks.aggregation import (
    calculate_aggregation_metadata,
    emit_aggregation_complete,
    emit_aggregation_detecting_conflicts,
    emit_aggregation_failed,
    emit_aggregation_started,
    emit_aggregation_synthesizing,
    extract_metadata_for_logging,
    extract_sse_metadata,
    synthesize_with_llm,
    validate_and_parse_findings,
)
from app.workflows.tasks.aggregation_fallback import (
    create_empty_aggregated_insights,
    create_fallback_aggregated_insights,
)
from app.workflows.tasks.aggregation_helpers import detect_conflicts
from app.workflows.tasks.aggregation_postprocessing import validate_and_format_aggregated_insights
from app.workflows.utils.timeout_handling import handle_timeout_error

logger = get_logger(__name__)


@traceable(
    name="aggregate_findings",
    run_type="chain",
    tags=["workflow", "node", "aggregation"],
)
async def aggregate_findings(
    state: AnalysisState,
) -> dict[str, object]:
    """Aggregate agent findings into coherent results using LLM synthesis.

    This function implements the fan-in pattern, collecting results from
    all parallel agent executions and synthesizing them into a unified structure
    with conflict resolution and executive summary generation.

    Args:
        state: Current workflow state with agent_findings populated

    Returns:
        Dictionary with aggregated_insights field (to avoid LangGraph concurrent update errors)

    """
    analysis_id = state["analysis_id"]
    agent_findings = state.get("agent_findings", [])
    start_time = time.time()

    # Emit SSE event: aggregation started
    await emit_aggregation_started(analysis_id, len(agent_findings))

    logger.info(
        "workflow_aggregation_started",
        analysis_id=analysis_id,
        findings_count=len(agent_findings),
    )

    try:
        # Step 1: Validate and parse findings
        validated_findings, agent_types, confidence_scores = validate_and_parse_findings(
            agent_findings
        )

        if not validated_findings:
            logger.warning(
                "workflow_aggregation_no_findings",
                analysis_id=analysis_id,
            )
            # Return basic structure with no findings
            return {"aggregated_insights": create_empty_aggregated_insights(start_time)}

        # Step 2: Detect conflicts
        await emit_aggregation_detecting_conflicts(analysis_id, len(validated_findings))

        conflicts = detect_conflicts(validated_findings)

        # Step 3: LLM Synthesis
        await emit_aggregation_synthesizing(analysis_id, len(validated_findings), len(conflicts))

        logger.info(
            "workflow_aggregation_synthesizing",
            analysis_id=analysis_id,
            findings_count=len(validated_findings),
            conflicts_detected=len(conflicts),
        )

        try:
            # Step 3: LLM Synthesis using extracted function
            aggregated_insights_dict = await synthesize_with_llm(
                validated_findings=validated_findings,
                conflicts=conflicts,
                confidence_scores=confidence_scores,
                analysis_id=analysis_id,
            )

            # Step 4: Post-processing and validation
            aggregated_insights_dict = validate_and_format_aggregated_insights(
                aggregated_insights_dict
            )

            # Step 5: Calculate metadata using extracted function
            aggregated_insights_dict = calculate_aggregation_metadata(
                validated_findings=validated_findings,
                agent_types=agent_types,
                confidence_scores=confidence_scores,
                conflicts=conflicts,
                aggregated_insights_dict=aggregated_insights_dict,
                start_time=start_time,
            )

        except (TimeoutError, GeneratorExit) as timeout_error:
            # Timeout or cancellation during LLM synthesis
            # Use timeout utility for consistent error handling
            try:
                raise handle_timeout_error(
                    exc=timeout_error,
                    context="LLM synthesis",
                    timeout=SYNTHESIS_TIMEOUT,
                    logger=logger,
                    analysis_id=analysis_id,
                )
            except TimeoutError:
                # Logged by utility, fallback to basic aggregation without LLM synthesis
                aggregated_insights_dict = create_fallback_aggregated_insights(
                    validated_findings=validated_findings,
                    agent_types=agent_types,
                    confidence_scores=confidence_scores,
                    conflicts=conflicts,
                    start_time=start_time,
                )
        except Exception as llm_error:
            logger.error(
                "workflow_aggregation_llm_failed",
                analysis_id=analysis_id,
                error=str(llm_error),
                exc_info=True,
            )
            # Graceful fallback: return basic aggregation without LLM synthesis
            aggregated_insights_dict = create_fallback_aggregated_insights(
                validated_findings=validated_findings,
                agent_types=agent_types,
                confidence_scores=confidence_scores,
                conflicts=conflicts,
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

        # Return only updated fields, not entire state
        return {"aggregated_insights": aggregated_insights_dict}

    except Exception as e:
        # Emit SSE event: aggregation failed
        await emit_aggregation_failed(analysis_id, str(e))

        logger.error(
            "workflow_aggregation_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
