"""Workflow result validation schemas.

Pydantic v2 models for validating workflow execution results with type safety,
field validators, and status-aware validation.
"""

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.core.constants import EMBEDDING_DIMENSIONS


class ExtractionMetadata(BaseModel):
    """Metadata extracted from content analysis.

    Contains title, word count, character count, and optional metadata fields.
    All fields are validated with appropriate constraints.
    """

    title: str = Field(..., min_length=1, max_length=500)
    word_count: int = Field(..., ge=0)
    char_count: int = Field(..., ge=0)
    language: str | None = Field(None, max_length=10)
    author: str | None = Field(None, max_length=200)
    published_date: str | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty or whitespace-only."""
        if not v or not v.strip():
            error_msg = "title cannot be empty or whitespace"
            raise ValueError(error_msg)
        return v.strip()


class ContentRef(BaseModel):
    """Content reference for Handle Pattern (Issue #244).

    Represents a reference to content stored in the ArtifactStore.
    URI format: analysis://{analysis_id}/content
    """

    uri: str = Field(..., pattern=r"^analysis://[a-f0-9-]{36}/content$")
    summary: str = Field(..., min_length=1, max_length=2000)
    size_bytes: int = Field(..., ge=0)
    content_type: str = Field(..., max_length=50)
    available_sections: list[str] = Field(default_factory=list)

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        """Validate URI format matches Handle Pattern."""
        pattern = r"^analysis://[a-f0-9-]{36}/content$"
        if not re.match(pattern, v):
            error_msg = f"URI must match pattern: {pattern}"
            raise ValueError(error_msg)
        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content_type is not empty."""
        if not v or not v.strip():
            error_msg = "content_type cannot be empty"
            raise ValueError(error_msg)
        return v.strip()


class WorkflowResult(BaseModel):
    """Validated workflow result schema.

    Represents the complete result of an analysis workflow execution.
    Both raw_content and content_ref are required for completed workflows
    (Issue #244 - Handle Pattern).

    - raw_content: Full content string for embedding, chunking, quality gate
    - content_ref: Handle Pattern reference for agent execution, state passing
    """

    content_ref: ContentRef
    raw_content: str = Field(..., min_length=1)
    extraction_metadata: ExtractionMetadata
    content_embedding: list[float] = Field(
        ..., min_length=EMBEDDING_DIMENSIONS, max_length=EMBEDDING_DIMENSIONS
    )
    artifact_id: str | None = None
    workflow_status: Literal["completed", "failed"] | None = None
    final_error: str | None = None

    @field_validator("content_embedding")
    @classmethod
    def validate_embedding(cls, v: list[float]) -> list[float]:
        """Ensure embedding has exactly 1536 dimensions."""
        if len(v) != EMBEDDING_DIMENSIONS:
            error_msg = f"content_embedding must be {EMBEDDING_DIMENSIONS} dimensions, got {len(v)}"
            raise ValueError(error_msg)
        return v

    @field_validator("raw_content")
    @classmethod
    def validate_raw_content(cls, v: str) -> str:
        """Validate raw_content is not empty or whitespace-only."""
        if not v or not v.strip():
            error_msg = "raw_content cannot be empty"
            raise ValueError(error_msg)
        return v

    def validate_for_status(self, status: str) -> list[str]:
        """Validate required fields for given workflow status.

        Args:
            status: Workflow status ('completed', 'failed', etc.)

        Returns:
            List of missing required field names. Empty list if all fields present.

        """
        missing: list[str] = []

        if status == "completed":
            if not self.content_ref:
                missing.append("content_ref")
            if not self.raw_content:
                missing.append("raw_content")
            if not self.extraction_metadata:
                missing.append("extraction_metadata")
            if not self.content_embedding:
                missing.append("content_embedding")

        elif status == "failed":
            # Failed workflows don't require content fields
            # Error fields validated separately
            pass

        return missing

    async def validate_content_exists(self, session) -> bool:
        """Validate that content_ref URI points to existing content in database.

        Args:
            session: AsyncSession to query database

        Returns:
            True if content exists, False otherwise

        """
        # Extract analysis_id from URI
        uri_parts = self.content_ref.uri.split("/")
        uri_parts_min_length = 3
        if len(uri_parts) < uri_parts_min_length:
            return False
        analysis_id_str = uri_parts[2]

        try:
            analysis_id = UUID(analysis_id_str)
        except ValueError:
            return False

        # Check if content exists in database
        from sqlalchemy import select

        from app.db.models.analysis import Analysis

        result = await session.execute(select(Analysis).where(Analysis.id == analysis_id))
        analysis = result.scalar_one_or_none()

        if not analysis:
            return False

        # Verify raw_content exists
        return analysis.raw_content is not None and len(analysis.raw_content) > 0
