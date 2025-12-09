"""Pydantic request/response schemas.

This package contains Pydantic models for API request and response validation.
Schemas ensure type safety and automatic validation of incoming requests and
outgoing responses.

Modules:
    - analyze: Schemas for analysis endpoints (AnalyzeRequest, AnalyzeResponse)
    - search: Schemas for search endpoints (SearchRequest, SearchResponse)
"""

# Analysis schemas
from .analyze import (
    AnalyzeCreateResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
)

# Search schemas
from .search import (
    ChunkMetadata,
    DateRange,
    SearchFilters,
    SearchMode,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

__all__ = [
    "AnalyzeCreateResponse",
    "AnalyzeRequest",
    "AnalyzeResponse",
    "ChunkMetadata",
    "DateRange",
    "ErrorResponse",
    "SearchFilters",
    "SearchMode",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
]
