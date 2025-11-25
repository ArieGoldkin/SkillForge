"""LangSmith tracing utilities for consistent instrumentation.

This module provides helper functions for instrumenting LangGraph nodes,
agents, and guardrails with proper metadata, tags, and run types for
observability in LangSmith.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from langsmith import traceable
from langsmith.run_trees import RunTree

from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def trace_node(
    name: str | None = None,
    run_type: str = "tool",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """Trace LangGraph node functions.

    Args:
        name: Name for the trace (defaults to function name)
        run_type: Run type for LangSmith ("tool", "chain", etc.)
        tags: List of tags for filtering traces
        metadata: Additional metadata to attach to trace

    Returns:
        Decorated function with tracing enabled

    Example:
        @trace_node(name="extract_content", run_type="tool", tags=["workflow", "node"])
        async def extract_content(url: str) -> dict:
            ...

    """
    default_tags = ["workflow", "node"]
    combined_tags = (tags or []) + default_tags

    def decorator(func: F) -> F:
        # Note: Any is necessary here for generic decorator factory pattern.
        # Type erasure is required to support functions with varying signatures.
        # The decorator must accept any function signature and preserve it.
        traced_func = traceable(  # type: ignore[call-overload]
            run_type=run_type,  # type: ignore[arg-type]
            name=name or func.__name__,
            tags=combined_tags,
            metadata=metadata or {},
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return await traced_func(func)(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def trace_agent(
    name: str | None = None,
    run_type: str = "chain",
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Callable[[F], F]:
    """Trace agent execution functions.

    Args:
        name: Name for the trace (defaults to function name)
        run_type: Run type for LangSmith ("chain" for agents)
        tags: List of tags for filtering traces
        metadata: Additional metadata to attach to trace

    Returns:
        Decorated function with tracing enabled

    Example:
        @trace_agent(name="tech_comparator", tags=["agent", "tech_comparator"])
        async def run_tech_comparator(...) -> dict:
            ...

    """
    default_tags = ["agent"]
    combined_tags = (tags or []) + default_tags

    def decorator(func: F) -> F:
        # Note: Any is necessary here for generic decorator factory pattern.
        # Type erasure is required to support functions with varying signatures.
        # The decorator must accept any function signature and preserve it.
        traced_func = traceable(  # type: ignore[call-overload]
            run_type=run_type,  # type: ignore[arg-type]
            name=name or func.__name__,
            tags=combined_tags,
            metadata=metadata or {},
        )

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            return await traced_func(func)(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


async def trace_guardrail(
    name: str,
    schema_name: str,
    inputs: dict[str, Any],
    validation_func: Callable[[dict[str, Any]], Any],
    parent_run: RunTree | None = None,
) -> Any:
    """Trace Pydantic validation as a guardrail step.

    Args:
        name: Name for the validation trace
        schema_name: Name of the Pydantic schema being validated
        inputs: Input data to validate
        validation_func: Function that performs validation
        parent_run: Optional parent RunTree for hierarchy

    Returns:
        Validated result from validation_func

    Raises:
        ValidationError: If validation fails (traced in LangSmith)

    Example:
        result = await trace_guardrail(
            name="validate_tech_comparison",
            schema_name="TechComparison",
            inputs={"primary_tech": "React", ...},
            validation_func=lambda d: TechComparison(**d),
        )

    """
    tags = ["guardrail", "validation"]
    metadata = {"schema": schema_name}

    # Create guardrail trace
    guardrail_run = RunTree(
        name=name,
        run_type="tool",
        inputs=inputs,
        tags=tags,
        parent_run_id=parent_run.id if parent_run else None,
    )
    guardrail_run.post()

    try:
        # Perform validation
        result = validation_func(inputs)

        # Success - end trace with outputs
        guardrail_run.end(
            outputs={"validated": True, "schema": schema_name, **metadata},
        )
        guardrail_run.patch()
        return result
    except Exception as e:
        # Validation failed - end trace with error
        error_msg = str(e)
        guardrail_run.end(
            error=error_msg,
            outputs={"validated": False, "error": error_msg},
        )
        guardrail_run.patch()

        logger.warning(
            "guardrail_validation_failed",
            schema_name=schema_name,
            error=error_msg,
        )

        raise
