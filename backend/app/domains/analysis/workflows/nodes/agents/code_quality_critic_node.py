"""Code quality critic agent node for LangGraph StateGraph.

Note: This node does NOT use @robust_traceable decorator because LangGraph
automatically traces all node executions. Adding @robust_traceable would
create duplicate spans in Langfuse. Runtime metadata is still updated
via update_current_trace().

Issue #244: Uses Handle Pattern - content loaded via content_ref (ArtifactStore)
with fallback to raw_content for backward compatibility.
"""

import time
from typing import cast

from langfuse import observe

from app.core.bulkhead import BulkheadFullError, BulkheadTimeoutError
from app.core.logging import get_logger
from app.core.tracing import get_current_trace_id, update_current_trace
from app.domains.analysis.agents.registry import get_agent_metadata
from app.domains.analysis.constants.error_codes import (
    AGENT_NO_CONTENT,
    AgentStatus,
)
from app.domains.analysis.workflows.agents.base import (
    handle_agent_node_error,
    record_agent_execution,
)
from app.domains.analysis.workflows.agents.resilience_wrapper import (
    execute_with_resilience,
)
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.runners import (
    get_fallback_content,
    has_content_available,
    run_code_quality_critic_with_session,
)

logger = get_logger(__name__)


@observe(as_type="agent", name="code_quality_critic", capture_input=True, capture_output=True)
async def code_quality_critic_node(state: AnalysisState) -> dict[str, object]:
    """Code quality critic agent node.

    Executes code quality analysis and returns findings.
    Each agent node manages its own database session for parallel execution.

    Issue #244: Uses Handle Pattern for content loading:
    1. Checks content_ref (preferred) or raw_content (fallback) availability
    2. Runner loads optimized content section via ArtifactStore
    3. Falls back to raw_content if artifact loading fails

    Note: LangGraph automatically traces this node. We update runtime metadata
    via update_current_trace() but don't add a separate tracing decorator.

    Args:
        state: Current workflow state with content_ref or raw_content

    Returns:
        Dictionary with agent_findings containing single result

    """
    # Issue #441: Skip if workflow is aborting
    from app.domains.analysis.workflows.utils.abort_helpers import check_should_abort

    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}

    analysis_id = state["analysis_id"]
    content_type = state["content_type"]

    # Issue #244: Check Handle Pattern availability (content_ref or raw_content)
    if not has_content_available(state):
        logger.warning(
            "agent_node_skipped_no_content",
            agent_type="code_quality_critic",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            has_content_ref=bool(state.get("content_ref")),
            has_raw_content=bool(state.get("raw_content")),
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="code_quality_critic",
            status=AgentStatus.SKIPPED,
            error_code=AGENT_NO_CONTENT,
            error_message="No content available for analysis",
        )
        return {"agent_findings": []}

    start_time = time.time()

    # Get Langfuse trace ID for correlation and update runtime metadata
    update_current_trace(
        metadata={
            "analysis_id": str(analysis_id),
            "content_type": content_type,
            "agent_name": "code_quality_critic",
        },
        tags=["parallel-execution"],
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",
    )
    trace_id = get_current_trace_id()

    logger.info(
        "agent_node_started",
        agent_type="code_quality_critic",
        analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
        trace_id=trace_id,
    )

    try:
        # Issue #244: Run agent with Handle Pattern - runner loads from artifact
        # get_fallback_content provides raw_content as fallback if artifact unavailable
        # Issue #574: Execute with tier-based resilience (bulkhead + circuit breaker)
        agent_meta = get_agent_metadata("code_quality_critic")
        tier = agent_meta.tier if agent_meta else 2  # Tier 2 VALIDATION

        result = await execute_with_resilience(
            agent_type="code_quality_critic",
            tier=tier,
            fn=lambda: run_code_quality_critic_with_session(
                content=get_fallback_content(state),
                content_type=content_type,
                analysis_id=str(analysis_id),
                state=state,
            ),
        )

        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)
        logger.info(
            "agent_node_complete",
            agent_type="code_quality_critic",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            duration_seconds=duration,
            trace_id=trace_id,
        )

        findings_value = result.get("findings")
        confidence_value = result.get("confidence_score")

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="code_quality_critic",
            status=AgentStatus.SUCCESS,
            findings=cast("dict[str, object]", findings_value)
            if isinstance(findings_value, dict)
            else None,
            confidence_score=float(confidence_value)
            if isinstance(confidence_value, (int, float))
            else None,
            processing_time_ms=processing_time_ms,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except (
        BulkheadFullError,
        BulkheadTimeoutError,
        GeneratorExit,
        TimeoutError,
        ValueError,
        Exception,
    ) as e:
        # Centralized error handling via shared helper (reduces return statements)
        duration = time.time() - start_time
        return await handle_agent_node_error(
            error=e,
            analysis_id=analysis_id,
            agent_type="code_quality_critic",
            duration=duration,
            trace_id=trace_id,
        )
