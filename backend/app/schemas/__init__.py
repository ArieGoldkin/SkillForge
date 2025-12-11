"""Pydantic request/response schemas.

This package contains Pydantic models for API request and response validation.
Schemas ensure type safety and automatic validation of incoming requests and
outgoing responses.

Modules:
    - analyze: Schemas for analysis endpoints (AnalyzeRequest, AnalyzeResponse)
    - library: Schemas for library search and filtering (LibraryFilters, LibrarySearchResult)
    - search: Schemas for search API (SearchRequest, SearchResponse, SearchMode, etc.)
    - context: Schemas for context engineering (ArtifactRef, ArtifactSection, etc.)
"""

from app.schemas.context import (
    ArtifactRef,
    ArtifactSection,
    CodeBlockInfo,
    ContentSections,
    HeadingInfo,
    LoadArtifactRequest,
    LoadArtifactResponse,
)
from app.schemas.search import (
    ChunkMetadata,
    DateRange,
    ReRankConfig,
    SearchFilters,
    SearchMode,
    SearchRequest,
    SearchResponse,
    SearchResult,
)

__all__ = [
    "ArtifactRef",
    "ArtifactSection",
    "ChunkMetadata",
    "CodeBlockInfo",
    "ContentSections",
    "DateRange",
    "HeadingInfo",
    "LoadArtifactRequest",
    "LoadArtifactResponse",
    "ReRankConfig",
    "SearchFilters",
    "SearchMode",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
]
