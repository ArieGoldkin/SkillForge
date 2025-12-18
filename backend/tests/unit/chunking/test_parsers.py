"""Unit tests for pluggable content parsers (Issue #222).

Tests cover:
- ParsedSection dataclass
- TextParser (default paragraph splitter)
- MarkdownParser (header extraction and hierarchy)
- HTMLParser (semantic block extraction)
- CodeParser (function/class boundary detection)
- ParserRegistry (parser discovery and selection)

Reference: docs/issues/222-pluggable-parsers/README.md
"""

from app.shared.services.chunking.parsers import (
    CodeParser,
    HTMLParser,
    MarkdownParser,
    ParsedSection,
    ParserRegistry,
    TextParser,
)

# =============================================================================
# ParsedSection Tests
# =============================================================================


def test_parsed_section_defaults():
    """ParsedSection should have sensible defaults for optional fields."""
    section = ParsedSection(title="Intro", content="Hello world")
    assert section.title == "Intro"
    assert section.content == "Hello world"
    assert section.level == 0
    assert section.path == []
    assert section.metadata == {}


def test_parsed_section_with_metadata():
    """ParsedSection should accept custom metadata."""
    section = ParsedSection(
        title="Section 1",
        content="Content here",
        level=2,
        path=["Chapter 1", "Section 1"],
        metadata={"source": "test", "line": 42},
    )
    assert section.level == 2
    assert section.path == ["Chapter 1", "Section 1"]
    assert section.metadata == {"source": "test", "line": 42}


# =============================================================================
# TextParser Tests
# =============================================================================


def test_text_parser_splits_paragraphs():
    """TextParser should split on double newlines like current behavior."""
    parser = TextParser()
    sections = parser.parse("Para 1\n\nPara 2\n\nPara 3")

    assert len(sections) == 3
    assert sections[0].content == "Para 1"
    assert sections[1].content == "Para 2"
    assert sections[2].content == "Para 3"
    assert all(s.title is None for s in sections)
    assert all(s.level == 0 for s in sections)
    assert all(s.path == ["root"] for s in sections)


def test_text_parser_empty_content():
    """TextParser should handle empty content gracefully."""
    parser = TextParser()
    sections = parser.parse("")
    assert sections == []


def test_text_parser_single_paragraph():
    """TextParser should handle single paragraph without splits."""
    parser = TextParser()
    sections = parser.parse("Single paragraph with no splits.")

    assert len(sections) == 1
    assert sections[0].content == "Single paragraph with no splits."


def test_text_parser_can_parse_anything():
    """TextParser should accept any content (default fallback)."""
    parser = TextParser()
    assert parser.can_parse("any content") is True
    assert parser.can_parse("", "text/html") is True
    assert parser.can_parse("# Markdown", "text/markdown") is True


# =============================================================================
# MarkdownParser Tests
# =============================================================================


def test_markdown_parser_extracts_headers():
    """MarkdownParser should split by headers and extract titles."""
    parser = MarkdownParser()
    content = """# Heading 1
Content under H1.

## Heading 2
Content under H2.

### Heading 3
Content under H3."""

    sections = parser.parse(content)

    assert len(sections) == 3
    assert sections[0].title == "Heading 1"
    assert sections[0].level == 1
    assert "Content under H1." in sections[0].content

    assert sections[1].title == "Heading 2"
    assert sections[1].level == 2
    assert "Content under H2." in sections[1].content

    assert sections[2].title == "Heading 3"
    assert sections[2].level == 3
    assert "Content under H3." in sections[2].content


def test_markdown_parser_builds_path_hierarchy():
    """MarkdownParser should track hierarchical paths."""
    parser = MarkdownParser()
    content = """# Chapter 1
Intro.

## Section 1.1
Details.

### Subsection 1.1.1
More details.

## Section 1.2
Other details."""

    sections = parser.parse(content)

    # Chapter 1 (H1)
    assert sections[0].path == ["Chapter 1"]

    # Section 1.1 (H2 under H1)
    assert sections[1].path == ["Chapter 1", "Section 1.1"]

    # Subsection 1.1.1 (H3 under H2)
    assert sections[2].path == ["Chapter 1", "Section 1.1", "Subsection 1.1.1"]

    # Section 1.2 (H2 under H1, resets H3)
    assert sections[3].path == ["Chapter 1", "Section 1.2"]


