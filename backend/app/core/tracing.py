"""Langfuse tracing utilities for consistent instrumentation.

This module provides the robust_traceable decorator for instrumenting
LangGraph nodes, agents, and workflows with proper metadata, tags, and
span types for observability in Langfuse.

The robust_traceable decorator follows Langfuse best practices by supporting:
- Static metadata at decorator level
- Runtime metadata updates via langfuse.update_current_trace()
- Thread grouping for multi-turn conversations
- Consistent tag and metadata patterns

Note: Exception handling (including GeneratorExit) is done at the application
boundary (e.g., workflow_runner.py) where we have context (analysis_id, status updates).
This decorator focuses solely on tracing and lets exceptions propagate naturally.
"""

from collections.abc import Awaitable, Callable
from typing import Any, Literal, ParamSpec, TypeVar

# Type variables for preserving function signatures in decorators
P = ParamSpec("P")  # Captures parameter types
R = TypeVar("R")  # Captures return type

# Span types supported by Langfuse @observe decorator
# Maps from Langfuse run_type to Langfuse as_type
# Valid types: generation, embedding, span, agent, tool
# Issue #384: Added "agent" and "tool" for Agent Graph Visualization
SpanType = Literal["span", "generation", "agent", "tool"]

# Mapping from Langfuse run_type to Langfuse as_type
# Issue #384: Updated to support agent graph visualization in Langfuse
RUN_TYPE_TO_SPAN_TYPE: dict[str, SpanType] = {
    "chain": "span",  # Workflow steps, chains
    "tool": "tool",  # Tool invocations - enables tool nesting in graphs
    "llm": "generation",  # LLM calls
    "retriever": "span",  # RAG retrieval
    "embedding": "span",  # Embedding calls
    "prompt": "span",  # Prompt templates
    "parser": "span",  # Output parsers
    "agent": "agent",  # Agent nodes - enables agent graph visualization
}


def robust_traceable(
    name: str | None = None,
    run_type: str = "chain",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Production-ready traceable wrapper for Langfuse instrumentation.

    This wrapper provides consistent tracing for LangGraph nodes, agents, and workflows.
    It follows Langfuse best practices by supporting static metadata, runtime updates,
    and thread grouping.

    Exception handling (including GeneratorExit) is done at the application boundary
    (e.g., workflow_runner.py) where we have context (analysis_id, status updates).
    This decorator focuses solely on tracing and lets exceptions propagate naturally.

    Args:
        name: Name for the trace (defaults to function name)
        run_type: Run type for backwards compatibility with Langfuse patterns
            ("chain", "tool", "llm", etc.) - mapped to Langfuse span types
        tags: List of tags for filtering traces (applied via update_current_trace)
        metadata: Additional metadata to attach to trace (applied via update_current_trace)

    Returns:
        Decorated function with tracing enabled

    Example:
        @robust_traceable(name="my_node", tags=["workflow", "node"])
        async def my_node(state: AnalysisState) -> dict:
            # Implementation - exceptions propagate naturally
            return {"result": "data"}

    """
    # Convert run_type to Langfuse span type
    span_type: SpanType = RUN_TYPE_TO_SPAN_TYPE.get(run_type, "span")

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        # Get function name safely for the trace name
        func_name = getattr(func, "__name__", "unknown")
        trace_name = name if name is not None else func_name

        try:
            from langfuse import get_client, observe

            # Apply Langfuse @observe decorator
            # Note: tags and metadata are applied at runtime via update_current_trace
            observed_func = observe(
                name=trace_name,
                as_type=span_type,
            )(func)

            # If we have tags or metadata, wrap to apply them at runtime
            if tags or metadata:
                import functools

                @functools.wraps(func)
                async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                    # Apply tags and metadata at runtime
                    try:
                        langfuse = get_client()
                        if tags or metadata:
                            update_kwargs: dict[str, Any] = {}
                            if tags:
                                update_kwargs["tags"] = tags
                            if metadata:
                                update_kwargs["metadata"] = metadata
                            if update_kwargs:
                                langfuse.update_current_trace(**update_kwargs)
                    except Exception:  # noqa: BLE001, S110 - Silent fallback when Langfuse unavailable
                        # Langfuse context not available - continue without
                        pass

                    return await observed_func(*args, **kwargs)

                return wrapper  # type: ignore[return-value]

            return observed_func  # type: ignore[return-value]

        except ImportError:
            # Langfuse not installed - return function unchanged
            return func

    return decorator


def update_current_trace(
    *,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    user_id: str | None = None,
    session_id: str | None = None,
) -> None:
    """Update the current Langfuse trace with additional context.

    This is a helper function for updating trace metadata at runtime,
    replacing the Langfuse pattern of `get_current_run_tree().metadata["key"] = value`.

    Args:
        tags: List of tags to add to the trace
        metadata: Dictionary of metadata to add to the trace
        user_id: User identifier for the trace
        session_id: Session identifier for grouping traces

    Example:
        # Instead of Langfuse pattern:
        # run_tree = get_current_run_tree()
        # run_tree.metadata["analysis_id"] = str(analysis_id)

        # Use Langfuse:
        update_current_trace(metadata={"analysis_id": str(analysis_id)})

    """
    try:
        from langfuse import get_client

        langfuse = get_client()

        update_kwargs: dict[str, Any] = {}
        if tags:
            update_kwargs["tags"] = tags
        if metadata:
            update_kwargs["metadata"] = metadata
        if user_id:
            update_kwargs["user_id"] = user_id
        if session_id:
            update_kwargs["session_id"] = session_id

        if update_kwargs:
            langfuse.update_current_trace(**update_kwargs)

    except ImportError:
        # Langfuse not installed - silently skip
        pass
    except Exception:  # noqa: BLE001, S110 - Silent fallback for trace context errors
        # Not in trace context or other error - silently skip
        pass


def get_current_trace_id() -> str | None:
    """Get the current Langfuse trace ID.

    This replaces the Langfuse pattern of `str(run_tree.trace_id)`.

    Returns:
        Current trace ID as string, or None if not in trace context

    """
    try:
        from langfuse import get_client

        langfuse = get_client()
        trace_id = langfuse.get_current_trace_id()
        return str(trace_id) if trace_id else None

    except ImportError:
        return None
    except Exception:  # noqa: BLE001
        return None
