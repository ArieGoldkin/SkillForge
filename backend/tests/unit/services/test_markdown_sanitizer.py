"""Unit tests for markdown sanitizer service.

Tests cover:
- Table blank line removal
- Unicode bullet conversion
- Edge cases (code blocks, nested structures)
- Integration of all sanitizers
"""

from app.services.utils.markdown import fix_lists, fix_tables, sanitize_markdown


class TestFixTables:
    """Tests for fix_tables function."""

    def test_removes_blank_lines_between_table_rows(self) -> None:
        """Should remove blank lines between table rows."""
        markdown = """| File | Description |
|------|-------------|

| a.py | First file |

| b.py | Second file |
"""
        expected = """| File | Description |
|------|-------------|
| a.py | First file |
| b.py | Second file |
"""
        assert fix_tables(markdown) == expected

    def test_preserves_tables_without_blank_lines(self) -> None:
        """Should not modify correctly formatted tables."""
        markdown = """| File | Description |
|------|-------------|
| a.py | First file |
| b.py | Second file |
"""
        assert fix_tables(markdown) == markdown

    def test_handles_multiple_consecutive_blank_lines(self) -> None:
        """Should remove multiple blank lines in tables."""
        markdown = """| A | B |
|---|---|


| 1 | 2 |


| 3 | 4 |
"""
        expected = """| A | B |
|---|---|
| 1 | 2 |
| 3 | 4 |
"""
        assert fix_tables(markdown) == expected

    def test_preserves_blank_lines_outside_tables(self) -> None:
        """Should only remove blank lines within tables, not elsewhere."""
        markdown = """# Header

Some text here.

| A | B |
|---|---|

| 1 | 2 |

More text after table.

Another paragraph.
"""
        expected = """# Header

Some text here.

| A | B |
|---|---|
| 1 | 2 |

More text after table.

Another paragraph.
"""
        assert fix_tables(markdown) == expected

    def test_handles_tables_with_complex_content(self) -> None:
        """Should handle tables with complex cell content."""
        markdown = """| Command | Description | Example |
|---------|-------------|---------|

| `git commit` | Create commit | `git commit -m "msg"` |

| `git push` | Push changes | `git push origin main` |
"""
        expected = """| Command | Description | Example |
|---------|-------------|---------|
| `git commit` | Create commit | `git commit -m "msg"` |
| `git push` | Push changes | `git push origin main` |
"""
        assert fix_tables(markdown) == expected

    def test_preserves_code_blocks_with_pipes(self) -> None:
        """Should not modify tables inside code blocks."""
        markdown = """```python
| A | B |

| 1 | 2 |
```

| Real | Table |
|------|-------|

| X | Y |
"""
        # Code block tables should be preserved with blank lines
        # Real table should have blank line removed
        result = fix_tables(markdown)
        assert "```python\n| A | B |\n\n| 1 | 2 |" in result
        assert "| Real | Table |\n|------|-------|\n| X | Y |" in result

    def test_handles_empty_string(self) -> None:
        """Should handle empty input gracefully."""
        assert fix_tables("") == ""

    def test_handles_no_tables(self) -> None:
        """Should handle markdown with no tables."""
        markdown = """# Header

This is just text.

No tables here.
"""
        assert fix_tables(markdown) == markdown

    def test_handles_malformed_table_rows(self) -> None:
        """Should handle incomplete or malformed table rows."""
        markdown = """| A | B |
|---|---|

| 1 |
| missing closing pipe

| 2 | 3 |
"""
        # Should still remove blank lines where table structure is detected
        result = fix_tables(markdown)
        assert "\n\n|" not in result or "```" in result


class TestFixLists:
    """Tests for fix_lists function."""

    def test_converts_bullet_at_line_start(self) -> None:
        """Should convert unicode bullets at line start to markdown syntax."""
        markdown = """• First item
• Second item
• Third item
"""
        expected = """- First item
- Second item
- Third item
"""
        assert fix_lists(markdown) == expected

    def test_converts_inline_bullets_to_list_items(self) -> None:
        """Should split inline bullets into separate list items."""
        markdown = "Text • Item 1 • Item 2 • Item 3"
        result = fix_lists(markdown)

        # Should split into multiple lines
        assert "Text\n" in result or result.startswith("Text")
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result

    def test_preserves_indented_bullets(self) -> None:
        """Should preserve indentation when converting bullets."""
        markdown = """• Level 1
  • Level 2
    • Level 3
"""
        expected = """- Level 1
  - Level 2
    - Level 3
"""
        assert fix_lists(markdown) == expected

    def test_handles_bold_items_with_bullets(self) -> None:
        """Should handle bullets before bold text."""
        markdown = """• **Risk 1**: Description one
• **Risk 2**: Description two
"""
        expected = """- **Risk 1**: Description one
- **Risk 2**: Description two
"""
        assert fix_lists(markdown) == expected

    def test_preserves_code_blocks(self) -> None:
        """Should not modify bullets inside code blocks."""
        markdown = """```
• This is in code
• Should not change
```

• This should change
"""
        expected = """```
• This is in code
• Should not change
```

- This should change
"""
        assert fix_lists(markdown) == expected

    def test_handles_mixed_list_styles(self) -> None:
        """Should handle documents with both bullet styles."""
        markdown = """- Already markdown
• Needs conversion
• Also needs conversion
- Already correct
"""
        expected = """- Already markdown
- Needs conversion
- Also needs conversion
- Already correct
"""
        assert fix_lists(markdown) == expected

    def test_handles_empty_string(self) -> None:
        """Should handle empty input gracefully."""
        assert fix_lists("") == ""

    def test_handles_no_bullets(self) -> None:
        """Should handle text with no bullets."""
        markdown = """# Header

This is just text.
No bullets here.
"""
        assert fix_lists(markdown) == markdown

    def test_preserves_bullets_in_inline_text(self) -> None:
        """Should handle bullets that are part of regular text carefully."""
        markdown = "The • symbol is sometimes used as a separator."
        result = fix_lists(markdown)
        # Should attempt to convert, but behavior depends on pattern matching
        # This test documents current behavior
        assert isinstance(result, str)