def test_markdown_parser_protects_code_blocks():
    """MarkdownParser should not split inside code blocks."""
    parser = MarkdownParser()
    content = """# Code Example
Here's some code:

```python
# This is a comment
def function():
    pass
```

End of code."""

    sections = parser.parse(content)

    assert len(sections) == 1
    assert "```python" in sections[0].content
    assert "def function():" in sections[0].content
    assert "```" in sections[0].content


def test_markdown_parser_header_metadata():
    """MarkdownParser should include LangChain-style header metadata."""
    parser = MarkdownParser()
    content = """# Top Level
Content.

## Sub Level
More content."""

    sections = parser.parse(content)

    # First section metadata
    assert sections[0].metadata == {"header_1": "Top Level"}

    # Second section metadata
    assert sections[1].metadata == {
        "header_1": "Top Level",
        "header_2": "Sub Level",
    }


def test_markdown_parser_no_headers_fallback():
    """MarkdownParser should return single section if no headers found."""
    parser = MarkdownParser()
    content = "Just plain text with no headers at all."

    sections = parser.parse(content)

    assert len(sections) == 1
    assert sections[0].title is None
    assert sections[0].content == content
    assert sections[0].level == 0
    assert sections[0].path == ["root"]


def test_markdown_parser_can_parse_detects_headers():
    """MarkdownParser should detect markdown content by headers."""
    parser = MarkdownParser()

    # Should detect markdown
    assert parser.can_parse("# Heading") is True
    assert parser.can_parse("## Another heading\nText") is True
    assert parser.can_parse("Some text\n### H3", "text/markdown") is True

    # Should not detect plain text without headers
    assert parser.can_parse("Plain text with no markdown") is False
    assert parser.can_parse("Plain text", "text/plain") is False


# =============================================================================
# HTMLParser Tests
# =============================================================================


def test_html_parser_extracts_paragraphs():
    """HTMLParser should extract <p> tags as sections."""
    parser = HTMLParser()
    content = """
    <html>
        <body>
            <p>First paragraph.</p>
            <p>Second paragraph.</p>
        </body>
    </html>
    """

    sections = parser.parse(content)

    # Should have at least 2 paragraph sections
    paragraph_sections = [s for s in sections if s.content and "paragraph" in s.content.lower()]
    assert len(paragraph_sections) >= 2


def test_html_parser_extracts_headings():
    """HTMLParser should extract headings and track hierarchy."""
    parser = HTMLParser()
    content = """
    <html>
        <body>
            <h1>Main Title</h1>
            <p>Content under main title.</p>
            <h2>Subtitle</h2>
            <p>Content under subtitle.</p>
        </body>
    </html>
    """

    sections = parser.parse(content)

    # Find heading sections
    h1_sections = [s for s in sections if s.level == 1]
    h2_sections = [s for s in sections if s.level == 2]

    assert len(h1_sections) >= 1
    assert len(h2_sections) >= 1
    assert any("Main Title" in s.title for s in h1_sections if s.title)


def test_html_parser_skips_script_style():
    """HTMLParser should skip <script> and <style> tags."""
    parser = HTMLParser()
    content = """
    <html>
        <head>
            <style>body { color: red; }</style>
            <script>console.log('test');</script>
        </head>
        <body>
            <p>Visible content.</p>
        </body>
    </html>
    """

    sections = parser.parse(content)

    # Should not include script/style content
    all_content = " ".join(s.content for s in sections)
    assert "console.log" not in all_content
    assert "color: red" not in all_content
    assert "Visible content" in all_content


