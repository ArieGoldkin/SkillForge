"""Pydantic schemas for artifact endpoints."""

from pydantic import BaseModel, Field


class ArtifactMetadataResponse(BaseModel):
    """Metadata and content for an artifact."""

    artifact_id: str = Field(..., description="Artifact identifier")
    analysis_id: str = Field(..., description="Parent analysis identifier")
    markdown_content: str = Field(..., description="Artifact markdown content")
    artifact_metadata: dict | None = Field(None, description="Optional artifact metadata")
    created_at: str = Field(..., description="Creation timestamp")
