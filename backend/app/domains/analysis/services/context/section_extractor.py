"""Section extractor for Handle Pattern content analysis.

Extracts code blocks, headings, and metadata from content for partial loading.
"""

import re

from app.domains.analysis.schemas.api import CodeBlockInfo, ContentSections, HeadingInfo


class SectionExtractor:
    """Extract sections from content for partial loading.

    Identifies code blocks, headings, and computes content metadata
    to enable efficient partial content retrieval.
    """

    # Regex patterns for content analysis
    CODE_BLOCK_PATTERN = re.compile(
        r"```(\w*)\n(.*?)```",
        re.DOTALL,
    )
    HEADING_PATTERN = re.compile(
        r"^(#{1,6})\s+(.+)$",
        re.MULTILINE,
    )

    def extract(self, content: str) -> ContentSections:
        """Extract all sections from content.

        Args:
            content: Raw text content to analyze

        Returns:
            ContentSections with code blocks, headings, and metadata

        """
        return ContentSections(
            code_blocks=self._extract_code_blocks(content),
            headings=self._extract_headings(content),
            word_count=self._count_words(content),
            char_count=len(content),
        )

    def _extract_code_blocks(self, content: str) -> list[CodeBlockInfo]:
        """Extract code block positions and languages."""
        blocks: list[CodeBlockInfo] = []

        for match in self.CODE_BLOCK_PATTERN.finditer(content):
            language = match.group(1) or None
            blocks.append(
                CodeBlockInfo(
                    start=match.start(),
                    end=match.end(),
                    language=language,
                )
            )

        return blocks

    def _extract_headings(self, content: str) -> list[HeadingInfo]:
        """Extract heading positions and levels."""
        headings: list[HeadingInfo] = []

        for match in self.HEADING_PATTERN.finditer(content):
            level = len(match.group(1))  # Count # characters
            text = match.group(2).strip()
            headings.append(
                HeadingInfo(
                    level=level,
                    text=text,
                    start=match.start(),
                )
            )

        return headings

    def _count_words(self, content: str) -> int:
        """Count words in content."""
        return len(content.split())

    def get_code_blocks_text(self, content: str) -> str:
        """Extract just the code blocks as text.

        Returns concatenated code blocks with language headers.
        """
        sections = self.extract(content)
        if not sections.code_blocks:
            return "No code blocks found in content."

        result: list[str] = []
        for block in sections.code_blocks:
            code_text = content[block.start : block.end]
            result.append(code_text)

        return "\n\n".join(result)

    def get_headings_outline(self, content: str) -> str:
        """Get document outline from headings.

        Returns formatted outline with indentation by level.
        """
        sections = self.extract(content)
        if not sections.headings:
            return "No headings found in content."

        result: list[str] = []
        for heading in sections.headings:
            indent = "  " * (heading.level - 1)
            result.append(f"{indent}- {heading.text}")

        return "\n".join(result)
