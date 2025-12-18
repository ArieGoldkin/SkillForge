"""Artifact-related type definitions.

This module defines TypedDict structures for artifact metadata
and generation results.
"""

from typing import TypedDict


class ArtifactMetadata(TypedDict, total=False):
    """Metadata for generated artifacts.

    Attributes:
        title: Artifact title
        source_url: Original source URL
        word_count: Total word count
        created_at: ISO timestamp of creation
        artifact_type: Type of artifact (implementation_guide, etc.)
        analysis_id: UUID of source analysis
        version: Artifact version number

    """

    title: str
    source_url: str
    word_count: int
    created_at: str
    artifact_type: str
    analysis_id: str
    version: int


class ArtifactSection(TypedDict, total=False):
    """A section within an artifact.

    Attributes:
        id: Section identifier
        title: Section title
        content: Section content (markdown)
        order: Display order
        section_type: Type of section

    """

    id: str
    title: str
    content: str
    order: int
    section_type: str


class GeneratedArtifact(TypedDict, total=False):
    """Complete generated artifact structure.

    Attributes:
        id: Artifact UUID
        metadata: Artifact metadata
        sections: List of artifact sections
        quick_reference: Quick reference content
        diagrams: Mermaid diagram definitions
        glossary: Term definitions

    """

    id: str
    metadata: ArtifactMetadata
    sections: list[ArtifactSection]
    quick_reference: str
    diagrams: list[str]
    glossary: dict[str, str]
