"""Branded/opaque types for domain IDs using NewType pattern.

2025 Best Practice: Use NewType for compile-time type safety without runtime overhead.
Prevents accidental mixing of different ID types (e.g., passing ArtifactID where AnalysisID expected).
"""

from typing import NewType
from uuid import UUID

# Core domain IDs
AnalysisID = NewType("AnalysisID", UUID)
ArtifactID = NewType("ArtifactID", UUID)
SessionID = NewType("SessionID", UUID)
ChunkID = NewType("ChunkID", UUID)

# String-based IDs
TraceID = NewType("TraceID", str)
TopicID = NewType("TopicID", str)
MessageID = NewType("MessageID", UUID)


# Factory functions for runtime validation
def create_analysis_id(value: UUID | str) -> AnalysisID:
    """Create typed AnalysisID with validation."""
    if isinstance(value, str):
        value = UUID(value)
    return AnalysisID(value)


def create_artifact_id(value: UUID | str) -> ArtifactID:
    """Create typed ArtifactID with validation."""
    if isinstance(value, str):
        value = UUID(value)
    return ArtifactID(value)


def create_session_id(value: UUID | str) -> SessionID:
    """Create typed SessionID with validation."""
    if isinstance(value, str):
        value = UUID(value)
    return SessionID(value)


def create_chunk_id(value: UUID | str) -> ChunkID:
    """Create typed ChunkID with validation."""
    if isinstance(value, str):
        value = UUID(value)
    return ChunkID(value)


def create_trace_id(value: str) -> TraceID:
    """Create typed TraceID."""
    return TraceID(value)


def create_topic_id(value: str) -> TopicID:
    """Create typed TopicID."""
    return TopicID(value)


def create_message_id(value: UUID | str) -> MessageID:
    """Create typed MessageID with validation."""
    if isinstance(value, str):
        value = UUID(value)
    return MessageID(value)


# Re-export all for easy imports
__all__ = [
    "AnalysisID",
    "ArtifactID",
    "ChunkID",
    "MessageID",
    "SessionID",
    "TopicID",
    "TraceID",
    "create_analysis_id",
    "create_artifact_id",
    "create_chunk_id",
    "create_message_id",
    "create_session_id",
    "create_topic_id",
    "create_trace_id",
]