def test_html_parser_malformed_html_fallback():
    """HTMLParser should fallback gracefully for malformed HTML."""
    parser = HTMLParser()
    content = "<html><p>Broken <tag> no closing"

    sections = parser.parse(content)

    # Should return at least one section (fallback)
    assert len(sections) >= 1
    assert sections[0].path == ["root"]


def test_html_parser_can_parse_detects_tags():
    """HTMLParser should detect HTML by tags."""
    parser = HTMLParser()

    # Should detect HTML
    assert parser.can_parse("<html><body></body></html>") is True
    assert parser.can_parse("<p>Text</p>", "text/html") is True
    assert parser.can_parse("Text with <div>tag</div>") is True

    # Should not detect plain text
    assert parser.can_parse("Plain text with no tags") is False


# =============================================================================
# CodeParser Tests
# =============================================================================


def test_code_parser_python_functions():
    """CodeParser should extract Python functions as sections."""
    parser = CodeParser()
    content = """def function_one():
    pass

def function_two():
    return True

def function_three():
    print("test")
"""

    sections = parser.parse(content, "python")

    assert len(sections) >= 3
    assert any("function_one" in s.title for s in sections if s.title)
    assert any("function_two" in s.title for s in sections if s.title)
    assert any("function_three" in s.title for s in sections if s.title)


def test_code_parser_python_classes():
    """CodeParser should extract Python classes as sections."""
    parser = CodeParser()
    content = """class MyClass:
    def method(self):
        pass

class AnotherClass:
    pass
"""

    sections = parser.parse(content, "python")

    assert len(sections) >= 2
    assert any("MyClass" in s.title for s in sections if s.title)
    assert any("AnotherClass" in s.title for s in sections if s.title)

    # Classes should have level 1, methods level 2 (if detected separately)
    class_sections = [s for s in sections if "class" in s.metadata.get("kind", "").lower()]
    assert any(s.level == 1 for s in class_sections)


def test_code_parser_javascript_functions():
    """CodeParser should extract JavaScript functions."""
    parser = CodeParser()
    content = """function myFunction() {
    return true;
}

const arrowFunc = () => {
    console.log('test');
};

export function exportedFunc() {
    return 42;
}
"""

    sections = parser.parse(content, "javascript")

    # Should detect at least the standard functions
    assert len(sections) >= 2
    assert any("myFunction" in s.title or "exportedFunc" in s.title for s in sections if s.title)


def test_code_parser_line_chunking_fallback():
    """CodeParser should fall back to line chunking for unstructured code."""
    parser = CodeParser(chunk_lines=5, chunk_lines_overlap=2)
    # Plain text without clear function/class boundaries
    content = "\n".join([f"Line {i}" for i in range(20)])

    sections = parser.parse(content)

    # Should create multiple chunks
    assert len(sections) > 1

    # Check metadata for line tracking
    assert "line_start" in sections[0].metadata
    assert "line_end" in sections[0].metadata


def test_code_parser_respects_max_chars():
    """CodeParser should truncate sections exceeding max_chars."""
    parser = CodeParser(max_chars=50)
    content = """def very_long_function():
    # This function has a very long body that exceeds the max_chars limit
    # and should be truncated to fit the constraint
    print("line 1")
    print("line 2")
    print("line 3")
    print("line 4")
    print("line 5")
"""

    sections = parser.parse(content, "python")

    assert len(sections) >= 1
    # Content should be truncated
    # max_chars (50) + truncation marker ("# ... truncated" = 16 chars) = ~66
    assert len(sections[0].content) <= 70  # Allow buffer for truncation marker


def test_code_parser_can_parse():
    """CodeParser should detect code by language or heuristics."""
    parser = CodeParser()

    # Should detect Python
    assert parser.can_parse("def function():\n    pass", "python") is True
    assert parser.can_parse("class MyClass:\n    pass") is True

    # Should detect JavaScript
    assert parser.can_parse("function test() {}", "javascript") is True
    assert parser.can_parse("const x = () => {}") is True

    # Should detect other languages
    assert parser.can_parse("func main() {}", "go") is True
    assert parser.can_parse("fn main() { let mut x = 5; }", "rust") is True

    # Should not detect plain text
    assert parser.can_parse("Just plain text with no code") is False


