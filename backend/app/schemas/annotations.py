"""Pydantic schemas for annotation endpoints.

These schemas handle request/response validation for the feedback
and annotation queue API endpoints.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class FeedbackType(str, Enum):
    """Allowed feedback types."""

    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class SubmitFeedbackRequest(BaseModel):
    """Request schema for submitting user feedback."""

    artifact_id: uuid.UUID = Field(..., description="ID of the artifact")
    trace_id: str | None = Field(None, description="Langfuse trace ID (optional)")
    feedback: FeedbackType = Field(..., description="User feedback type")
    comment: str | None = Field(
        None,
        max_length=1000,
        description="Optional user comment (max 1000 chars)",
    )

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, v: str | None) -> str | None:
        """Validate and sanitize comment."""
        if v:
            # Strip whitespace
            v = v.strip()
            # Reject empty strings
            if not v:
                return None
        return v


class SubmitFeedbackResponse(BaseModel):
    """Response schema for feedback submission."""

    status: str = Field(..., description="Submission status")
    message: str = Field(..., description="Human-readable message")
    langfuse_submitted: bool = Field(..., description="Whether feedback was submitted to Langfuse")


class FlagForReviewRequest(BaseModel):
    """Request schema for flagging artifact for review."""

    artifact_id: uuid.UUID = Field(..., description="ID of the artifact to flag")
    reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Reason for flagging (10-500 chars)",
    )


class FlagForReviewResponse(BaseModel):
    """Response schema for flag operation."""

    queue_id: int = Field(..., description="ID of the queue entry")
    message: str = Field(..., description="Confirmation message")


class AnnotationQueueItemResponse(BaseModel):
    """Response schema for annotation queue entry."""

    id: int = Field(..., description="Queue entry ID")
    artifact_id: uuid.UUID = Field(..., description="Artifact ID")
    trace_id: str | None = Field(None, description="Langfuse trace ID")
    reason: str = Field(..., description="Reason for queuing")
    status: str = Field(..., description="Queue status")
    metadata: dict | None = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="Queue entry creation time")
    reviewed_at: datetime | None = Field(None, description="Review completion time")

    model_config = {"from_attributes": True}


class AnnotationQueueListResponse(BaseModel):
    """Response schema for paginated queue list."""

    items: list[AnnotationQueueItemResponse] = Field(..., description="Queue entries")
    total: int = Field(..., description="Total number of pending items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Current offset")
