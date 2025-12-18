"""LangSmith tracing utilities for consistent instrumentation.

This module provides the robust_traceable decorator for instrumenting
LangGraph nodes, agents, and workflows with proper metadata, tags, and
run types for observability in LangSmith.

The robust_traceable decorator follows LangSmith best practices by supporting:
- Static metadata at decorator level
- Runtime metadata updates via get_current_run_tree()
- Thread grouping for multi-turn conversations
- Consistent tag and metadata patterns

Note: Exception handling (including GeneratorExit) is done at the application
boundary (e.g., workflow_runner.py) where we have context (analysis_id, status updates).
This decorator focuses solely on tracing and lets exceptions propagate naturally.
"""

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Literal, ParamSpec, TypeVar

from langsmith import traceable

# Type variables for preserving function signatures in decorators
P = ParamSpec("P")  # Captures parameter types
R = TypeVar("R")  # Captures return type

# Run types supported by LangSmith traceable
RunType = Literal["tool", "chain", "llm", "retriever", "embedding", "prompt", "parser"]


def robust_traceable(
    name: str | None = None,
    run_type: RunType = "chain",
    tags: list[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Production-ready traceable wrapper for LangSmith instrumentation.

    This wrapper provides consistent tracing for LangGraph nodes, agents, and workflows.
    It follows LangSmith best practices by supporting static metadata, runtime updates,
    and thread grouping.

    Exception handling (including GeneratorExit) is done at the application boundary
    (e.g., workflow_runner.py) where we have context (analysis_id, status updates).
    This decorator focuses solely on tracing and lets exceptions propagate naturally.

    Args:
        name: Name for the trace (defaults to function name)
        run_type: Run type for LangSmith ("chain", "tool", etc.)
        tags: List of tags for filtering traces
        metadata: Additional metadata to attach to trace

    Returns:
        Decorated function with tracing enabled

    Example:
        @robust_traceable(name="my_node", tags=["workflow", "node"])
        async def my_node(state: AnalysisState) -> dict:
            # Implementation - exceptions propagate naturally
            return {"result": "data"}

    """

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        # Get function name safely for the trace name
        func_name = getattr(func, "__name__", "unknown")
        trace_name = name if name is not None else func_name

        # Use keyword-only arguments for traceable to match LangSmith API
        # Type ignore: LangSmith traceable has complex overloads that ty/mypy can't resolve
        traced_func = traceable(  # type: ignore[call-overload]
            run_type=run_type,
            name=trace_name,
            tags=tags or [],
            metadata=metadata or {},
        )
        # Apply tracing directly - no exception handling wrapper
        # Exceptions propagate naturally to application boundary handlers
        return traced_func(func)  # type: ignore[return-value]

    return decorator
