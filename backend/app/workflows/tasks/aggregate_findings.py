"""Aggregate agent findings into coherent results.

This module handles the fan-in pattern for collecting and synthesizing
results from parallel agent execution using LLM synthesis.
"""

import time

from langsmith import traceable

from app.core.logging import get_logger
from app.services.sse_helpers import emit_streaming_event
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.invocation import invoke_agent
from app.workflows.agents.response_processing import extract_structured_response
from app.workflows.state import AnalysisState
from app.workflows.tasks.aggregation_fallback import (
    create_empty_aggregated_insights,
    create_fallback_aggregated_insights,
)
from app.workflows.tasks.aggregation_helpers import (
    detect_conflicts,
    format_findings_for_llm,
    validate_and_parse_findings,
)
from app.workflows.tasks.aggregation_postprocessing import (
    validate_and_format_aggregated_insights,
)
from app.workflows.tasks.prompt_builders import build_synthesis_user_prompt
from app.workflows.tasks.schemas.aggregated_insights import AggregatedInsights

logger = get_logger(__name__)

# LLM Synthesis System Prompt
SYNTHESIS_SYSTEM_PROMPT = """You are an expert technical analyst synthesizing findings from 8 specialized analysis agents. Your task is to create a cohesive, actionable narrative from potentially conflicting or overlapping insights.

AGENTS PROVIDED:
1. Tech Comparator - Technology comparisons and alternatives
2. Security Auditor - Security risks and best practices
3. Implementation Planner - Step-by-step implementation guidance
4. Integration Feasibility - Integration with modern stacks
5. Performance Analyst - Performance trade-offs and optimization
6. Code Quality Critic - Best practices and antipatterns
7. Trend Validator - Technology trend alignment (2025+)
8. Dependency Mapper - Required libraries and dependencies

YOUR TASKS:
1. Create an executive summary (2-3 sentences) that captures the essence of the entire analysis
2. Extract 3-7 key findings (bullet points) - prioritize by impact and importance
3. Synthesize technical analysis from all agents into coherent sections
4. Resolve any contradictions (prioritize higher confidence scores)
5. Provide unified recommendations

CONFIDENCE SCORES:
Each agent provides a confidence_score (0.0-1.0). When agents disagree, prioritize findings from agents with higher confidence scores.

OUTPUT REQUIREMENTS:
- Executive summary must be exactly 2-3 sentences
- Key findings must be 3-7 items, prioritized by impact
- Synthesis sections should combine insights from all relevant agents
- Conflicts should be clearly resolved with reasoning
"""


@traceable(
    name="aggregate_findings",
    run_type="chain",
    tags=["workflow", "node", "aggregation"],
)
async def aggregate_findings(  # noqa: PLR0915
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
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="aggregation",
        status="running",
        findings_count=len(agent_findings),
    )

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
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="aggregation",
            status="detecting_conflicts",
            findings_count=len(validated_findings),
        )

        conflicts = detect_conflicts(validated_findings)

        # Step 3: LLM Synthesis
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="aggregation",
            status="synthesizing",
            findings_count=len(validated_findings),
            conflicts_detected=len(conflicts),
        )

        logger.info(
            "workflow_aggregation_synthesizing",
            analysis_id=analysis_id,
            findings_count=len(validated_findings),
            conflicts_detected=len(conflicts),
        )

        # Format findings for LLM
        formatted_findings = format_findings_for_llm(
            validated_findings, conflicts, confidence_scores
        )

        # Create synthesis agent
        synthesis_agent = create_structured_agent(
            system_prompt=SYNTHESIS_SYSTEM_PROMPT,
            response_schema=AggregatedInsights,
        )

        # Build user prompt using prompt builder
        user_prompt = build_synthesis_user_prompt(formatted_findings=formatted_findings)

        # Calculate metadata values for use in both success and fallback paths
        confidence_values = list(confidence_scores.values())

        try:
            input_messages = {"messages": [{"role": "user", "content": user_prompt}]}

            # Invoke agent with timeout (120 seconds for synthesis)
            agent_timeout = 120.0
            final_result = await invoke_agent(
                agent=synthesis_agent,
                input_messages=input_messages,
                analysis_id=analysis_id,
                agent_type="aggregator",
                timeout=agent_timeout,
            )

            # Extract structured response (validated Pydantic model)
            structured_response = extract_structured_response(final_result, "aggregator")

            # structured_response is already a dict from extract_structured_response
            aggregated_insights_dict = structured_response

            # Step 4: Post-processing and validation
            aggregated_insights_dict = validate_and_format_aggregated_insights(
                aggregated_insights_dict
            )

            # Calculate metadata
            processing_time_ms = int((time.time() - start_time) * 1000)

            conflicts_resolved_raw = aggregated_insights_dict.get("conflicts_resolved", [])
            conflicts_resolved_list = (
                conflicts_resolved_raw if isinstance(conflicts_resolved_raw, list) else []
            )

            metadata = {
                "total_agents": len(validated_findings),
                "agents_executed": agent_types,
                "confidence_avg": (
                    sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
                ),
                "confidence_min": min(confidence_values) if confidence_values else 0.0,
                "confidence_max": max(confidence_values) if confidence_values else 0.0,
                "processing_time_ms": processing_time_ms,
                "conflicts_detected": len(conflicts),
                "conflicts_resolved": len(conflicts_resolved_list),
            }

            aggregated_insights_dict["metadata"] = metadata

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
        metadata_dict = aggregated_insights_dict.get("metadata", {})
        if not isinstance(metadata_dict, dict):
            metadata_dict = {}
        conflicts_resolved_count = metadata_dict.get("conflicts_resolved", 0)
        if not isinstance(conflicts_resolved_count, int):
            conflicts_resolved_count = 0

        key_findings_list = aggregated_insights_dict.get("key_findings", [])
        if not isinstance(key_findings_list, list):
            key_findings_list = []

        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="aggregation",
            status="complete",
            findings_count=len(validated_findings),
            conflicts_resolved=conflicts_resolved_count,
            key_findings_count=len(key_findings_list),
        )

        # Get conflicts_resolved for logging
        metadata_for_logging = aggregated_insights_dict.get("metadata", {})
        if isinstance(metadata_for_logging, dict):
            conflicts_resolved_for_log = metadata_for_logging.get("conflicts_resolved", 0)
            if not isinstance(conflicts_resolved_for_log, int):
                conflicts_resolved_for_log = 0
        else:
            conflicts_resolved_for_log = 0

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
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage="aggregation",
            status="failed",
            error=str(e),
            error_code="AGGREGATION_FAILED",
        )

        logger.error(
            "workflow_aggregation_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
