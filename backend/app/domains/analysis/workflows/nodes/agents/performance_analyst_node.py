"""Performance analyst agent node for LangGraph StateGraph.

Note: This node does NOT use @robust_traceable decorator because LangGraph
automatically traces all node executions. Adding @robust_traceable would
create duplicate spans in Langfuse. Runtime metadata is still updated
via update_current_trace().

Issue #244: Uses Handle Pattern - content loaded via content_ref (ArtifactStore)
with fallback to raw_content for backward compatibility.
"""

import time

from langfuse import observe

from app.core.logging import get_logger
from app.core.tracing import get_current_trace_id, update_current_trace
from app.domains.analysis.constants.error_codes import (
    AGENT_NO_CONTENT,
    AgentStatus,
)
from app.domains.analysis.workflows.agents.base import (
    handle_agent_node_error,
    record_agent_execution,
)
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.runners import (
    get_fallback_content,
    has_content_available,
    run_performance_analyst_with_session,
)

logger = get_logger(__name__)


@observe(as_type="agent", name="performance_analyst", capture_input=True, capture_output=True)
async def performance_analyst_node(state: AnalysisState) -> dict[str, object]:
    """Execute performance analysis.

    Executes performance analysis and returns findings.
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
            agent_type="performance_analyst",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            has_content_ref=bool(state.get("content_ref")),
            has_raw_content=bool(state.get("raw_content")),
        )
        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="performance_analyst",
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
            "agent_name": "performance_analyst",
        },
        tags=["parallel-execution"],
        session_id=f"analysis-{analysis_id}",
        user_id="anonymous",
    )
    trace_id = get_current_trace_id()

    logger.info(
        "agent_node_started",
        agent_type="performance_analyst",
        analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
        trace_id=trace_id,
    )

    try:
        # Issue #244: Run agent with Handle Pattern - runner loads from artifact
        # get_fallback_content provides raw_content as fallback if artifact unavailable
        result = await run_performance_analyst_with_session(
            content=get_fallback_content(state),
            content_type=content_type,
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            state=state,
        )

        duration = time.time() - start_time
        processing_time_ms = int(duration * 1000)
        logger.info(
            "agent_node_complete",
            agent_type="performance_analyst",
            analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
            duration_seconds=duration,
            trace_id=trace_id,
        )

        # Extract fields for database recording
        findings_raw = result.get("findings", {})
        confidence_raw = result.get("confidence_score")

        # Type-safe extraction with fallbacks (cast to satisfy type checker)
        findings_to_save = findings_raw if isinstance(findings_raw, dict) else {}
        confidence_to_save = float(confidence_raw) if confidence_raw is not None else None

        await record_agent_execution(
            analysis_id=analysis_id,
            agent_type="performance_analyst",
            status=AgentStatus.SUCCESS,
            findings=findings_to_save,
            confidence_score=confidence_to_save,
            processing_time_ms=processing_time_ms,
        )

        # Return findings as single-item list (aggregate will collect from all nodes)
        return {"agent_findings": [result]}
    except (GeneratorExit, TimeoutError, ValueError, Exception) as e:  # noqa: BLE001 - Intentional: catch all exceptions for graceful degradation
        # Centralized error handling via shared helper (reduces return statements)
        duration = time.time() - start_time
        return await handle_agent_node_error(
            error=e,
            analysis_id=analysis_id,
            agent_type="performance_analyst",
            duration=duration,
            trace_id=trace_id,
        )
