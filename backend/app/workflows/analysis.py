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

    Regular exceptions (Exception) are NOT caught here - they propagate to
    the wrapper's exception handlers for proper error handling.
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
    except Exception:
        # Regular exceptions (JinaReaderError, ValueError, etc.) should propagate
        # Don't catch them here - let them propagate to wrapper's exception handlers
        raise
    except BaseException as cleanup_exc:
        # Catch other BaseExceptions during cleanup (SystemExit, KeyboardInterrupt)
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
            # Re-raise BaseExceptions (except GeneratorExit) - they're critical
            raise
    finally:
        logger.debug("workflow_cleanup_complete")


async def _wrapped_ainvoke(*args, **kwargs):
    """Wrapper around workflow.ainvoke to catch and log GeneratorExit.

    This wrapper catches GeneratorExit at multiple levels:
    1. During workflow execution (treats as error, re-raises)
    2. During cleanup phase (suppresses, logs at DEBUG, returns result)

    Note: The @traceable decorator on run_workflow_task() creates the outer
    trace, and LangGraph's internal tracing automatically nests under it.
    The generator filtering Client is still configured globally to prevent
    GeneratorExit during serialization.
    """
    workflow_completed = False
    result = None
    try:
        async with _workflow_cleanup_context():
            logger.debug(
                "workflow_ainvoke_called",
                args_count=len(args),
                kwargs_keys=list(kwargs.keys()),
            )
            result = await _original_ainvoke(*args, **kwargs)
            workflow_completed = True  # Mark as completed successfully

            # Validate result - LangGraph should always return a dict (state)
            if result is None:
                logger.error(
                    "workflow_returned_none",
                    note=(
                        "Workflow ainvoke returned None. This should never happen - "
                        "LangGraph workflows should always return the state dict. "
                        "This may indicate an internal LangGraph error or exception handling issue."
                    ),
                )
                raise RuntimeError(
                    "Workflow returned None - this indicates an internal error. "
                    "Check workflow node implementations and exception handling."
                )

            logger.debug(
                "workflow_ainvoke_success",
                result_type=type(result).__name__,
                result_keys=list(result.keys()) if isinstance(result, dict) else None,
            )
            # Return result immediately after successful completion
            # This ensures result is returned even if GeneratorExit occurs during cleanup
            return result
    except Exception as exc:
        # Catch regular exceptions (not BaseException) for logging
        # These are workflow execution errors (e.g., JinaReaderError, ValueError)
        # Log and re-raise to allow calling code to handle them
        logger.error(
            "workflow_execution_exception",
            error_type=type(exc).__name__,
            error_message=str(exc),
            exc_info=True,
            traceback=traceback.format_exc(),
            context="workflow_ainvoke_wrapper",
            note=(
                "Regular exception caught during workflow execution. "
                "This is a workflow error (e.g., extraction failure, agent error) "
                "and should be handled by the calling code."
            ),
        )
        # Re-raise to allow calling code to handle the error
        raise
    except GeneratorExit as gen_exit:
        if workflow_completed and result is not None:
            # GeneratorExit during cleanup after successful completion
            # This is normal generator lifecycle behavior - suppress it and return result
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
            # Return the result - workflow completed successfully
            return result
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
    except RuntimeError as runtime_err:
        # Python converts GeneratorExit in async functions to RuntimeError
        # Check if this is a converted GeneratorExit
        if "coroutine ignored GeneratorExit" in str(runtime_err):
            if workflow_completed and result is not None:
                # GeneratorExit during cleanup (converted to RuntimeError) - normal behavior
                logger.debug(
                    "workflow_cleanup_generator_exit",
                    error_type="RuntimeError",
                    error_message=str(runtime_err),
                    exc_info=True,
                    traceback=traceback.format_exc(),
                    context="workflow_ainvoke_wrapper_cleanup",
                    note=(
                        "GeneratorExit caught during cleanup (converted to RuntimeError) after successful workflow completion. "
                        "This is normal generator lifecycle behavior when LangGraph's pregel "
                        "module closes async generators during cleanup. "
                        "Suppressing to prevent false errors."
                    ),
                )
                # Return the result - workflow completed successfully
                return result
            else:
                # GeneratorExit during execution (converted to RuntimeError) - real error
                logger.error(
                    "workflow_execution_generator_exit",
                    error_type="RuntimeError",
                    error_message=str(runtime_err),
                    exc_info=True,
                    traceback=traceback.format_exc(),
                    context="workflow_ainvoke_wrapper_execution",
                    note=(
                        "GeneratorExit caught during workflow execution (converted to RuntimeError, before completion). "
                        "This indicates the workflow was interrupted or cancelled. "
                        "Check LangGraph streaming and timeout configuration."
                    ),
                )
                # Re-raise RuntimeError
                raise
        else:
            # Not a GeneratorExit - re-raise as normal RuntimeError
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
