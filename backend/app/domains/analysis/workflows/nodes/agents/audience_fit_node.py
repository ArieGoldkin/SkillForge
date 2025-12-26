"""Audience fit agent node for LangGraph StateGraph.

Note: This node does NOT use @robust_traceable decorator because LangGraph
automatically traces all node executions. Adding @robust_traceable would
create duplicate spans in Langfuse. Runtime metadata is still updated
via update_current_trace().

Issue #244: Uses Handle Pattern - content loaded via content_ref (ArtifactStore)
with fallback to raw_content for backward compatibility.
"""

import time
from typing import cast

from langfuse import get_client, observe

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.core.tracing import get_current_trace_id, update_current_trace
from app.domains.analysis.agents.registry import get_agent_metadata
from app.domains.analysis.constants.error_codes import (
    AGENT_CANCELLED,
    AGENT_LLM_ERROR,
    AGENT_NO_CONTENT,
    AGENT_TIMEOUT,
    AgentStatus,
)
from app.domains.analysis.workflows.agents.base import (
    emit_agent_progress,
    record_agent_execution,
)
from app.domains.analysis.workflows.agents.resilience_wrapper import (
    execute_with_resilience,
)
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.runners import (
    get_fallback_content,
    has_content_available,
    run_audience_fit_with_session,
)

logger = get_logger(__name__)


@observe(as_type="agent", name="audience_fit", capture_input=True, capture_output=True)
async def audience_fit_node(state: AnalysisState) -> dict[str, object]:
    """Audience fit agent node.

    Executes audience analysis and returns findings.
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
            agent_type="audience_fit",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            has_content_ref=bool(state.get("content_ref")),
            has_raw_content=bool(state.get("raw_content")),
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="audience_fit",
            status=AgentStatus.SKIPPED,
            error_code=AGENT_NO_CONTENT,
            error_message="No content available for analysis",
        )
        return {"agent_findings": []}

    start_time = time.time()

    # Update Langfuse agent-level metadata
    langfuse = get_client()
    if langfuse:
        langfuse.update_current_span(
            metadata={
                "agent_type": "audience_fit",
                "analysis_id": str(analysis_id),
            }
        )

    # Get Langfuse trace ID for correlation and update runtime metadata
    update_current_trace(
        metadata={
            "analysis_id": str(analysis_id),
            "content_type": content_type,
            "agent_name": "audience_fit",
        },
        tags=["parallel-execution"],
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",
    )
    trace_id = get_current_trace_id()

    logger.info(
        "agent_node_started",
        agent_type="audience_fit",
        analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
        trace_id=trace_id,
    )

    try:
        # Issue #244: Run agent with Handle Pattern - runner loads from artifact
        # get_fallback_content provides raw_content as fallback if artifact unavailable
        # Issue #574: Execute with tier-based resilience (bulkhead + circuit breaker)
        agent_meta = get_agent_metadata("audience_fit")
        tier = agent_meta.tier if agent_meta else 1  # Default to Tier 1 if not found

        result = await execute_with_resilience(
            agent_type="audience_fit",
            tier=tier,
            fn=lambda: run_audience_fit_with_session(
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
            agent_type="audience_fit",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            duration_seconds=duration,
            trace_id=trace_id,
        )

        # Extract fields for database recording
        findings_raw = result.get("findings", {})
        confidence_raw = result.get("confidence_score")

        # Type-safe extraction with fallbacks (cast to satisfy type checker)
        findings_to_save: dict[str, object] | None = (
            cast("dict[str, object]", findings_raw) if isinstance(findings_raw, dict) else None
        )
        confidence_to_save: float | None = (
            float(confidence_raw) if isinstance(confidence_raw, (int, float)) else None
        )

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="audience_fit",
            status=AgentStatus.SUCCESS,
            findings=findings_to_save,
            confidence_score=confidence_to_save,
            processing_time_ms=processing_time_ms,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except GeneratorExit:
        # GeneratorExit during execution (cancellation/timeout) - return empty for
        # graceful degradation. Cleanup GeneratorExit is handled by robust_traceable wrapper
        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)
        logger.warning(
            "agent_node_cancelled",
            agent_type="audience_fit",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="audience_fit",
            status=AgentStatus.FAILED,
            error_code=AGENT_CANCELLED,
            error_message="Agent execution cancelled",
            processing_time_ms=processing_time_ms,
        )
        # Return empty findings on cancellation (allows other agents to continue)
        return {"agent_findings": []}
    except TimeoutError as e:
        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)

        # Emit failed event using existing emit_agent_progress helper
        await emit_agent_progress(
            analysis_id,
            "audience_fit",
            "failed",
            error=str(e),
            error_code="AUDIENCE_FIT_FAILED",
            processing_time_ms=processing_time_ms,
        )

        # Record error to database
        from app.domains.analysis.services.persistence.error_recorder import error_recorder

        await error_recorder.record(
            analysis_id=analysis_id,
            error_code="AUDIENCE_FIT_FAILED",
            error_message=str(e),
            stage="audience_fit",
        )

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="audience_fit",
            status=AgentStatus.FAILED,
            error_code=AGENT_TIMEOUT,
            error_message=str(e)[:2000],
            processing_time_ms=processing_time_ms,
        )

        logger.error(
            "agent_node_failed",
            agent_type="audience_fit",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,  # Returns empty findings, doesn't break workflow
            exc_info=True,
        )
        # Return empty findings on error (allows other agents to continue)
        return {"agent_findings": []}
    except Exception as e:
        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)

        # Emit failed event using existing emit_agent_progress helper
        await emit_agent_progress(
            analysis_id,
            "audience_fit",
            "failed",
            error=str(e),
            error_code="AUDIENCE_FIT_FAILED",
            processing_time_ms=processing_time_ms,
        )

        # Record error to database
        from app.domains.analysis.services.persistence.error_recorder import error_recorder

        await error_recorder.record(
            analysis_id=analysis_id,
            error_code="AUDIENCE_FIT_FAILED",
            error_message=str(e),
            stage="audience_fit",
        )

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="audience_fit",
            status=AgentStatus.FAILED,
            error_code=AGENT_LLM_ERROR,
            error_message=str(e)[:2000],
            processing_time_ms=processing_time_ms,
        )

        logger.error(
            "agent_node_failed",
            agent_type="audience_fit",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,  # Returns empty findings, doesn't break workflow
            exc_info=True,
        )
        # Return empty findings on error (allows other agents to continue)
        return {"agent_findings": []}
