"""Type stubs for langgraph.graph module."""

from collections.abc import Callable, Mapping
from typing import Any, Generic, TypeVar

from langgraph.checkpoint import BaseCheckpointSaver

StateType = TypeVar("StateType", bound=Mapping[str, Any])

class StateGraph(Generic[StateType]):
    """State machine graph for workflows."""
    
    def __init__(
        self,
        state_schema: type[StateType],
        config_schema: type | None = None,
    ) -> None: ...
    
    def add_node(
        self,
        node: str,
        action: Callable[..., Any],
        **kwargs: Any,
    ) -> "StateGraph[StateType]": ...
    
    def add_edge(
        self,
        source: str,
        dest: str,
    ) -> "StateGraph[StateType]": ...
    
    def add_conditional_edges(
        self,
        source: str,
        path: Callable[..., str | list[str]],
        path_map: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> "StateGraph[StateType]": ...
    
    def set_entry_point(self, node: str) -> "StateGraph[StateType]": ...
    
    def set_finish_point(self, node: str) -> "StateGraph[StateType]": ...
    
    def compile(
        self,
        checkpointer: BaseCheckpointSaver | None = None,
        **kwargs: Any,
    ) -> "CompiledGraph[StateType]": ...

class CompiledGraph(Generic[StateType]):
    """Compiled workflow graph."""
    
    async def ainvoke(
        self,
        input: StateType | dict[str, Any],
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> StateType: ...
    
    async def astream(
        self,
        input: StateType | dict[str, Any],
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any: ...
    
    async def aget_state(
        self,
        config: dict[str, Any],
    ) -> Any: ...

START: str
END: str


