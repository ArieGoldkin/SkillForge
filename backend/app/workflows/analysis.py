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
    from app.workflows.analysis import analysis_workflow

    result = await analysis_workflow.ainvoke(
        {
            "url": "https://example.com/article",
            "analysis_id": "unique-analysis-id",
        },
        config={"configurable": {"thread_id": "unique-analysis-id"}},
    )
    ```

"""

import traceback
from contextlib import asynccontextmanager

from app.core.logging import get_logger
from app.workflows.graph_builder import build_analysis_graph

logger = get_logger(__name__)

# Build and compile the StateGraph workflow
try:
    analysis_workflow = build_analysis_graph()
    logger.info("workflow_graph_compiled", workflow_type="StateGraph")
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

# Wrap workflow execution to catch GeneratorExit at the top level
_original_ainvoke = analysis_workflow.ainvoke


@asynccontextmanager
async def _workflow_cleanup_context():
    """Context manager to catch GeneratorExit during workflow cleanup.

    This wraps the workflow execution to catch cleanup exceptions that occur
    after the workflow completes, during LangGraph's internal cleanup phase.

    GeneratorExit during cleanup is normal generator lifecycle behavior and
    is logged at DEBUG level (not ERROR) to avoid false error indicators.
    """
    try:
        yield
        logger.debug("workflow_cleanup_started")
    except GeneratorExit as gen_exit:
        # Catch GeneratorExit during cleanup - this is normal behavior
        # Log at DEBUG level since it's expected during generator cleanup
        logger.debug(
            "workflow_cleanup_generator_exit",
            error_type="GeneratorExit",
            error_message=str(gen_exit),
            exc_info=True,
            traceback=traceback.format_exc(),
            context="workflow_cleanup_context_manager",
            note=(
                "GeneratorExit caught in cleanup context manager. "
                "This is normal generator lifecycle behavior when LangGraph's pregel module "
                "closes async generators during cleanup after workflow execution completes. "
                "This is expected and does not indicate an error."
            ),
        )
        # Don't re-raise - cleanup exceptions shouldn't break the workflow
    except BaseException as cleanup_exc:
        # Catch other BaseExceptions during cleanup
        if isinstance(cleanup_exc, GeneratorExit):
            # Already handled above
            pass
        else:
            # Other BaseExceptions during cleanup are still errors
            logger.error(
                "workflow_cleanup_base_exception",
                error_type=type(cleanup_exc).__name__,
                error_message=str(cleanup_exc),
                exc_info=True,
                traceback=traceback.format_exc(),
                context="workflow_cleanup_context_manager",
            )
    finally:
        logger.debug("workflow_cleanup_complete")


async def _wrapped_ainvoke(*args, **kwargs):
    """Wrapper around workflow.ainvoke to catch and log GeneratorExit.

    This wrapper catches GeneratorExit at multiple levels:
    1. During workflow execution (treats as error, re-raises)
    2. During cleanup phase (suppresses, logs at DEBUG)

    Note: The @traceable decorator on run_workflow_task() creates the outer
    trace, and LangGraph's internal tracing automatically nests under it.
    The generator filtering Client is still configured globally to prevent
    GeneratorExit during serialization.
    """
    workflow_completed = False
    async with _workflow_cleanup_context():
        try:
            logger.debug(
                "workflow_ainvoke_called",
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )
            result = await _original_ainvoke(*args, **kwargs)
            workflow_completed = True  # Mark as completed successfully
            logger.debug(
                "workflow_ainvoke_success",
                result_type=type(result).__name__,
                result_keys=list(result.keys()) if isinstance(result, dict) else None,
            )
            return result
        except GeneratorExit as gen_exit:
            if workflow_completed:
                # GeneratorExit during cleanup after successful completion
                # This is normal generator lifecycle behavior - suppress it
                logger.debug(
                    "workflow_cleanup_generator_exit",
                    error_type="GeneratorExit",
                    error_message=str(gen_exit),
                    exc_info=True,
                    traceback=traceback.format_exc(),
                    context="workflow_ainvoke_wrapper_cleanup",
                    note=(
                        "GeneratorExit caught during cleanup after successful workflow completion. "
                        "This is normal generator lifecycle behavior when LangGraph's pregel "
                        "module closes async generators during cleanup. "
                        "Suppressing to prevent false errors."
                    ),
                )
                # Don't re-raise - this is expected cleanup behavior
            else:
                # GeneratorExit during execution - this is a real error
                logger.error(
                    "workflow_execution_generator_exit",
                    error_type="GeneratorExit",
                    error_message=str(gen_exit),
                    exc_info=True,
                    traceback=traceback.format_exc(),
                    context="workflow_ainvoke_wrapper_execution",
                    note=(
                        "GeneratorExit caught during workflow execution (before completion). "
                        "This indicates the workflow was interrupted or cancelled. "
                        "Check LangGraph streaming and timeout configuration."
                    ),
                )
                # Re-raise GeneratorExit (it's a BaseException, not Exception)
                raise
        except BaseException as base_exc:
            # Catch other BaseExceptions (SystemExit, KeyboardInterrupt) for logging
            if isinstance(base_exc, GeneratorExit):
                # Already handled above, but catch here as safety net
                raise
            logger.error(
                "workflow_ainvoke_base_exception",
                error_type=type(base_exc).__name__,
                error_message=str(base_exc),
                exc_info=True,
                traceback=traceback.format_exc(),
            )
            raise


# Replace ainvoke with wrapped version for debug logging
analysis_workflow.ainvoke = _wrapped_ainvoke  # type: ignore[method-assign]
