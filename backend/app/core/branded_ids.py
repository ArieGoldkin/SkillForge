"""Branded/opaque types for domain IDs using Annotated pattern.

2025 Best Practice: Use Annotated[T, label] for documented type aliases.
- Zero runtime overhead (same as base type)
- No conversion needed at boundaries
- Self-documenting code
- Pydantic compatible

Note: This replaces the NewType pattern which required conversion functions.
Annotated types are the same as their base type at both compile and runtime,
but carry metadata for documentation purposes.
"""

from typing import Annotated
from uuid import UUID

# Core domain IDs (UUID-based)
# These are type aliases with documentation metadata
AnalysisID = Annotated[UUID, "analysis_id"]
ArtifactID = Annotated[UUID, "artifact_id"]
SessionID = Annotated[UUID, "session_id"]
ChunkID = Annotated[UUID, "chunk_id"]
MessageID = Annotated[UUID, "message_id"]

# String-based IDs
TraceID = Annotated[str, "trace_id"]
TopicID = Annotated[str, "topic_id"]


# Re-export all for easy imports
__all__ = [
    "AnalysisID",
    "ArtifactID",
    "ChunkID",
    "MessageID",
    "SessionID",
    "TopicID",
    "TraceID",
]
