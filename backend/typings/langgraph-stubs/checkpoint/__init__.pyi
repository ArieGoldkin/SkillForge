"""Type stubs for langgraph.checkpoint module."""

from typing import Any

class BaseCheckpointSaver:
    """Base class for checkpoint savers."""

    ...

class MemorySaver(BaseCheckpointSaver):
    """In-memory checkpoint saver."""
    def __init__(self) -> None: ...