# =============================================================================
# ParserRegistry Tests
# =============================================================================


def test_registry_default_parser():
    """ParserRegistry should return default TextParser when no match."""
    registry = ParserRegistry()

    parser = registry.get_parser("Plain text with no special format")

    assert isinstance(parser, TextParser)


def test_registry_register_and_get():
    """ParserRegistry should register and retrieve parsers by content type."""
    registry = ParserRegistry()

    markdown_parser = MarkdownParser()
    registry.register(markdown_parser)

    # Should match by content type
    parser = registry.get_parser("# Heading", "text/markdown")
    assert isinstance(parser, MarkdownParser)

    parser = registry.get_parser("Some text", "md")
    assert isinstance(parser, MarkdownParser)


def test_registry_content_type_matching():
    """ParserRegistry should prioritize content_type over can_parse()."""
    registry = ParserRegistry()

    registry.register(MarkdownParser())
    registry.register(HTMLParser())

    # Explicit content_type should take priority
    parser = registry.get_parser("<p>Text</p>", "text/html")
    assert isinstance(parser, HTMLParser)

    parser = registry.get_parser("# Heading", "text/markdown")
    assert isinstance(parser, MarkdownParser)


def test_registry_can_parse_fallback():
    """ParserRegistry should use can_parse() when content_type not provided."""
    registry = ParserRegistry()

    registry.register(MarkdownParser())
    registry.register(HTMLParser())
    registry.register(CodeParser())

    # Should detect markdown by content
    parser = registry.get_parser("# Markdown Heading")
    assert isinstance(parser, MarkdownParser)

    # Should detect HTML by content
    parser = registry.get_parser("<html><body><p>Text</p></body></html>")
    assert isinstance(parser, HTMLParser)

    # Should detect code by content
    parser = registry.get_parser("def function():\n    pass")
    assert isinstance(parser, CodeParser)

    # Should fall back to TextParser for unknown content
    parser = registry.get_parser("Plain text with no special markers")
    assert isinstance(parser, TextParser)


# =============================================================================
# Edge Cases and Integration
# =============================================================================


def test_empty_sections_filtered():
    """Parsers should not return empty sections."""
    parser = TextParser()
    content = "\n\n\n\n"  # Only whitespace

    sections = parser.parse(content)

    assert sections == []


def test_markdown_mixed_heading_levels():
    """MarkdownParser should handle non-sequential heading levels."""
    parser = MarkdownParser()
    content = """# H1
Content.

### H3 (skipping H2)
More content.

## H2 (back to H2)
Final content."""

    sections = parser.parse(content)

    assert len(sections) == 3
    assert sections[0].level == 1
    assert sections[1].level == 3
    assert sections[2].level == 2

    # Path should track hierarchy correctly
    assert sections[1].path == ["H1", "H3 (skipping H2)"]
    assert sections[2].path == ["H1", "H2 (back to H2)"]


def test_html_nested_tags():
    """HTMLParser should handle nested semantic tags."""
    parser = HTMLParser()
    content = """
    <html>
        <body>
            <section>
                <h2>Section Title</h2>
                <article>
                    <p>Article paragraph.</p>
                </article>
            </section>
        </body>
    </html>
    """

    sections = parser.parse(content)

    # Should extract semantic content
    assert len(sections) > 0


def test_code_parser_language_detection():
    """CodeParser should detect language from heuristics."""
    parser = CodeParser()

    # Python heuristics
    python_code = """import os
def main():
    pass
"""
    sections = parser.parse(python_code)
    assert any(
        "python" in s.metadata.get("language", "") for s in sections if s.metadata.get("language")
    )

    # JavaScript heuristics
    js_code = """const x = 5;
function test() {
    return x;
}
"""
    sections = parser.parse(js_code)
    assert any(
        "javascript" in s.metadata.get("language", "")
        for s in sections
        if s.metadata.get("language")
    )
