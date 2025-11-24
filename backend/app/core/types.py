"""Type aliases for common data structures used throughout the application.

This module provides type aliases for complex types to improve code readability
and maintainability. Using type aliases makes it easier to understand what
data structures are being used and allows for easier refactoring if types change.

Type Aliases:
    EmbeddingVector: List of floats representing an embedding vector
    AnalysisID: String identifier for an analysis
    ChannelName: String identifier for SSE event channels
    EventData: Dictionary containing event data for SSE broadcasting
    ExtractionResult: Dictionary containing extraction results from Jina Reader
"""

# Embedding types
EmbeddingVector = list[float]

# Identifier types
AnalysisID = str
ChannelName = str

# Event and message types
EventData = dict[str, object]

# Extraction result type
ExtractionResult = dict[str, str | int | dict[str, str]]
