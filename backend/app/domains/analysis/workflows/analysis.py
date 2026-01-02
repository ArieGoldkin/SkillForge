"""LangGraph StateGraph workflow for content analysis.

This module implements the analysis workflow using LangGraph v1.0 StateGraph
with native parallel execution patterns (fan-out/fan-in).

Architecture:
    The workflow uses LangGraph's StateGraph API for better observability
    and native parallel execution. State is automatically checkpointed to
    PostgreSQL (or MemorySaver in development).

Workflow Flow:
    1. Extract Content: Uses JinaReader to extract content from URL
    2. Fan-out: Generate Embedding + Supervisor Routing (parallel)
    3. Fan-out: Execute Selected Agents (native LangGraph parallel)
    4. Fan-in: Aggregate Findings
    5. Return Complete State

Checkpointing:
    - Production: Uses PostgresSaver for persistent state across restarts
    - Development: Falls back to MemorySaver if database unavailable
    - Thread-based isolation: Each analysis_id uses a unique thread_id

SSE Events:
    The workflow emits Server-Sent Events (SSE) at each stage:
    - progress events: Stage status updates (running, complete)
    - error events: Failure notifications with error details
    - evaluation events: Agent quality evaluation results (NEW)
    - metrics events: Performance and quality metrics (NEW)

State Management:
    AnalysisState is a TypedDict that tracks workflow progress. Fields are
    populated incrementally as the workflow progresses through stages.

Example:
    ```python
    from app.domains.analysis.workflows.analysis import create_analysis_workflow

    workflow = create_analysis_workflow()
    result = await workflow.ainvoke(
        {
            "url": "https://example.com/article",
            "analysis_id": "unique-analysis-id",
        },
        config={"configurable": {"thread_id": "unique-analysis-id"}},
    )
    ```

"""

import traceback

from app.core.logging import get_logger
from app.domains.analysis.workflows.graph_builder import build_analysis_graph

logger = get_logger(__name__)


def create_analysis_workflow(checkpointer=None):
    """Create a new analysis workflow instance.

    This is a factory function. Each call creates a new workflow instance.
    For production, workflows should be created at application startup and
    reused (injected into components that need them).

    Args:
        checkpointer: Optional checkpointer instance (AsyncPostgresSaver, MemorySaver, etc.)
                     If not provided, falls back to get_checkpointer() in graph_builder.
                     Issue #602: Pass checkpointer from FastAPI app.state for production.

    Returns:
        Compiled StateGraph ready for execution

    """
    try:
        workflow = build_analysis_graph(checkpointer_override=checkpointer)
        logger.info(
            "workflow_graph_compiled",
            workflow_type="StateGraph",
            checkpointer_type=type(checkpointer).__name__ if checkpointer else "default",
        )
        return workflow
    except Exception as build_error:
        # Log graph build errors with full traceback for debugging
        logger.error(
            "workflow_graph_build_failed",
            error_type=type(build_error).__name__,
            error_message=str(build_error),
            exc_info=True,
            traceback=traceback.format_exc(),
        )
        # Re-raise to prevent application startup with broken workflow
        raise