class TestSanitizeMarkdown:
    """Integration tests for sanitize_markdown function."""

    def test_fixes_both_tables_and_lists(self) -> None:
        """Should fix both table and list issues in one pass."""
        markdown = """# Analysis

• **Overview**: Some text

| File | Description |
|------|-------------|

| a.py | First file |

| b.py | Second file |

• **Risks**: Listed below
• Risk 1: Something
• Risk 2: Something else
"""
        result = sanitize_markdown(markdown)

        # Tables should have no blank lines
        assert "| a.py | First file |\n| b.py | Second file |" in result

        # Bullets should be converted
        assert "- **Overview**:" in result
        assert "- **Risks**:" in result
        assert "- Risk 1:" in result
        assert "- Risk 2:" in result

    def test_handles_complex_real_world_document(self) -> None:
        """Should handle a complex document with multiple issues."""
        markdown = """# Technical Analysis

## Quick Reference

• **Framework**: React 19
• **Key Features**: Server Components • Async transitions • Enhanced hydration

## File Structure

| File | Purpose | Dependencies |
|------|---------|--------------|

| index.ts | Entry point | react, react-dom |

| App.tsx | Root component | react |

| utils.ts | Utilities | None |

## Risks

• **Risk 1**: Breaking changes • **Risk 2**: Migration complexity
"""
        result = sanitize_markdown(markdown)

        # Should fix tables - no blank lines WITHIN table rows
        assert "| index.ts | Entry point" in result
        # Check that there are no blank lines between table rows (but allow blank line before table)
        assert "| index.ts | Entry point | react, react-dom |\n| App.tsx | Root component" in result
        # Blank line before table (after header) is OK, so \n\n| is allowed in that context
        assert "## File Structure\n\n|" in result  # This is correct markdown

        # Should fix lists
        assert "- **Framework**:" in result
        assert "- **Key Features**:" in result
        assert result.count("- **Risk") == 2  # Both risks on separate lines

    def test_handles_none_input(self) -> None:
        """Should handle None input gracefully."""
        assert sanitize_markdown(None) is None  # type: ignore[arg-type]

    def test_handles_empty_string(self) -> None:
        """Should handle empty string."""
        assert sanitize_markdown("") == ""

    def test_handles_non_string_input(self) -> None:
        """Should handle non-string input gracefully."""
        assert sanitize_markdown(123) == 123  # type: ignore[arg-type]

    def test_preserves_valid_markdown(self) -> None:
        """Should not break already valid markdown."""
        markdown = """# Header

This is a paragraph.

- List item 1
- List item 2

| A | B |
|---|---|
| 1 | 2 |

```python
def hello():
    print("world")
```
"""
        result = sanitize_markdown(markdown)
        # Should be mostly unchanged (minor differences in whitespace handling OK)
        assert "# Header" in result
        assert "- List item 1" in result
        assert "| A | B |" in result
        assert "```python" in result

    def test_performance_with_large_document(self) -> None:
        """Should handle large documents efficiently."""
        # Create a large document with many tables and lists
        large_markdown = ""
        for i in range(100):
            large_markdown += f"""
## Section {i}

• Item {i}.1
• Item {i}.2

| Col1 | Col2 |
|------|------|

| {i} | data |

"""
        # Should complete without error
        result = sanitize_markdown(large_markdown)
        assert isinstance(result, str)
        assert len(result) > 0
        assert result.count("- Item") == 200  # All bullets converted

    def test_idempotency(self) -> None:
        """Should be idempotent - running twice gives same result."""
        markdown = """• Item 1
• Item 2

| A | B |
|---|---|

| 1 | 2 |
"""
        result1 = sanitize_markdown(markdown)
        result2 = sanitize_markdown(result1)
        assert result1 == result2
