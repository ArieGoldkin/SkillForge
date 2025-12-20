"""Pydantic schemas for analysis API endpoints."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    """Request schema for creating a new analysis.

    Attributes:
        url: The URL to analyze (must be a valid HTTP/HTTPS URL)
        analysis_id: Optional analysis ID (auto-generated if not provided)
        skill_level: User's skill level for personalized analysis output

    Example:
        ```python
        request = AnalyzeRequest(url="https://example.com/article", skill_level="intermediate")
        ```

    """

    url: HttpUrl = Field(..., description="URL to analyze (must be HTTP/HTTPS)")
    analysis_id: str | None = Field(
        default=None,
        description="Optional analysis ID (auto-generated if not provided)",
    )
    skill_level: Literal["beginner", "intermediate", "expert"] = Field(
        default="intermediate",
        description="User's experience level for personalized output",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "url": "https://example.com/article",
                "skill_level": "intermediate",
            }
        }
    }


class AnalyzeCreateResponse(BaseModel):
    """Response schema for creating a new analysis.

    This schema is returned immediately after creating an analysis request.
    It contains minimal information available at creation time.

    Attributes:
        analysis_id: Unique identifier for the analysis
        url: Source URL that was analyzed
        content_type: Detected content type (article, video, repo)
        status: Analysis status (always "pending" at creation)
        sse_endpoint: URL endpoint for streaming progress updates

    Example:
        ```python
        response = AnalyzeCreateResponse(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            content_type="article",
            status="pending",
            sse_endpoint="/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/stream",
        )
        ```

    """

    analysis_id: str = Field(..., description="Unique identifier for the analysis")
    url: str = Field(..., description="Source URL that was analyzed")
    content_type: str = Field(..., description="Detected content type (article, video, repo)")
    status: str = Field(
        default="pending", description="Analysis status (pending, running, complete, failed)"
    )
    sse_endpoint: str = Field(..., description="SSE endpoint URL for streaming progress updates")

    model_config = {
        "json_schema_extra": {
            "example": {
                "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                "url": "https://example.com/article",
                "content_type": "article",
                "status": "pending",
                "sse_endpoint": "/api/v1/analyze/123e4567-e89b-12d3-a456-426614174000/stream",
            }
        }
    }


class AnalyzeStatusResponse(BaseModel):
    """Response schema for analysis status and artifact lookup."""

    analysis_id: str = Field(..., description="Unique identifier for the analysis")
    url: str = Field(..., description="Source URL that was analyzed")
    content_type: str = Field(..., description="Detected content type")
    status: str = Field(..., description="Analysis status")
    title: str | None = Field(None, description="Extracted title if available")
    artifact_id: str | None = Field(None, description="Latest artifact id if generated")
    created_at: str = Field(..., description="Timestamp when analysis was created")
    updated_at: str = Field(..., description="Timestamp when analysis was last updated")


class AnalyzeResponse(BaseModel):
    """Response schema for analysis results.

    Attributes:
        analysis_id: Unique identifier for the analysis
        url: Source URL that was analyzed
        content_type: Detected content type (article, video, repo)
        raw_content: Extracted text content
        extraction_metadata: Metadata from extraction service
        content_embedding: Vector embedding of the content (dimensions)
        status: Analysis status (pending, running, complete, failed)

    Example:
        ```python
        response = AnalyzeResponse(
            analysis_id="123e4567-e89b-12d3-a456-426614174000",
            url="https://example.com/article",
            content_type="article",
            raw_content="Article content...",
            extraction_metadata={"word_count": 5234},
            content_embedding=[0.1, 0.2, ...],  # 1536 dimensions
            status="complete",
        )
        ```

    """

    analysis_id: str = Field(..., description="Unique identifier for the analysis")
    url: str = Field(..., description="Source URL that was analyzed")
    content_type: str = Field(..., description="Detected content type")
    raw_content: str = Field(..., description="Extracted text content")
    extraction_metadata: dict = Field(..., description="Metadata from extraction service")
    content_embedding: list[float] = Field(
        ..., description="Vector embedding of the content (1536 dimensions)"
    )
    status: str = Field(
        default="complete", description="Analysis status (pending, running, complete, failed)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "analysis_id": "123e4567-e89b-12d3-a456-426614174000",
                "url": "https://example.com/article",
                "content_type": "article",
                "raw_content": "Article content...",
                "extraction_metadata": {"word_count": 5234},
                "content_embedding": [0.1] * 1536,
                "status": "complete",
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response schema for API errors.

    Attributes:
        error: Error details with code, message, and optional request_id

    Example:
        ```python
        error = ErrorResponse(
            error={
                "code": "INVALID_URL",
                "message": "URL must be a valid HTTP/HTTPS URL",
                "request_id": "abc-123",
            }
        )
        ```

    """

    error: dict[str, str] = Field(
        ...,
        description="Error details with code, message, and optional request_id",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": {
                    "code": "INVALID_URL",
                    "message": "URL must be a valid HTTP/HTTPS URL",
                    "request_id": "abc-123",
                }
            }
        }
    }


