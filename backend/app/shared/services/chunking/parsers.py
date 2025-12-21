r"""Pluggable content parsers for format-aware chunking.

This module provides a Protocol-based interface for parsing different content formats
(plain text, Markdown, HTML, code) into semantic sections before chunking.

Design follows LlamaIndex NodeParser and LangChain TextSplitter patterns for
industry-standard RAG pipelines (2025 best practices).

Example:
    >>> parser = MarkdownParser()
    >>> sections = parser.parse("# Heading\nContent")
    >>> for section in sections:
    ...     print(section.title, section.level)

See Also:
    - Issue #222: Pluggable Parsers for Chunking
    - docs/issues/222-pluggable-parsers/README.md

"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser as StdlibHTMLParser
from typing import Any, ClassVar, Protocol, runtime_checkable


@dataclass
class ParsedSection:
    """A parsed section with title and hierarchical metadata.

    Output type for ContentParser implementations. Captures semantic structure
    of documents before chunking.

    Attributes:
        title: Section heading/title (None for untitled sections)
        content: The text content of this section
        level: Heading level (1-6 for Markdown/HTML, 0 for plain text)
        path: Hierarchical path from document root (e.g., ["Chapter 1", "Section 1.1"])
        metadata: Optional parser-specific metadata (e.g., {"header_1": "Chapter 1"})

    Example:
        >>> section = ParsedSection(
        ...     title="Introduction",
        ...     content="This is the intro...",
        ...     level=1,
        ...     path=["Introduction"],
        ...     metadata={"header_1": "Introduction"},
        ... )

    """

    title: str | None
    content: str
    level: int = 0
    path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ContentParser(Protocol):
    """Protocol for content parsers that extract semantic structure from documents.

    Implementations should:
    - Declare supported content types via supported_types property
    - Parse content into structured ParsedSection objects
    - Implement heuristic detection via can_parse() for auto-selection

    This protocol follows the LlamaIndex NodeParser pattern for format-aware parsing
    before chunking.

    Example:
        >>> class MyParser:
        ...     @property
        ...     def supported_types(self) -> list[str]:
        ...         return ["text/custom", "custom"]
        ...
        ...     def parse(
        ...         self, content: str, content_type: str | None = None
        ...     ) -> list[ParsedSection]:
        ...         return [ParsedSection(title=None, content=content, level=0, path=["root"])]
        ...
        ...     def can_parse(self, content: str, content_type: str | None = None) -> bool:
        ...         return content_type in self.supported_types

    """

    @property
    def supported_types(self) -> list[str]:
        """Content types this parser supports.

        Returns MIME types and file extensions (e.g., ['text/markdown', 'md']).
        Used by ParserRegistry for content-type matching.

        Returns:
            List of supported content types and extensions

        """
        ...

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        """Parse content into structured sections.

        Args:
            content: Raw content to parse
            content_type: Optional MIME type or file extension hint

        Returns:
            List of ParsedSection objects with semantic structure

        Raises:
            ValueError: If content cannot be parsed

        """
        ...

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        """Check if this parser can handle the given content.

        Used by ParserRegistry for heuristic parser selection when content_type
        is not explicitly provided.

        Args:
            content: Raw content to check
            content_type: Optional MIME type or file extension hint

        Returns:
            True if parser can handle this content

        """
        ...


class TextParser:
    r"""Default text parser that splits on double newlines (paragraph breaks).

    This parser replicates the existing _split_to_paragraphs() behavior,
    providing backward compatibility as the fallback parser.

    Supported content types: text/plain, txt, text

    Example:
        >>> parser = TextParser()
        >>> sections = parser.parse("Paragraph 1\n\nParagraph 2\n\nParagraph 3")
        >>> len(sections)
        3
        >>> sections[0].content
        'Paragraph 1'

    """

    @property
    def supported_types(self) -> list[str]:
        """Return supported content types for plain text."""
        return ["text/plain", "txt", "text"]

    def parse(self, content: str, _content_type: str | None = None) -> list[ParsedSection]:
        r"""Parse plain text into paragraph sections.

        Splits on double newlines (\n\n), strips whitespace, and filters empty sections.

        Args:
            content: Raw text content
            content_type: Ignored (all text is supported)

        Returns:
            List of ParsedSection objects, one per paragraph

        """
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

        return [
            ParsedSection(
                title=None,
                content=para,
                level=0,
                path=["root"],
            )
            for para in paragraphs
        ]

    def can_parse(self, _content: str, _content_type: str | None = None) -> bool:
        """Return True - default parser accepts all content."""
        return True


class MarkdownParser:
    r"""Markdown parser following LlamaIndex MarkdownNodeParser patterns.

    Splits Markdown documents by headers (#, ##, etc.), preserving hierarchy
    and tracking header metadata for filtering. Protects code blocks from
    splitting.

    Features (aligned with 2025 RAG best practices):
    - Splits by headers (#, ##, etc.) preserving hierarchy
    - Tracks header metadata for each section (like LangChain's MarkdownHeaderTextSplitter)
    - Handles code blocks (``` ```) without splitting inside them
    - No external dependencies - uses stdlib re module

    Supported content types: text/markdown, md, markdown

    Reference:
        https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/modules/

    Example:
        >>> parser = MarkdownParser()
        >>> sections = parser.parse("# Chapter 1\nIntro\n## Section 1.1\nDetails")
        >>> sections[0].title
        'Chapter 1'
        >>> sections[0].metadata
        {'header_1': 'Chapter 1'}
        >>> sections[1].path
        ['Chapter 1', 'Section 1.1']

    """

    HEADING_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    CODE_BLOCK_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"```[\s\S]*?```", re.MULTILINE)

    @property
    def supported_types(self) -> list[str]:
        """Return supported content types for Markdown."""
        return ["text/markdown", "md", "markdown"]

    def parse(self, content: str, _content_type: str | None = None) -> list[ParsedSection]:
        """Parse Markdown into sections by headers.

        Splits on header lines (#, ##, etc.), preserving content under each header
        until the next header. Tracks hierarchical path and metadata.

        Args:
            content: Raw Markdown content
            content_type: Optional type hint (not required)

        Returns:
            List of ParsedSection objects with:
            - title: The header text
            - content: Text under that header (until next header)
            - level: Header level (1-6)
            - path: Hierarchical path ["H1 title", "H2 title", ...]
            - metadata: {"header_1": "...", "header_2": "...", ...} for filtering

        """
        sections: list[ParsedSection] = []

        # Temporarily replace code blocks to avoid splitting inside them
        code_blocks: list[str] = []

        def save_code_block(match: re.Match[str]) -> str:
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        protected_content = self.CODE_BLOCK_PATTERN.sub(save_code_block, content)
        lines = protected_content.split("\n")

        # Track header hierarchy (like LangChain's metadata tracking)
        header_stack: dict[int, str] = {}  # level -> title
        current_title: str | None = None
        current_level = 0
        current_content: list[str] = []

        for line in lines:
            heading_match = self.HEADING_PATTERN.match(line)
            if heading_match:
                # Flush previous section
                if current_content or current_title:
                    section_content = "\n".join(current_content).strip()
                    # Restore code blocks
                    for i, block in enumerate(code_blocks):
                        section_content = section_content.replace(f"__CODE_BLOCK_{i}__", block)

                    sections.append(
                        ParsedSection(
                            title=current_title,
                            content=section_content,
                            level=current_level,
                            path=self._build_path(header_stack, current_level),
                            metadata=self._build_header_metadata(header_stack),
                        )
                    )

                # Update header hierarchy
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()

                # Clear deeper levels when we go up
                header_stack = {k: v for k, v in header_stack.items() if k < level}
                header_stack[level] = title

                current_title = title
                current_level = level
                current_content = []
            else:
                current_content.append(line)

        # Flush final section
        if current_content or current_title:
            section_content = "\n".join(current_content).strip()
            for i, block in enumerate(code_blocks):
                section_content = section_content.replace(f"__CODE_BLOCK_{i}__", block)

            sections.append(
                ParsedSection(
                    title=current_title,
                    content=section_content,
                    level=current_level,
                    path=self._build_path(header_stack, current_level),
                    metadata=self._build_header_metadata(header_stack),
                )
            )

        # If no headings found, return as single section
        if not sections:
            sections.append(
                ParsedSection(title=None, content=content.strip(), level=0, path=["root"])
            )

        return sections

    def _build_path(self, header_stack: dict[int, str], current_level: int) -> list[str]:
        """Build hierarchical path from header stack.

        Args:
            header_stack: Mapping of heading levels to titles
            current_level: Current section's heading level

        Returns:
            Hierarchical path list (e.g., ["Chapter 1", "Section 1.1"]), defaults to ["root"]

        """
        path = [header_stack[lvl] for lvl in sorted(header_stack.keys()) if lvl <= current_level]
        return path if path else ["root"]

    def _build_header_metadata(self, header_stack: dict[int, str]) -> dict[str, Any]:
        """Build LangChain-style header metadata for filtering.

        Args:
            header_stack: Mapping of heading levels to titles

        Returns:
            Metadata dict with keys like "header_1", "header_2", etc.

        """
        return {f"header_{lvl}": title for lvl, title in header_stack.items()}

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        """Check if content looks like Markdown.

        Args:
            content: Content to check
            content_type: Optional type hint

        Returns:
            True if content_type matches or content contains Markdown headers

        """
        if content_type in self.supported_types:
            return True
        return bool(self.HEADING_PATTERN.search(content))


class HTMLParser:
    """HTML parser following LlamaIndex HTMLNodeParser patterns.

    Extracts semantic HTML tags (p, h1-h6, section, article, etc.) while
    skipping non-content elements (script, style, nav, footer).

    Features (aligned with 2025 RAG best practices):
    - Extracts semantic HTML tags: ["p", "h1-h6", "li", "b", "i", "u", "section", "article"]
    - Strips scripts, styles, and non-content elements
    - Uses Python's built-in html.parser - no BeautifulSoup dependency
    - Preserves document structure in path metadata

    Supported content types: text/html, html, htm

    Reference:
        https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/modules/

    Example:
        >>> parser = HTMLParser()
        >>> sections = parser.parse("<h1>Title</h1><p>Content</p>")
        >>> sections[0].title
        'Title'
        >>> sections[1].content
        'Content'

    """

    # LlamaIndex default tags (we add a few more semantic tags)
    DEFAULT_TAGS: ClassVar[list[str]] = [
        "p",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "b",
        "i",
        "u",
        "section",
        "article",
        "main",
        "div",
    ]
    SKIP_TAGS: ClassVar[list[str]] = ["script", "style", "nav", "footer", "header", "aside"]

    def __init__(self, tags: list[str] | None = None):
        """Initialize HTML parser with custom tag list.

        Args:
            tags: Optional list of HTML tags to extract. If None, uses DEFAULT_TAGS.

        """
        self.tags = tags or self.DEFAULT_TAGS

    @property
    def supported_types(self) -> list[str]:
        """Return supported content types for HTML."""
        return ["text/html", "html", "htm"]

    def parse(self, content: str, _content_type: str | None = None) -> list[ParsedSection]:
        """Parse HTML into semantic sections.

        Extracts content from semantic tags while skipping non-content elements.
        Preserves heading hierarchy for path tracking.

        Args:
            content: Raw HTML content
            content_type: Optional type hint (not required)

        Returns:
            List of ParsedSection objects for each semantic block

        """
        sections: list[ParsedSection] = []
        current_heading: str | None = None
        current_level = 0

        # Capture outer instance variables for inner class
        parser_tags = self.tags
        skip_tags = self.SKIP_TAGS

        class SectionExtractor(StdlibHTMLParser):
            """Inner HTML parser that extracts semantic sections."""

            def __init__(self) -> None:
                super().__init__()
                self.tag_stack: list[str] = []
                self.current_text: list[str] = []
                self.skip_depth = 0

            def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
                self.tag_stack.append(tag)
                if tag in skip_tags:
                    self.skip_depth += 1

            def handle_endtag(self, tag: str) -> None:
                if tag in skip_tags:
                    self.skip_depth = max(0, self.skip_depth - 1)

                if self.skip_depth == 0 and tag in parser_tags:
                    text = " ".join(self.current_text).strip()
                    if text:
                        nonlocal current_heading, current_level

                        is_heading = tag in ("h1", "h2", "h3", "h4", "h5", "h6")
                        level = int(tag[1]) if is_heading else 0

                        if is_heading:
                            current_heading = text
                            current_level = level

                        sections.append(
                            ParsedSection(
                                title=text if is_heading else current_heading,
                                content="" if is_heading else text,
                                level=level if is_heading else current_level,
                                path=[current_heading] if current_heading else ["root"],
                                metadata={"html_tag": tag},
                            )
                        )
                    self.current_text = []

                if self.tag_stack and self.tag_stack[-1] == tag:
                    self.tag_stack.pop()

            def handle_data(self, data: str) -> None:
                if self.skip_depth == 0 and data.strip():
                    self.current_text.append(data.strip())

        extractor = SectionExtractor()
        try:
            extractor.feed(content)
        except (ValueError, TypeError, AttributeError):
            # Fallback for malformed HTML
            return [ParsedSection(title=None, content=content, level=0, path=["root"])]

        return (
            sections
            if sections
            else [ParsedSection(title=None, content=content, level=0, path=["root"])]
        )

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        """Check if content looks like HTML.

        Args:
            content: Content to check
            content_type: Optional type hint

        Returns:
            True if content_type matches or content contains HTML tags

        """
        if content_type in self.supported_types:
            return True
        # Check for HTML-like content
        return bool(re.search(r"<[a-zA-Z][^>]*>", content))


class CodeParser:
    r"""Code parser following LlamaIndex CodeSplitter patterns.

    Splits code by semantic boundaries (functions, classes, methods) with
    configurable line-based chunking and overlap for large code blocks.

    Features (aligned with 2025 RAG best practices):
    - Configurable chunk_lines (default: 40) and chunk_lines_overlap (default: 15)
    - Language detection for Python, JavaScript/TypeScript, Go, Rust
    - Extracts classes, functions, methods as semantic units
    - Falls back to line-based chunking for unsupported languages

    Supported languages: Python, JavaScript, TypeScript, Go, Rust

    Reference:
        https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/modules/

    Example:
        >>> parser = CodeParser(chunk_lines=40)
        >>> sections = parser.parse("def foo():\n    pass\n\ndef bar():\n    pass")
        >>> sections[0].title
        'def foo'
        >>> sections[0].metadata["language"]
        'python'

    """

    # LlamaIndex defaults
    DEFAULT_CHUNK_LINES: ClassVar[int] = 40
    DEFAULT_CHUNK_LINES_OVERLAP: ClassVar[int] = 15
    DEFAULT_MAX_CHARS: ClassVar[int] = 1500

    # Language-specific patterns
    PATTERNS: ClassVar[dict[str, re.Pattern[str]]] = {
        "python": re.compile(r"^(class|def|async def)\s+(\w+)", re.MULTILINE),
        "javascript": re.compile(r"^(function|class|const|let|var|export)\s+(\w+)", re.MULTILINE),
        "typescript": re.compile(
            r"^(function|class|const|let|var|export|interface|type)\s+(\w+)", re.MULTILINE
        ),
        "go": re.compile(r"^(func|type)\s+(\w+)", re.MULTILINE),
        "rust": re.compile(r"^(fn|struct|impl|enum|trait)\s+(\w+)", re.MULTILINE),
    }

    def __init__(
        self,
        chunk_lines: int = DEFAULT_CHUNK_LINES,
        chunk_lines_overlap: int = DEFAULT_CHUNK_LINES_OVERLAP,
        max_chars: int = DEFAULT_MAX_CHARS,
    ):
        """Initialize code parser with chunking parameters.

        Args:
            chunk_lines: Number of lines per chunk (default: 40)
            chunk_lines_overlap: Number of overlapping lines between chunks (default: 15)
            max_chars: Maximum characters per chunk (default: 1500)

        """
        self.chunk_lines = chunk_lines
        self.chunk_lines_overlap = chunk_lines_overlap
        self.max_chars = max_chars

    @property
    def supported_types(self) -> list[str]:
        """Return supported content types for code."""
        return [
            "text/x-python",
            "py",
            "python",
            "text/javascript",
            "js",
            "ts",
            "typescript",
            "go",
            "rust",
            "code",
        ]

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        """Parse code into semantic sections (functions, classes) or line chunks.

        Attempts to detect language and split by semantic boundaries (function/class
        definitions). Falls back to line-based chunking if no patterns match.

        Args:
            content: Raw code content
            content_type: Optional language hint (e.g., "py", "js")

        Returns:
            List of ParsedSection objects for each code section

        """
        language = self._detect_language(content, content_type)
        pattern = self.PATTERNS.get(language)

        if pattern:
            sections = self._parse_by_definitions(content, pattern, language)
            if sections:
                return sections

        # Fallback: line-based chunking (like LlamaIndex's default behavior)
        return self._parse_by_lines(content)

    def _detect_language(self, content: str, content_type: str | None) -> str:
        """Detect programming language from content type or heuristics.

        Args:
            content: Code content to analyze
            content_type: Optional type hint

        Returns:
            Language identifier (e.g., "python", "javascript") or "unknown"

        """
        type_mapping = {
            "py": "python",
            "python": "python",
            "text/x-python": "python",
            "js": "javascript",
            "javascript": "javascript",
            "text/javascript": "javascript",
            "ts": "typescript",
            "typescript": "typescript",
            "go": "go",
            "rust": "rust",
        }
        if content_type and content_type in type_mapping:
            return type_mapping[content_type]

        # Heuristics
        if "def " in content or "import " in content:
            return "python"
        if "function " in content or "const " in content or "=>" in content:
            return "javascript"
        if "func " in content and "package " in content:
            return "go"
        if "fn " in content and ("let mut" in content or "impl " in content):
            return "rust"

        return "unknown"

    def _parse_by_definitions(
        self, content: str, pattern: re.Pattern[str], language: str
    ) -> list[ParsedSection]:
        """Parse code by function/class definitions.

        Args:
            content: Code content
            pattern: Regex pattern for language-specific definitions
            language: Language identifier

        Returns:
            List of ParsedSection objects or empty list if no matches

        """
        matches = list(pattern.finditer(content))
        if not matches:
            return []

        sections: list[ParsedSection] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)

            kind = match.group(1)
            name = match.group(2)
            section_content = content[start:end].strip()

            # Respect max_chars limit
            if len(section_content) > self.max_chars:
                section_content = section_content[: self.max_chars] + "\n# ... truncated"

            sections.append(
                ParsedSection(
                    title=f"{kind} {name}",
                    content=section_content,
                    level=1
                    if kind in ("class", "struct", "impl", "trait", "type", "interface")
                    else 2,
                    path=[name],
                    metadata={"kind": kind, "name": name, "language": language},
                )
            )

        return sections

    def _parse_by_lines(self, content: str) -> list[ParsedSection]:
        """Fallback: chunk by lines with overlap (LlamaIndex default behavior).

        Args:
            content: Code content to chunk

        Returns:
            List of ParsedSection objects for line-based chunks

        """
        lines = content.split("\n")
        sections: list[ParsedSection] = []

        start = 0
        chunk_idx = 0
        while start < len(lines):
            end = min(start + self.chunk_lines, len(lines))
            chunk_content = "\n".join(lines[start:end])

            if len(chunk_content) > self.max_chars:
                chunk_content = chunk_content[: self.max_chars]

            sections.append(
                ParsedSection(
                    title=f"chunk_{chunk_idx}",
                    content=chunk_content,
                    level=0,
                    path=["root", f"chunk_{chunk_idx}"],
                    metadata={"chunk_idx": chunk_idx, "line_start": start, "line_end": end},
                )
            )

            # Advance start position, ensuring we always make progress
            # When overlap >= chunk_lines, we must still advance by at least 1
            next_start = end - self.chunk_lines_overlap
            if next_start <= start:
                next_start = start + 1
            start = next_start
            chunk_idx += 1

            # Break if we've processed all lines
            if end >= len(lines):
                break

        return (
            sections
            if sections
            else [ParsedSection(title=None, content=content, level=0, path=["root"])]
        )

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        """Check if content looks like code.

        Args:
            content: Content to check
            content_type: Optional type hint

        Returns:
            True if content_type matches or content contains code patterns

        """
        if content_type in self.supported_types:
            return True
        return any(p.search(content) for p in self.PATTERNS.values())


class ParserRegistry:
    r"""Registry for content parsers with automatic selection.

    Provides centralized parser discovery and selection based on content types
    or heuristic matching. Falls back to TextParser when no specialized parser
    is available.

    Example:
        >>> registry = ParserRegistry()
        >>> registry.register(MarkdownParser())
        >>> registry.register(HTMLParser())
        >>> parser = registry.get_parser("# Title\nContent", "text/markdown")
        >>> isinstance(parser, MarkdownParser)
        True

    """

    def __init__(self) -> None:
        """Initialize registry with default TextParser as fallback."""
        self._parsers: dict[str, ContentParser] = {}
        self._default: ContentParser = TextParser()

    def register(self, parser: ContentParser) -> None:
        """Register a parser for its supported types.

        Each content type in parser.supported_types will be mapped to this parser.

        Args:
            parser: Parser instance to register

        """
        for content_type in parser.supported_types:
            self._parsers[content_type] = parser

    def get_parser(self, content: str, content_type: str | None = None) -> ContentParser:
        """Get appropriate parser for content.

        Selection priority:
        1. Exact content_type match in registry
        2. First parser where can_parse() returns True
        3. Default TextParser (always accepts)

        Args:
            content: Content to parse
            content_type: Optional MIME type or file extension hint

        Returns:
            ContentParser instance (never None - falls back to TextParser)

        """
        if content_type and content_type in self._parsers:
            return self._parsers[content_type]

        for parser in self._parsers.values():
            if parser.can_parse(content, content_type):
                return parser

        return self._default
