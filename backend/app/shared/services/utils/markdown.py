"""Markdown sanitizer service for fixing LLM-generated markdown issues.

This module provides functions to fix common markdown formatting issues
produced by LLMs, such as blank lines in tables and unicode bullets in lists.
"""

import re


def fix_tables(markdown: str) -> str:  # noqa: PLR0912 - complexity justified for markdown parsing
    r"""Remove blank lines between table rows while preserving table structure.

    LLMs often generate tables with blank lines between rows, which breaks
    GitHub Flavored Markdown (GFM) parsing. This function removes those blank
    lines while preserving code blocks and other markdown structures.

    Args:
        markdown: Raw markdown content with potential table issues

    Returns:
        Markdown with blank lines removed from table rows

    Examples:
        >>> text = "| A | B |\\n|---|---|\\n\\n| 1 | 2 |\\n\\n| 3 | 4 |"
        >>> fix_tables(text)
        '| A | B |\\n|---|---|\\n| 1 | 2 |\\n| 3 | 4 |'

    """
    # Split into lines for processing
    lines = markdown.split("\n")
    result_lines = []
    in_code_block = False
    last_was_table_row = False
    pending_blank_line = False

    for i, line in enumerate(lines):
        # Track code blocks (don't modify their content)
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            if pending_blank_line:
                result_lines.append("")
                pending_blank_line = False
            result_lines.append(line)
            last_was_table_row = False
            continue

        # Don't process inside code blocks
        if in_code_block:
            result_lines.append(line)
            continue

        # Check if this line is a table row (starts with |)
        is_table_row = bool(line.strip() and line.strip().startswith("|"))

        # Look ahead to find next non-blank line and check if it's a table row
        next_is_table = False
        for j in range(i + 1, len(lines)):
            next_line = lines[j]
            if next_line.strip():  # Found next non-blank line
                next_is_table = bool(next_line.strip().startswith("|"))
                break

        if is_table_row:
            # Add any pending blank line before starting a new table section
            if pending_blank_line and not last_was_table_row:
                result_lines.append("")
                pending_blank_line = False

            result_lines.append(line)
            last_was_table_row = True
        elif not line.strip():
            # Blank line
            if last_was_table_row and next_is_table:
                # Blank line between table rows - skip it (handles multiple blank lines)
                continue
            if last_was_table_row and not next_is_table:
                # Blank line after table ends - keep it for later
                if not pending_blank_line:  # Only set once to avoid multiple pending
                    pending_blank_line = True
                last_was_table_row = False
            else:
                # Regular blank line - keep it
                if pending_blank_line:
                    result_lines.append("")
                    pending_blank_line = False
                result_lines.append(line)
        else:
            # Non-table, non-blank line
            if pending_blank_line:
                result_lines.append("")
                pending_blank_line = False
            result_lines.append(line)
            last_was_table_row = False

    # Don't forget any pending blank line at the end
    if pending_blank_line:
        result_lines.append("")

    return "\n".join(result_lines)


def fix_lists(markdown: str) -> str:
    r"""Convert unicode bullets to proper markdown list syntax.

    LLMs sometimes use unicode bullet characters (•) instead of proper
    markdown list syntax (-). This function converts them while handling
    both line-start and inline bullets.

    Args:
        markdown: Raw markdown content with unicode bullets

    Returns:
        Markdown with unicode bullets replaced by proper list syntax

    Examples:
        >>> text = "• Item 1\\n• Item 2"
        >>> fix_lists(text)
        '- Item 1\\n- Item 2'
        >>> text = "Text • Item 1 • Item 2"
        >>> fix_lists(text)
        'Text\\n- Item 1\\n- Item 2'

    """
    # Split into lines for processing
    lines = markdown.split("\n")
    result_lines = []
    in_code_block = False

    for line in lines:
        # Track code blocks (don't modify their content)
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result_lines.append(line)
            continue

        # Don't process inside code blocks
        if in_code_block:
            result_lines.append(line)
            continue

        # Replace bullets in this line
        processed_line = line

        # First, check for inline bullets (e.g., "Text • Item1 • Item2" or "• Item1 • Item2")
        # Inline bullets have non-whitespace text before them (not just indentation)
        # Pattern: content (not just spaces) + space + bullet + space + more content
        if "•" in processed_line:
            # Only treat as inline if there's actual text content before the bullet
            # Not just whitespace (which would be indentation)
            inline_match = re.search(r"^(\s*)(\S.+?)\s+•\s+(.+)", processed_line)
            if inline_match:
                # This line has inline bullets (text before the bullet, not just indent)
                # Split the line on bullets
                parts = re.split(r"\s+•\s+", processed_line)
                if len(parts) > 1:
                    # Convert each part to a list item
                    for part in parts:
                        # Remove leading bullet if present at very start
                        cleaned_part = re.sub(r"^(\s*)•\s+", r"\1", part)
                        result_lines.append(f"- {cleaned_part}")
                    continue

        # Pattern: Bullet at start of line only (no inline bullets)
        # Match: "  • Item" or "• Item" (with optional leading whitespace)
        if re.match(r"^(\s*)•\s+", processed_line):
            processed_line = re.sub(r"^(\s*)•\s+", r"\1- ", processed_line)

        result_lines.append(processed_line)

    return "\n".join(result_lines)


def sanitize_markdown(markdown: str) -> str:
    r"""Apply all markdown sanitizers to fix LLM-generated formatting issues.

    This is the main entry point for markdown sanitization. It applies
    all available sanitizers in the correct order to fix common issues
    produced by LLMs.

    Args:
        markdown: Raw markdown content from LLM

    Returns:
        Sanitized markdown with formatting issues fixed

    Examples:
        >>> text = "| A | B |\\n|---|---|\\n\\n| 1 | 2 |\\n• Item"
        >>> result = sanitize_markdown(text)
        >>> "\\n\\n" not in result  # No blank lines in table
        True
        >>> "- Item" in result  # Bullets converted
        True

    """
    if not markdown or not isinstance(markdown, str):
        return markdown

    # Apply sanitizers in order
    result = fix_tables(markdown)
    return fix_lists(result)
