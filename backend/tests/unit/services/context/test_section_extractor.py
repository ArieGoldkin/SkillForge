"""Unit tests for SectionExtractor.

Tests content analysis for partial loading:
- Code block extraction
- Heading extraction
- Content metadata
"""

import pytest

from app.domains.analysis.services.context.section_extractor import SectionExtractor



@pytest.fixture
def extractor() -> SectionExtractor:
    """Create SectionExtractor instance."""
    return SectionExtractor()


class TestExtractCodeBlocks:
    """Tests for code block extraction."""

    def test_extract_single_code_block(self, extractor: SectionExtractor) -> None:
        """Should extract single code block."""
        content = """Some text before

```python
def hello():
    print("Hello")
```

Some text after
"""
        sections = extractor.extract(content)

        assert len(sections.code_blocks) == 1
        block = sections.code_blocks[0]
        assert block.language == "python"
        assert (
            content[block.start : block.end] == '```python\ndef hello():\n    print("Hello")\n```'
        )

    def test_extract_multiple_code_blocks(self, extractor: SectionExtractor) -> None:
        """Should extract multiple code blocks."""
        content = """
```javascript
console.log("JS");
```

Some text

```typescript
const x: number = 1;
```
"""
        sections = extractor.extract(content)

        assert len(sections.code_blocks) == 2
        assert sections.code_blocks[0].language == "javascript"
        assert sections.code_blocks[1].language == "typescript"

    def test_extract_code_block_no_language(self, extractor: SectionExtractor) -> None:
        """Should handle code block without language."""
        content = """```
plain code
```"""
        sections = extractor.extract(content)

        assert len(sections.code_blocks) == 1
        assert sections.code_blocks[0].language is None

    def test_no_code_blocks(self, extractor: SectionExtractor) -> None:
        """Should handle content without code blocks."""
        content = "Just plain text without any code."
        sections = extractor.extract(content)

        assert len(sections.code_blocks) == 0


class TestExtractHeadings:
    """Tests for heading extraction."""

    def test_extract_markdown_headings(self, extractor: SectionExtractor) -> None:
        """Should extract markdown headings."""
        content = """# Title

## Section 1

### Subsection 1.1

## Section 2
"""
        sections = extractor.extract(content)

        assert len(sections.headings) == 4
        assert sections.headings[0].level == 1
        assert sections.headings[0].text == "Title"
        assert sections.headings[1].level == 2
        assert sections.headings[1].text == "Section 1"
        assert sections.headings[2].level == 3
        assert sections.headings[2].text == "Subsection 1.1"

    def test_heading_with_formatting(self, extractor: SectionExtractor) -> None:
        """Should extract heading text without extra whitespace."""
        content = "## Heading with spaces  "
        sections = extractor.extract(content)

        assert len(sections.headings) == 1
        assert sections.headings[0].text == "Heading with spaces"

    def test_no_headings(self, extractor: SectionExtractor) -> None:
        """Should handle content without headings."""
        content = "Just plain text."
        sections = extractor.extract(content)

        assert len(sections.headings) == 0


class TestContentMetadata:
    """Tests for content metadata."""

    def test_word_count(self, extractor: SectionExtractor) -> None:
        """Should count words correctly."""
        content = "One two three four five."
        sections = extractor.extract(content)

        assert sections.word_count == 5

    def test_char_count(self, extractor: SectionExtractor) -> None:
        """Should count characters correctly."""
        content = "Hello World"
        sections = extractor.extract(content)

        assert sections.char_count == 11


class TestGetCodeBlocksText:
    """Tests for get_code_blocks_text method."""

    def test_get_code_blocks_text(self, extractor: SectionExtractor) -> None:
        """Should return concatenated code blocks."""
        content = """
```python
code1
```

```javascript
code2
```
"""
        result = extractor.get_code_blocks_text(content)

        assert "```python" in result
        assert "code1" in result
        assert "```javascript" in result
        assert "code2" in result

    def test_no_code_blocks_message(self, extractor: SectionExtractor) -> None:
        """Should return message when no code blocks."""
        content = "No code here"
        result = extractor.get_code_blocks_text(content)

        assert result == "No code blocks found in content."


class TestGetHeadingsOutline:
    """Tests for get_headings_outline method."""

    def test_get_headings_outline(self, extractor: SectionExtractor) -> None:
        """Should return formatted outline."""
        content = """# Title

## Section 1

### Subsection 1.1
"""
        result = extractor.get_headings_outline(content)

        assert "- Title" in result
        assert "  - Section 1" in result
        assert "    - Subsection 1.1" in result

    def test_no_headings_message(self, extractor: SectionExtractor) -> None:
        """Should return message when no headings."""
        content = "No headings here"
        result = extractor.get_headings_outline(content)

        assert result == "No headings found in content."
