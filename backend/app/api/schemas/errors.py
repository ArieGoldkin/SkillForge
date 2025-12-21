"""Standard error response schemas for API endpoints.

This module provides consistent error response models used across all API endpoints.
"""

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Error detail information.

    Attributes:
        code: Machine-readable error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        message: Human-readable error message
        request_id: Optional request ID for tracing (extracted from X-Request-ID header)

    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    request_id: str | None = Field(None, description="Request ID for tracing")


class ErrorResponse(BaseModel):
    """Standard error response wrapper.

    All API error responses follow this structure for consistency.

    Example:
        {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid URL format",
                "request_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

    """

    error: ErrorDetail = Field(..., description="Error details")