# Artifact schemas


class ArtifactMetadataResponse(BaseModel):
    """Metadata and content for an artifact."""

    artifact_id: str = Field(..., description="Artifact identifier")
    analysis_id: str = Field(..., description="Parent analysis identifier")
    markdown_content: str = Field(..., description="Artifact markdown content")
    artifact_metadata: dict | None = Field(None, description="Optional artifact metadata")
    trace_id: str | None = Field(None, description="Langfuse trace ID for feedback")
    created_at: str = Field(..., description="Creation timestamp")


# Context engineering schemas (Handle Pattern)


class ArtifactSection(str, Enum):
    """Available sections for partial content loading.

    Agents can request specific sections to minimize token usage.
    """

    FULL = "full"  # Complete content (use sparingly)
    SUMMARY = "summary"  # LLM-generated summary (~500 tokens)
    FIRST_N = "first_n"  # First N characters
    CODE_BLOCKS = "code_blocks"  # Extracted code snippets only
    HEADINGS = "headings"  # Document structure/outline


class CodeBlockInfo(BaseModel):
    """Information about an extracted code block."""

    start: int = Field(..., description="Start character offset")
    end: int = Field(..., description="End character offset")
    language: str | None = Field(None, description="Programming language if detected")

    model_config = ConfigDict(frozen=True)


class HeadingInfo(BaseModel):
    """Information about a document heading."""

    level: int = Field(..., ge=1, le=6, description="Heading level (1-6)")
    text: str = Field(..., description="Heading text")
    start: int = Field(..., description="Start character offset")

    model_config = ConfigDict(frozen=True)


class ContentSections(BaseModel):
    """Extracted sections and metadata from content.

    Stored in Analysis.content_sections JSONB column.
    """

    code_blocks: list[CodeBlockInfo] = Field(default_factory=list)
    headings: list[HeadingInfo] = Field(default_factory=list)
    word_count: int = Field(0, ge=0)
    char_count: int = Field(0, ge=0)

    model_config = ConfigDict(frozen=True)


class ArtifactRef(BaseModel):
    """Reference to large content stored in database.

    Instead of passing large content inline through agent state,
    we pass lightweight refs with always-available summaries.
    Agents can load full content or sections on-demand via MCP tool.

    Example:
        state = {
            "content_ref": ArtifactRef(
                uri="analysis://abc-123/content",
                summary="Article about React Server Components...",
                size_bytes=45000,
                content_type="text/markdown",
                available_sections=["summary", "code_blocks", "headings"]
            )
        }

    """

    uri: str = Field(
        ...,
        description="Artifact URI: analysis://{analysis_id}/content",
        pattern=r"^analysis://[a-f0-9-]+/content$",
    )
    summary: str = Field(
        ...,
        max_length=2000,
        description="Always-available content summary (~500 tokens)",
    )
    size_bytes: int = Field(..., ge=0, description="Original content size in bytes")
    content_type: str = Field(
        "text/plain",
        description="MIME type: text/plain, text/markdown, etc.",
    )
    available_sections: list[str] = Field(
        default_factory=lambda: ["summary", "full"],
        description="Sections available for loading",
    )

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_analysis_id(
        cls,
        analysis_id: str,
        summary: str,
        size_bytes: int,
        content_type: str = "text/plain",
        available_sections: list[str] | None = None,
    ) -> "ArtifactRef":
        """Create an ArtifactRef from an analysis ID."""
        return cls(
            uri=f"analysis://{analysis_id}/content",
            summary=summary,
            size_bytes=size_bytes,
            content_type=content_type,
            available_sections=available_sections or ["summary", "full"],
        )

    def get_analysis_id(self) -> str:
        """Extract analysis ID from URI."""
        # URI format: analysis://{analysis_id}/content
        return self.uri.split("/")[2]


class LoadArtifactRequest(BaseModel):
    """Request schema for load_artifact MCP tool."""

    uri: str = Field(..., description="Artifact URI to load")
    section: ArtifactSection = Field(
        ArtifactSection.SUMMARY,
        description="Section to load (default: summary)",
    )
    max_chars: int | None = Field(
        None,
        ge=100,
        le=500000,
        description="Max chars for full/first_n sections",
    )


class LoadArtifactResponse(BaseModel):
    """Response schema for load_artifact MCP tool."""

    content: str = Field(..., description="Loaded content or section")
    section: ArtifactSection = Field(..., description="Section that was loaded")
    truncated: bool = Field(False, description="Whether content was truncated")
    original_size: int = Field(..., description="Original content size")
