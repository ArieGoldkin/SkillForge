"""Pydantic schemas for context engineering - Handle Pattern.

This module defines schemas for artifact references used in the Handle Pattern
from Google ADK's Context Engineering framework. Large payloads are stored
as references and loaded on-demand rather than passed inline through state.

Reference: https://google.github.io/adk-docs/sessions/context-engineering/
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


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
