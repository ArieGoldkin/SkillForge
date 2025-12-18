"""Type stubs for langgraph.checkpoint.postgres module."""

from typing import Any

from langgraph.checkpoint import BaseCheckpointSaver

class PostgresSaver(BaseCheckpointSaver):
    """PostgreSQL checkpoint saver."""
    
    def __init__(self, conn_string: str | None = None, **kwargs: Any) -> None: ...
    
    @classmethod
    def from_conn_string(cls, conn_string: str) -> "PostgresSaver": ...
    
    async def setup(self) -> None: ...


