"""Context engineering services for Handle Pattern.

This package implements Google ADK's Context Engineering patterns:
- ArtifactStore: Store large content as refs, load on-demand
- SectionExtractor: Extract code blocks, headings for partial loading
- load_artifact tool: MCP tool for agents to load content sections

Reference: https://google.github.io/adk-docs/sessions/context-engineering/
"""

from app.services.context.artifact_store import (
    ArtifactNotFoundError,
    ArtifactStore,
    ArtifactStoreError,
    InvalidURIError,
)
from app.services.context.section_extractor import SectionExtractor
from app.services.context.tools import ARTIFACT_TOOLS, load_artifact

__all__ = [
    "ARTIFACT_TOOLS",
    "ArtifactNotFoundError",
    "ArtifactStore",
    "ArtifactStoreError",
    "InvalidURIError",
    "SectionExtractor",
    "load_artifact",
]
