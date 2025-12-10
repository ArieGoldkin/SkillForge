# Issue 222 – Pluggable Parsers for Chunking (Extensibility)

## Summary
Add an interface and implementations for pluggable content parsers (Markdown, HTML, code-aware) that feed the hierarchical chunker. This future-proofs the chunking system and aligns with 2025 RAG best practices.

## Research: 2025 Best Practices

Based on research from [Firecrawl](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025), [LlamaIndex](https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/modules/), [Weaviate](https://weaviate.io/blog/chunking-strategies-for-rag), and [Docling benchmarks](https://procycons.com/en/blogs/pdf-data-extraction-benchmark/):

### Key Findings

| Strategy | When to Use | Performance |
|----------|-------------|-------------|
| **Recursive Chunking** | Default for most text | LangChain's recommended default |
| **Semantic Chunking** | High-value docs | +70% accuracy but 10x cost |
| **Hierarchical Chunking** | Large/complex docs | Best for coarse-to-fine retrieval |
| **Format-Aware Parsing** | Structured content | Required before chunking structured docs |

### Industry Standards

**LlamaIndex NodeParsers:**
- `MarkdownNodeParser` - Splits by headers, preserves hierarchy
- `HTMLNodeParser` - Uses BeautifulSoup, extracts semantic tags `["p", "h1-h6", "li", "section"]`
- `CodeSplitter` - Language-aware with `chunk_lines=40`, `chunk_lines_overlap=15`

**LangChain TextSplitters:**
- `RecursiveCharacterTextSplitter` - Hierarchical separators `["\n\n", "\n", " ", ""]`
- `MarkdownHeaderTextSplitter` - Splits by headers, tracks metadata
- `Language.PYTHON/JS/etc` - Language-specific code splitting

**Document Parsing Libraries (2025):**
- **Docling** (IBM) - 97.9% accuracy on complex tables, MIT license, 1GB+ install
- **Unstructured** - 64+ file types, Apache 2.0, enterprise-grade
- **Chonkie** - Lightweight chunking, MIT license, fast

### Recommended Architecture (from research)

> "Rather than viewing these libraries as mutually exclusive competitors, a more sophisticated architectural approach is to use them **sequentially**. For complex documents, the optimal pipeline involves using a high-fidelity parser like Docling or Unstructured for the initial parsing stages to produce clean, structurally-aware text (e.g., in Markdown format), then passing this to a specialized, high-performance chunker."

## Goals
- **Format-aware parsing** before chunking (headings from Markdown, semantic blocks from HTML/code)
- **Align with LlamaIndex/LangChain patterns** for familiar APIs
- **Lightweight implementations** using stdlib (no heavy deps like Docling in core)
- **Optional integration points** for advanced parsers (Docling, Unstructured)
- **Backward compatibility** with existing `_split_to_paragraphs()` behavior

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Content Pipeline                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Raw Content         Parser                    Chunker              │
│   ───────────>    ┌───────────┐             ┌───────────┐           │
│                   │           │             │           │           │
│   "# Heading\n    │  Markdown │  sections   │ build_    │  coarse/  │
│    Some text..."  │  Parser   │ ─────────>  │ chunks()  │ ─> fine   │
│                   │           │             │           │  chunks   │
│                   └───────────┘             └───────────┘           │
│                         │                                           │
│                         │ implements                                │
│                         ▼                                           │
│                 ┌───────────────┐                                   │
│                 │ ContentParser │  <── Protocol (interface)         │
│                 │   Protocol    │                                   │
│                 └───────────────┘                                   │
│                         ▲                                           │
│         ┌───────────────┼───────────────┐                          │
│         │               │               │                          │
│   ┌───────────┐   ┌───────────┐   ┌───────────┐                   │
│   │   Text    │   │  Markdown │   │   HTML    │                   │
│   │  Parser   │   │  Parser   │   │  Parser   │                   │
│   │ (default) │   │  (stub)   │   │  (stub)   │                   │
│   └───────────┘   └───────────┘   └───────────┘                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Shapes (Contract)

### ParsedSection (Parser Output)
```python
@dataclass
class ParsedSection:
    """A parsed section with title and content.

    Attributes:
        title: Section heading/title (None for untitled sections)
        content: The text content of this section
        level: Heading level (1-6 for Markdown, 0 for plain text)
        path: Hierarchical path from document root
        metadata: Optional parser-specific metadata
    """
    title: str | None
    content: str
    level: int = 0
    path: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
```

### ContentParser Protocol
```python
@runtime_checkable
class ContentParser(Protocol):
    """Protocol for content parsers.

    Implementations must provide:
    - supported_types: List of content types this parser handles
    - parse(): Convert raw content to ParsedSection list
    - can_parse(): Check if content can be parsed by this parser
    """

    @property
    def supported_types(self) -> list[str]:
        """Content types this parser supports (e.g., ['text/markdown', 'md'])."""
        ...

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        """Parse content into sections.

        Args:
            content: Raw content to parse
            content_type: MIME type or file extension hint

        Returns:
            List of ParsedSection objects
        """
        ...

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        """Check if this parser can handle the content.

        Args:
            content: Raw content to check
            content_type: MIME type or file extension hint

        Returns:
            True if parser can handle this content
        """
        ...
```

## Implementation Plan

### Phase 1: Core Interface (This PR)

1. **Create `parsers.py`** in `backend/app/services/chunking/`
   - `ParsedSection` dataclass
   - `ContentParser` Protocol
   - `TextParser` implementation (wraps current `_split_to_paragraphs`)
   - `ParserRegistry` for parser discovery

2. **Parser Stubs** (minimal implementations that raise `NotImplementedError`)
   - `MarkdownParser` stub
   - `HTMLParser` stub
   - `CodeParser` stub

3. **Integration with Chunker**
   - Add optional `parser: ContentParser | None` parameter to `build_chunks()`
   - If parser provided, use `parser.parse()` instead of `_split_to_paragraphs()`
   - Preserve all existing behavior when no parser specified

### Phase 2: Future Extensions (Out of Scope)
- Full Markdown parser with heading extraction
- HTML parser with semantic block detection
- Code parser with function/class boundary detection

## File Structure

```
backend/app/services/chunking/
├── __init__.py          # Export parsers + chunker
├── chunker.py           # Existing (minor update)
├── parsers.py           # NEW: Parser interface + implementations
├── dedup.py             # Existing (unchanged)
└── summaries.py         # Existing (unchanged)
```

## Detailed Design

### TextParser (Default)
Wraps the existing `_split_to_paragraphs()` logic:

```python
class TextParser:
    """Default text parser - splits on double newlines."""

    @property
    def supported_types(self) -> list[str]:
        return ["text/plain", "txt", "text"]

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
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

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        return True  # Default parser accepts everything
```

### MarkdownParser (LlamaIndex-style Implementation)
```python
class MarkdownParser:
    """Markdown parser following LlamaIndex MarkdownNodeParser patterns.

    Features (aligned with industry standards):
    - Splits by headers (#, ##, etc.) preserving hierarchy
    - Tracks header metadata for each section (like LangChain's MarkdownHeaderTextSplitter)
    - Handles code blocks (``` ```) without splitting inside them
    - No external dependencies - uses stdlib re module

    Reference: https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/modules/
    """

    HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```', re.MULTILINE)

    @property
    def supported_types(self) -> list[str]:
        return ["text/markdown", "md", "markdown"]

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        """Parse markdown into sections by headers.

        Returns sections with:
        - title: The header text
        - content: Text under that header (until next header)
        - level: Header level (1-6)
        - path: Hierarchical path ["H1 title", "H2 title", ...]
        - metadata: {"header_1": "...", "header_2": "...", ...} for filtering
        """
        sections: list[ParsedSection] = []

        # Temporarily replace code blocks to avoid splitting inside them
        code_blocks: list[str] = []
        def save_code_block(match: re.Match) -> str:
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

        protected_content = self.CODE_BLOCK_PATTERN.sub(save_code_block, content)
        lines = protected_content.split('\n')

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
                    section_content = '\n'.join(current_content).strip()
                    # Restore code blocks
                    for i, block in enumerate(code_blocks):
                        section_content = section_content.replace(f"__CODE_BLOCK_{i}__", block)

                    sections.append(ParsedSection(
                        title=current_title,
                        content=section_content,
                        level=current_level,
                        path=self._build_path(header_stack, current_level),
                        metadata=self._build_header_metadata(header_stack),
                    ))

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
            section_content = '\n'.join(current_content).strip()
            for i, block in enumerate(code_blocks):
                section_content = section_content.replace(f"__CODE_BLOCK_{i}__", block)

            sections.append(ParsedSection(
                title=current_title,
                content=section_content,
                level=current_level,
                path=self._build_path(header_stack, current_level),
                metadata=self._build_header_metadata(header_stack),
            ))

        # If no headings found, return as single section
        if not sections:
            sections.append(ParsedSection(
                title=None, content=content.strip(), level=0, path=["root"]
            ))

        return sections

    def _build_path(self, header_stack: dict[int, str], current_level: int) -> list[str]:
        """Build hierarchical path from header stack."""
        return [header_stack[lvl] for lvl in sorted(header_stack.keys()) if lvl <= current_level]

    def _build_header_metadata(self, header_stack: dict[int, str]) -> dict[str, Any]:
        """Build LangChain-style header metadata for filtering."""
        return {f"header_{lvl}": title for lvl, title in header_stack.items()}

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        if content_type in self.supported_types:
            return True
        return bool(self.HEADING_PATTERN.search(content))
```

### HTMLParser (LlamaIndex-style Implementation)
```python
class HTMLParser:
    """HTML parser following LlamaIndex HTMLNodeParser patterns.

    Features (aligned with industry standards):
    - Extracts semantic HTML tags: ["p", "h1-h6", "li", "b", "i", "u", "section", "article"]
    - Strips scripts, styles, and non-content elements
    - Uses Python's built-in html.parser - no BeautifulSoup dependency
    - Preserves document structure in path metadata

    Reference: https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/modules/
    """

    # LlamaIndex default tags (we add a few more semantic tags)
    DEFAULT_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "b", "i", "u", "section", "article", "main", "div"]
    SKIP_TAGS = ["script", "style", "nav", "footer", "header", "aside"]

    def __init__(self, tags: list[str] | None = None):
        self.tags = tags or self.DEFAULT_TAGS

    @property
    def supported_types(self) -> list[str]:
        return ["text/html", "html", "htm"]

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        from html.parser import HTMLParser as StdlibHTMLParser

        sections: list[ParsedSection] = []
        current_heading: str | None = None
        current_level = 0

        class SectionExtractor(StdlibHTMLParser):
            def __init__(extractor_self):
                super().__init__()
                extractor_self.tag_stack: list[str] = []
                extractor_self.current_text: list[str] = []
                extractor_self.skip_depth = 0

            def handle_starttag(extractor_self, tag: str, attrs: list[tuple[str, str | None]]):
                extractor_self.tag_stack.append(tag)
                if tag in self.SKIP_TAGS:
                    extractor_self.skip_depth += 1

            def handle_endtag(extractor_self, tag: str):
                if tag in self.SKIP_TAGS:
                    extractor_self.skip_depth = max(0, extractor_self.skip_depth - 1)

                if extractor_self.skip_depth == 0 and tag in self.tags:
                    text = ' '.join(extractor_self.current_text).strip()
                    if text:
                        nonlocal current_heading, current_level

                        is_heading = tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')
                        level = int(tag[1]) if is_heading else 0

                        if is_heading:
                            current_heading = text
                            current_level = level

                        sections.append(ParsedSection(
                            title=text if is_heading else current_heading,
                            content="" if is_heading else text,
                            level=level if is_heading else current_level,
                            path=[current_heading] if current_heading else ["root"],
                            metadata={"html_tag": tag},
                        ))
                    extractor_self.current_text = []

                if extractor_self.tag_stack and extractor_self.tag_stack[-1] == tag:
                    extractor_self.tag_stack.pop()

            def handle_data(extractor_self, data: str):
                if extractor_self.skip_depth == 0 and data.strip():
                    extractor_self.current_text.append(data.strip())

        extractor = SectionExtractor()
        try:
            extractor.feed(content)
        except Exception:
            # Fallback for malformed HTML
            return [ParsedSection(title=None, content=content, level=0, path=["root"])]

        return sections if sections else [ParsedSection(title=None, content=content, level=0, path=["root"])]

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        if content_type in self.supported_types:
            return True
        # Check for HTML-like content
        return bool(re.search(r'<[a-zA-Z][^>]*>', content))
