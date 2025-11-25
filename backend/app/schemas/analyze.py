"""Pydantic schemas for analysis API endpoints."""

from pydantic import BaseModel, Field, HttpUrl


class AnalyzeRequest(BaseModel):
    """Request schema for creating a new analysis.

    Attributes:
        url: The URL to analyze (must be a valid HTTP/HTTPS URL)
        analysis_id: Optional analysis ID (auto-generated if not provided)

    Example:
        ```python
        request = AnalyzeRequest(url="https://example.com/article")
        ```

    """

    url: HttpUrl = Field(..., description="URL to analyze (must be HTTP/HTTPS)")
    analysis_id: str | None = Field(
        default=None,
        description="Optional analysis ID (auto-generated if not provided)",
    )

    model_config = {"json_schema_extra": {"example": {"url": "https://example.com/article"}}}


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
