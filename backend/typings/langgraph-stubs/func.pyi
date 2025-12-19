"""Type stubs for langgraph.func module."""

from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def entrypoint(
    checkpointer: Any = None,
    **kwargs: Any,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for workflow entrypoints."""
    ...

def task(
    func: Callable[P, R] | None = None,
    **kwargs: Any,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator for workflow tasks."""
    ...







