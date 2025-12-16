"""Artifact store for Handle Pattern - stores large content as refs.

This service implements the Handle Pattern from Google ADK's Context Engineering:
- Store large content in database with lightweight refs
- Generate summaries for always-available context
- Support partial loading via sections

Reference: https://google.github.io/adk-docs/sessions/context-engineering/
"""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domains.analysis.schemas.api import ArtifactRef, ArtifactSection, ContentSections
from app.domains.analysis.services.context.section_extractor import SectionExtractor
from app.models.analysis import Analysis

logger = get_logger(__name__)

# Threshold for generating summaries (5KB)
SUMMARY_THRESHOLD_BYTES = 5000
# Default max chars for first_n section
DEFAULT_FIRST_N_CHARS = 5000
# URI parsing constants
URI_MIN_PARTS = 4  # analysis://{id}/content has 4 parts
# Summary generation constants
SUMMARY_MAX_CHARS = 2000
SUMMARY_MAX_WORDS = 500


class ArtifactStoreError(Exception):
    """Base exception for artifact store errors."""


class ArtifactNotFoundError(ArtifactStoreError):
    """Raised when artifact is not found."""


class InvalidURIError(ArtifactStoreError):
    """Raised when URI format is invalid."""


class ArtifactStore:
    """Database-backed artifact storage with section loading.

    Implements the Handle Pattern: store large payloads as refs,
    load on-demand instead of passing inline through state.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize store with database session."""
        self.session = session
        self.extractor = SectionExtractor()

    async def create_ref(
        self,
        analysis_id: str,
        content: str,
        content_type: str = "text/plain",
        summary: str | None = None,
    ) -> ArtifactRef:
        """Store content and create lightweight ref.

        Args:
            analysis_id: Analysis UUID
            content: Raw content to store
            content_type: MIME type (text/plain, text/markdown)
            summary: Optional pre-generated summary

        Returns:
            ArtifactRef with URI, summary, and available sections

        """
        size_bytes = len(content.encode("utf-8"))

        # Extract sections for partial loading
        sections = self.extractor.extract(content)

        # Generate summary if not provided and content is large
        if summary is None:
            summary = self._generate_summary(content, size_bytes)

        # Determine available sections based on content
        available_sections = self._get_available_sections(sections)

        # Update analysis with content, summary and sections
        # Issue #299-304: Must persist raw_content for load() to retrieve
        await self._update_analysis(
            analysis_id=analysis_id,
            content=content,
            content_summary=summary,
            content_sections=sections.model_dump(),
        )

        logger.info(
            "artifact_ref_created",
            analysis_id=analysis_id,
            size_bytes=size_bytes,
            sections_count=len(available_sections),
            has_code_blocks=bool(sections.code_blocks),
            has_headings=bool(sections.headings),
        )

        return ArtifactRef.from_analysis_id(
            analysis_id=analysis_id,
            summary=summary,
            size_bytes=size_bytes,
            content_type=content_type,
            available_sections=available_sections,
        )

    async def load(
        self,
        uri: str,
        section: ArtifactSection = ArtifactSection.SUMMARY,
        max_chars: int | None = None,
    ) -> str:
        """Load content or section from artifact.

        Args:
            uri: Artifact URI (analysis://{id}/content)
            section: Which section to load
            max_chars: Max characters for full/first_n

        Returns:
            Requested content section

        Raises:
            InvalidURIError: If URI format is invalid
            ArtifactNotFoundError: If analysis not found

        """
        analysis_id = self._parse_uri(uri)
        analysis = await self._get_analysis(analysis_id)

        if analysis is None:
            msg = f"Analysis not found: {analysis_id}"
            raise ArtifactNotFoundError(msg)

        # Type assertion: raw_content is str at runtime
        content: str = str(analysis.raw_content or "")

        match section:
            case ArtifactSection.SUMMARY:
                return self._load_summary(analysis)
            case ArtifactSection.FULL:
                return self._load_full(content, max_chars)
            case ArtifactSection.FIRST_N:
                return self._load_first_n(content, max_chars or DEFAULT_FIRST_N_CHARS)
            case ArtifactSection.CODE_BLOCKS:
                return self._load_code_blocks(content, analysis)
            case ArtifactSection.HEADINGS:
                return self._load_headings(content, analysis)
            case _:
                return self._load_summary(analysis)

    def _parse_uri(self, uri: str) -> str:
        """Extract analysis ID from URI.

        Expected format: analysis://{analysis_id}/content
        """
        if not uri.startswith("analysis://"):
            msg = f"Invalid URI scheme: {uri}"
            raise InvalidURIError(msg)

        parts = uri.split("/")
        if len(parts) < URI_MIN_PARTS:
            msg = f"Invalid URI format: {uri}"
            raise InvalidURIError(msg)

        analysis_id = parts[2]

        # Validate UUID format
        try:
            uuid.UUID(analysis_id)
        except ValueError as e:
            msg = f"Invalid analysis ID in URI: {analysis_id}"
            raise InvalidURIError(msg) from e

        return analysis_id

    async def _get_analysis(self, analysis_id: str) -> Analysis | None:
        """Get analysis by ID."""
        result = await self.session.execute(
            select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
        )
        return result.scalar_one_or_none()

    async def _update_analysis(
        self,
        analysis_id: str,
        content: str,
        content_summary: str,
        content_sections: dict,
    ) -> None:
        """Update analysis with raw_content, summary and sections.

        Issue #299-304: Must persist raw_content so load() can retrieve it.
        """
        await self.session.execute(
            update(Analysis)
            .where(Analysis.id == uuid.UUID(analysis_id))
            .values(
                raw_content=content,
                content_summary=content_summary,
                content_sections=content_sections,
            )
        )
        await self.session.commit()

    def _generate_summary(self, content: str, size_bytes: int) -> str:
        """Generate summary from content.

        For now, uses first ~500 words as summary, capped at 2000 chars.
        Future: Use LLM for better summarization.
        """
        if size_bytes < SUMMARY_THRESHOLD_BYTES:
            # Content is small enough to use as-is
            return content[:SUMMARY_MAX_CHARS] if len(content) > SUMMARY_MAX_CHARS else content

        # Extract meaningful summary (first N words)
        words = content.split()
        summary_words = words[:SUMMARY_MAX_WORDS]
        summary = " ".join(summary_words)

        if len(words) > SUMMARY_MAX_WORDS:
            summary += "..."

        # Ensure summary doesn't exceed max chars (for Pydantic validation)
        if len(summary) > SUMMARY_MAX_CHARS:
            summary = summary[: SUMMARY_MAX_CHARS - 3] + "..."

        return summary

    def _get_available_sections(self, sections: ContentSections) -> list[str]:
        """Determine which sections are available for loading."""
        available = ["summary", "full", "first_n"]

        if sections.code_blocks:
            available.append("code_blocks")

        if sections.headings:
            available.append("headings")

        return available

    def _load_summary(self, analysis: Analysis) -> str:
        """Load summary from analysis."""
        if analysis.content_summary:
            return str(analysis.content_summary)

        # Fallback: generate from raw content
        content: str = str(analysis.raw_content or "")
        return self._generate_summary(content, len(content.encode("utf-8")))

    def _load_full(self, content: str, max_chars: int | None) -> str:
        """Load full content with optional truncation."""
        if max_chars and len(content) > max_chars:
            return content[:max_chars] + f"\n\n[Truncated at {max_chars} characters]"
        return content

    def _load_first_n(self, content: str, n: int) -> str:
        """Load first N characters."""
        if len(content) <= n:
            return content
        return content[:n] + f"\n\n[First {n} characters of {len(content)} total]"

    def _load_code_blocks(self, content: str, analysis: Analysis) -> str:
        """Load code blocks from content."""
        # Use stored sections if available
        if analysis.content_sections:
            sections = ContentSections.model_validate(analysis.content_sections)
            if sections.code_blocks:
                blocks: list[str] = []
                for block in sections.code_blocks:
                    blocks.append(content[block.start : block.end])
                return "\n\n".join(blocks)

        # Fallback: extract fresh
        return self.extractor.get_code_blocks_text(content)

    def _load_headings(self, content: str, analysis: Analysis) -> str:
        """Load headings outline from content."""
        # Use stored sections if available
        if analysis.content_sections:
            sections = ContentSections.model_validate(analysis.content_sections)
            if sections.headings:
                result: list[str] = []
                for heading in sections.headings:
                    indent = "  " * (heading.level - 1)
                    result.append(f"{indent}- {heading.text}")
                return "\n".join(result)

        # Fallback: extract fresh
        return self.extractor.get_headings_outline(content)