```

### CodeParser (LlamaIndex-style Implementation)
```python
class CodeParser:
    """Code parser following LlamaIndex CodeSplitter patterns.

    Features (aligned with industry standards):
    - Configurable chunk_lines (default: 40) and chunk_lines_overlap (default: 15)
    - Language detection for Python, JavaScript/TypeScript, Go, Rust
    - Extracts classes, functions, methods as semantic units
    - Falls back to line-based chunking for unsupported languages

    Reference: https://docs.llamaindex.ai/en/stable/module_guides/loading/node_parsers/modules/
    """

    # LlamaIndex defaults
    DEFAULT_CHUNK_LINES = 40
    DEFAULT_CHUNK_LINES_OVERLAP = 15
    DEFAULT_MAX_CHARS = 1500

    # Language-specific patterns
    PATTERNS = {
        "python": re.compile(r'^(class|def|async def)\s+(\w+)', re.MULTILINE),
        "javascript": re.compile(r'^(function|class|const|let|var|export)\s+(\w+)', re.MULTILINE),
        "typescript": re.compile(r'^(function|class|const|let|var|export|interface|type)\s+(\w+)', re.MULTILINE),
        "go": re.compile(r'^(func|type)\s+(\w+)', re.MULTILINE),
        "rust": re.compile(r'^(fn|struct|impl|enum|trait)\s+(\w+)', re.MULTILINE),
    }

    def __init__(
        self,
        chunk_lines: int = DEFAULT_CHUNK_LINES,
        chunk_lines_overlap: int = DEFAULT_CHUNK_LINES_OVERLAP,
        max_chars: int = DEFAULT_MAX_CHARS,
    ):
        self.chunk_lines = chunk_lines
        self.chunk_lines_overlap = chunk_lines_overlap
        self.max_chars = max_chars

    @property
    def supported_types(self) -> list[str]:
        return ["text/x-python", "py", "python", "text/javascript", "js", "ts", "typescript", "go", "rust", "code"]

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        """Parse code into semantic sections (functions, classes) or line chunks."""
        language = self._detect_language(content, content_type)
        pattern = self.PATTERNS.get(language)

        if pattern:
            sections = self._parse_by_definitions(content, pattern, language)
            if sections:
                return sections

        # Fallback: line-based chunking (like LlamaIndex's default behavior)
        return self._parse_by_lines(content)

    def _detect_language(self, content: str, content_type: str | None) -> str:
        """Detect programming language from content type or heuristics."""
        type_mapping = {
            "py": "python", "python": "python", "text/x-python": "python",
            "js": "javascript", "javascript": "javascript", "text/javascript": "javascript",
            "ts": "typescript", "typescript": "typescript",
            "go": "go", "rust": "rust",
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

    def _parse_by_definitions(self, content: str, pattern: re.Pattern, language: str) -> list[ParsedSection]:
        """Parse code by function/class definitions."""
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
                section_content = section_content[:self.max_chars] + "\n# ... truncated"

            sections.append(ParsedSection(
                title=f"{kind} {name}",
                content=section_content,
                level=1 if kind in ("class", "struct", "impl", "trait", "type", "interface") else 2,
                path=[name],
                metadata={"kind": kind, "name": name, "language": language},
            ))

        return sections

    def _parse_by_lines(self, content: str) -> list[ParsedSection]:
        """Fallback: chunk by lines with overlap (LlamaIndex default behavior)."""
        lines = content.split('\n')
        sections: list[ParsedSection] = []

        start = 0
        chunk_idx = 0
        while start < len(lines):
            end = min(start + self.chunk_lines, len(lines))
            chunk_content = '\n'.join(lines[start:end])

            if len(chunk_content) > self.max_chars:
                chunk_content = chunk_content[:self.max_chars]

            sections.append(ParsedSection(
                title=f"chunk_{chunk_idx}",
                content=chunk_content,
                level=0,
                path=["root", f"chunk_{chunk_idx}"],
                metadata={"chunk_idx": chunk_idx, "line_start": start, "line_end": end},
            ))

            start = end - self.chunk_lines_overlap
            chunk_idx += 1

        return sections if sections else [ParsedSection(title=None, content=content, level=0, path=["root"])]

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        if content_type in self.supported_types:
            return True
        return any(p.search(content) for p in self.PATTERNS.values())
```

### ParserRegistry
```python
class ParserRegistry:
    """Registry for content parsers with automatic selection."""

    def __init__(self) -> None:
        self._parsers: dict[str, ContentParser] = {}
        self._default: ContentParser = TextParser()

    def register(self, parser: ContentParser) -> None:
        """Register a parser for its supported types."""
        for content_type in parser.supported_types:
            self._parsers[content_type] = parser

    def get_parser(
        self,
        content: str,
        content_type: str | None = None
    ) -> ContentParser:
        """Get appropriate parser for content.

        Priority:
        1. Exact content_type match
        2. First parser where can_parse() returns True
        3. Default text parser
        """
        if content_type and content_type in self._parsers:
            return self._parsers[content_type]

        for parser in self._parsers.values():
            if parser.can_parse(content, content_type):
                return parser

        return self._default
```

### Chunker Integration

Minimal change to `build_chunks()`:

```python
def build_chunks(
    text: str,
    *,
    parser: ContentParser | None = None,  # NEW optional parameter
    short_window: int = DEFAULT_SHORT_WINDOW,
    # ... existing params
) -> tuple[list[ChunkText], list[ChunkText]]:
    """Produce coarse and fine chunks with path metadata and token validation.

    Args:
        text: Document text to chunk
        parser: Optional content parser. If provided, uses parser.parse()
                instead of default paragraph splitting.
        # ... existing args
    """
    if not text or not text.strip():
        return [], []

    # NEW: Use parser if provided, else fall back to paragraph splitting
    if parser is not None:
        sections = parser.parse(text)
        # Convert ParsedSection to paragraph-like structure
        paragraphs = [s.content for s in sections]
        section_titles = [s.title for s in sections]
        section_paths = [s.path for s in sections]
    else:
        paragraphs = _split_to_paragraphs(text)
        section_titles = [None] * len(paragraphs)
        section_paths = [["root"]] * len(paragraphs)

    # ... rest of chunking logic uses paragraphs, section_titles, section_paths
```

## Scope

### In Scope
- `ContentParser` Protocol definition
- `ParsedSection` dataclass
- `TextParser` implementation (equivalent to current behavior)
- `MarkdownParser` - Full working implementation (regex-based, LlamaIndex-style)
- `HTMLParser` - Full working implementation (stdlib html.parser, LlamaIndex-style tags)
- `CodeParser` - Full working implementation (multi-language, LlamaIndex CodeSplitter-style)
- `ParserRegistry` for parser discovery
- Optional parser parameter in `build_chunks()`
- Documentation on extending parsers + integrating Docling/Unstructured

### Out of Scope
- Heavy external dependencies (Docling, Unstructured, BeautifulSoup)
- AST-based code parsing (tree-sitter)
- PDF/DOCX parsing
- Auto-detection of content types from URLs
- Frontend changes

## Deliverables

| Deliverable | Location |
|-------------|----------|
| Parser interface + types | `backend/app/services/chunking/parsers.py` |
| TextParser implementation | `backend/app/services/chunking/parsers.py` |
| Parser stubs (Markdown/HTML/Code) | `backend/app/services/chunking/parsers.py` |
| ParserRegistry | `backend/app/services/chunking/parsers.py` |
| Chunker integration | `backend/app/services/chunking/chunker.py` (minor update) |
| Unit tests | `backend/tests/unit/chunking/test_parsers.py` |
| Documentation | This README + inline docstrings |

## Tests

### Unit Tests (`test_parsers.py`)
```python
# Test ParsedSection dataclass
def test_parsed_section_defaults():
    section = ParsedSection(title="Intro", content="Hello")
    assert section.level == 0
    assert section.path == []

# Test TextParser
def test_text_parser_splits_paragraphs():
    parser = TextParser()
    sections = parser.parse("Para 1\n\nPara 2\n\nPara 3")
    assert len(sections) == 3
    assert sections[0].content == "Para 1"

def test_text_parser_can_parse_anything():
    parser = TextParser()
    assert parser.can_parse("any content") is True

# Test MarkdownParser stub
def test_markdown_parser_raises_not_implemented():
    parser = MarkdownParser()
    with pytest.raises(NotImplementedError):
        parser.parse("# Heading\nContent")

def test_markdown_parser_can_parse_detects_headers():
    parser = MarkdownParser()
    assert parser.can_parse("# Heading") is True
    assert parser.can_parse("Plain text", "txt") is False

# Test ParserRegistry
def test_registry_returns_default_parser():
    registry = ParserRegistry()
    parser = registry.get_parser("plain text")
    assert isinstance(parser, TextParser)

def test_registry_matches_content_type():
    registry = ParserRegistry()
    registry.register(MarkdownParser())
    parser = registry.get_parser("# Heading", "text/markdown")
    assert isinstance(parser, MarkdownParser)
```

### Integration Tests
```python
# Test chunker with parser
def test_build_chunks_with_parser():
    parser = TextParser()
    coarse, fine = build_chunks("Para 1\n\nPara 2", parser=parser)
    assert len(coarse) == 2

# Test chunker without parser (backward compatibility)
def test_build_chunks_without_parser():
    coarse, fine = build_chunks("Para 1\n\nPara 2")
    assert len(coarse) == 2  # Same as before
```

## Acceptance Criteria

- [ ] `ContentParser` Protocol is defined with `supported_types`, `parse()`, `can_parse()`
- [ ] `ParsedSection` dataclass captures title, content, level, path, metadata
- [ ] `TextParser` produces identical output to current `_split_to_paragraphs()`
- [ ] Parser stubs exist for Markdown, HTML, Code (raise `NotImplementedError`)
- [ ] `ParserRegistry` can register and select parsers
- [ ] `build_chunks()` accepts optional `parser` parameter
- [ ] Existing chunking behavior unchanged when no parser provided
- [ ] Unit tests pass for all components
- [ ] CI checks pass (ruff format, ruff check, mypy)

## Migration Path

**No migration needed** - this is purely additive:

1. Current code continues to work (no parser = existing behavior)
2. New code can optionally pass a parser for format-aware chunking
3. Future PRs can implement full parsers without API changes

## Future: External Parser Integration

The pluggable design enables integrating heavy-duty parsers when needed:

### Docling Integration (Example)
```python
# future: app/services/chunking/parsers_docling.py
class DoclingParser:
    """High-fidelity parser using IBM Docling for complex documents.

    Use for: PDFs with tables, multi-column layouts, scientific papers.
    Install: pip install docling (1GB+ download)
    """

    def __init__(self):
        from docling.document_converter import DocumentConverter
        self.converter = DocumentConverter()

    @property
    def supported_types(self) -> list[str]:
        return ["application/pdf", "pdf", "docx", "pptx"]

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        # Docling outputs markdown - we chain to MarkdownParser
        result = self.converter.convert(content)
        markdown_content = result.document.export_to_markdown()
        return MarkdownParser().parse(markdown_content)

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        return content_type in self.supported_types
```

### Unstructured Integration (Example)
```python
# future: app/services/chunking/parsers_unstructured.py
class UnstructuredParser:
    """Enterprise document parser using Unstructured.io.

    Use for: 64+ file types, enterprise connectors.
    Install: pip install unstructured
    """

    def __init__(self):
        from unstructured.partition.auto import partition

        self._partition = partition

    @property
    def supported_types(self) -> list[str]:
        return ["application/pdf", "text/html", "application/msword", "*"]

    def parse(self, content: str, content_type: str | None = None) -> list[ParsedSection]:
        elements = self._partition(text=content)
        return [
            ParsedSection(
                title=el.metadata.get("title"),
                content=str(el),
                level=0,
                path=["root"],
                metadata={"category": el.category},
            )
            for el in elements
        ]

    def can_parse(self, content: str, content_type: str | None = None) -> bool:
        return True  # Unstructured handles almost anything
```

### Usage Pattern
```python
# Register external parsers when available
registry = ParserRegistry()

try:
    from app.services.chunking.parsers_docling import DoclingParser
    registry.register(DoclingParser())
except ImportError:
    pass  # Docling not installed, use built-in parsers

# Automatic selection based on content type
parser = registry.get_parser(content, content_type="application/pdf")
sections = parser.parse(content)
```

## Questions for Review

1. **Registry vs explicit parser?** Should we use a registry for auto-detection, or require callers to explicitly pass parsers?
   - Proposal: Support both - registry for convenience, explicit for control

2. **Section metadata?** What metadata should `ParsedSection` capture?
   - Proposal: Start minimal (title, content, level, path), extend via `metadata` dict

3. **Error handling?** Should `can_parse()` be strict or permissive?
   - Proposal: Permissive - return True when uncertain, let `parse()` fail gracefully
