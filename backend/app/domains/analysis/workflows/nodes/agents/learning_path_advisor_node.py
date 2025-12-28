"""Learning path advisor agent node for LangGraph StateGraph.

Note: This node does NOT use @robust_traceable decorator because LangGraph
automatically traces all node executions. Adding @robust_traceable would
create duplicate spans in Langfuse. Runtime metadata is still updated
via update_current_trace().

Issue #244: Uses Handle Pattern - content loaded via content_ref (ArtifactStore)
with fallback to raw_content for backward compatibility.
Issue #500: Tier 3 Research agent with memory integration for personalized learning paths.
"""

import time
from typing import cast

from langfuse import get_client, observe

from app.core.bulkhead import BulkheadFullError, BulkheadTimeoutError
from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.core.tracing import get_current_trace_id, update_current_trace
from app.domains.analysis.agents.registry import get_agent_metadata
from app.domains.analysis.constants.error_codes import (
    AGENT_BULKHEAD_REJECTED,
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
    run_learning_path_advisor_with_session,
)

logger = get_logger(__name__)


@observe(
    as_type="agent",
    name="learning_path_advisor",
    capture_input=True,
    capture_output=True,
)
async def learning_path_advisor_node(state: AnalysisState) -> dict[str, object]:  # noqa: PLR0915 - Agent node requires comprehensive error handling
    """Learning path advisor agent node.

    Executes personalized learning path creation using memory (prior_memory) and
    returns findings. This is a Tier 3 Research agent that adapts recommendations
    based on user's skill level and learning history.

    Each agent node manages its own database session for parallel execution.

    Issue #244: Uses Handle Pattern for content loading:
    1. Checks content_ref (preferred) or raw_content (fallback) availability
    2. Runner loads optimized content section via ArtifactStore
    3. Falls back to raw_content if artifact loading fails

    Issue #500: Memory-enabled agent receives prior_memory from agent_router
    containing user's learning history for personalization.

    Note: LangGraph automatically traces this node. We update runtime metadata
    via update_current_trace() but don't add a separate tracing decorator.

    Args:
        state: Current workflow state with content_ref or raw_content and prior_memory

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
            agent_type="learning_path_advisor",
            analysis_id=str(analysis_id),
            has_content_ref=bool(state.get("content_ref")),
            has_raw_content=bool(state.get("raw_content")),
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="learning_path_advisor",
            status=AgentStatus.SKIPPED,
            error_code=AGENT_NO_CONTENT,
            error_message="No content available for analysis",
        )
        return {"agent_findings": []}

    start_time = time.time()

    # Update Langfuse agent-level metadata
    langfuse = get_client()
    if langfuse:
        # Log memory usage for observability
        has_prior_memory = bool(state.get("prior_memory"))
        langfuse.update_current_span(
            metadata={
                "agent_type": "learning_path_advisor",
                "analysis_id": str(analysis_id),
                "tier": 3,
                "has_memory": has_prior_memory,
                "skill_level": state.get("skill_level", "intermediate"),
            }
        )

    # Get Langfuse trace ID for correlation and update runtime metadata
    update_current_trace(
        metadata={
            "analysis_id": str(analysis_id),
            "content_type": content_type,
            "agent_name": "learning_path_advisor",
            "tier": 3,
            "requires_memory": True,
        },
        tags=["parallel-execution", "tier-3-research", "memory-enabled"],
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",
    )
    trace_id = get_current_trace_id()

    logger.info(
        "agent_node_started",
        agent_type="learning_path_advisor",
        analysis_id=str(analysis_id),
        trace_id=trace_id,
        tier=3,
        has_prior_memory=bool(state.get("prior_memory")),
    )

    try:
        # Issue #244: Run agent with Handle Pattern - runner loads from artifact
        # Issue #500: State contains prior_memory injected by agent_router
        # get_fallback_content provides raw_content as fallback if artifact unavailable

        # Issue #574: Execute with tier-based resilience (bulkhead + circuit breaker)
        agent_meta = get_agent_metadata("learning_path_advisor")
        tier = agent_meta.tier if agent_meta else 3  # Tier 3 RESEARCH

        result = await execute_with_resilience(
            agent_type="learning_path_advisor",
            tier=tier,
            fn=lambda: run_learning_path_advisor_with_session(
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
            agent_type="learning_path_advisor",
            analysis_id=str(analysis_id),
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
            agent_type="learning_path_advisor",
            status=AgentStatus.SUCCESS,
            findings=findings_to_save,
            confidence_score=confidence_to_save,
            processing_time_ms=processing_time_ms,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except (BulkheadFullError, BulkheadTimeoutError) as e:
        # Issue #588: Bulkhead rejection - graceful degradation
        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)
        logger.warning(
            "agent_bulkhead_rejected",
            agent_type="learning_path_advisor",
            analysis_id=str(analysis_id),
            error_type=type(e).__name__,
            error=str(e),
            duration_seconds=duration,
            trace_id=trace_id,
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="learning_path_advisor",
            status=AgentStatus.FAILED,
            error_code=AGENT_BULKHEAD_REJECTED,
            error_message=str(e)[:500],
            processing_time_ms=processing_time_ms,
        )
        return {"agent_findings": []}
    except GeneratorExit:
        # GeneratorExit during execution (cancellation/timeout) - return empty for
        # graceful degradation. Cleanup GeneratorExit is handled by robust_traceable wrapper
        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)
        logger.warning(
            "agent_node_cancelled",
            agent_type="learning_path_advisor",
            analysis_id=str(analysis_id),
            exception_type="GeneratorExit",
            duration_seconds=duration,
            step_timeout=STEP_TIMEOUT,
            trace_id=trace_id,
            handled_gracefully=True,
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="learning_path_advisor",
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
            "learning_path_advisor",
            "failed",
            error=str(e),
            error_code="LEARNING_PATH_ADVISOR_FAILED",
            processing_time_ms=processing_time_ms,
        )

        # Record error to database
        from app.domains.analysis.services.persistence.error_recorder import (
            error_recorder,
        )

        await error_recorder.record(
            analysis_id=analysis_id,
            error_code="LEARNING_PATH_ADVISOR_FAILED",
            error_message=str(e),
            stage="learning_path_advisor",
        )

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="learning_path_advisor",
            status=AgentStatus.FAILED,
            error_code=AGENT_TIMEOUT,
            error_message=str(e)[:2000],
            processing_time_ms=processing_time_ms,
        )

        logger.error(
            "agent_node_failed",
            agent_type="learning_path_advisor",
            analysis_id=str(analysis_id),
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
            "learning_path_advisor",
            "failed",
            error=str(e),
            error_code="LEARNING_PATH_ADVISOR_FAILED",
            processing_time_ms=processing_time_ms,
        )

        # Record error to database
        from app.domains.analysis.services.persistence.error_recorder import (
            error_recorder,
        )

        await error_recorder.record(
            analysis_id=analysis_id,
            error_code="LEARNING_PATH_ADVISOR_FAILED",
            error_message=str(e),
            stage="learning_path_advisor",
        )

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="learning_path_advisor",
            status=AgentStatus.FAILED,
            error_code=AGENT_LLM_ERROR,
            error_message=str(e)[:2000],
            processing_time_ms=processing_time_ms,
        )

        logger.error(
            "agent_node_failed",
            agent_type="learning_path_advisor",
            analysis_id=str(analysis_id),
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
