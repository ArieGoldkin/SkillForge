"""Unit tests for proactive recall functions.

Issue #245: Agent Memory Access (RAG)
Tests the proactive context injection functionality.
"""

import uuid

from app.services.memory import MemorySnippet
from app.services.memory.proactive_recall import (
    format_memory_context,
    inject_proactive_context,
)


class TestFormatMemoryContext:
    """Tests for format_memory_context function."""

    def test_empty_snippets_returns_empty_string(self):
        """Test that empty list returns empty string."""
        result = format_memory_context([])
        assert result == ""

    def test_single_snippet_formatting(self):
        """Test formatting with single snippet."""
        snippets = [
            MemorySnippet(
                content="SQL injection prevention pattern",
                memory_type="vulnerability_pattern",
                relevance=0.85,
                source_id=str(uuid.uuid4()),
            )
        ]

        result = format_memory_context(snippets)

        assert "## Relevant Context from Past Analyses" in result
        assert "SQL injection prevention pattern" in result
        assert "[vulnerability_pattern]" in result
        assert "(relevance: 0.85)" in result
        assert "Use this context to inform your analysis" in result

    def test_multiple_snippets_numbered(self):
        """Test that multiple snippets are numbered correctly."""
        snippets = [
            MemorySnippet(
                content="First pattern",
                memory_type="vulnerability_pattern",
                relevance=0.90,
                source_id=str(uuid.uuid4()),
            ),
            MemorySnippet(
                content="Second practice",
                memory_type="best_practice",
                relevance=0.80,
                source_id=str(uuid.uuid4()),
            ),
            MemorySnippet(
                content="Third summary",
                memory_type="analysis_summary",
                relevance=0.75,
                source_id=str(uuid.uuid4()),
            ),
        ]

        result = format_memory_context(snippets)

        assert "1. [vulnerability_pattern]" in result
        assert "2. [best_practice]" in result
        assert "3. [analysis_summary]" in result
        assert "First pattern" in result
        assert "Second practice" in result
        assert "Third summary" in result

    def test_includes_header_and_footer(self):
        """Test that header and footer instructions are included."""
        snippets = [
            MemorySnippet(
                content="Test content",
                memory_type="best_practice",
                relevance=0.8,
                source_id=str(uuid.uuid4()),
            )
        ]

        result = format_memory_context(snippets)

        # Header
        assert "## Relevant Context from Past Analyses" in result
        assert "The following information from past analyses may be relevant" in result

        # Footer
        assert "Use this context to inform your analysis where applicable" in result


class TestInjectProactiveContext:
    """Tests for inject_proactive_context function."""

    def test_empty_context_returns_original_prompt(self):
        """Test that empty context returns original prompt unchanged."""
        prompt = "Analyze this code for security issues."
        result = inject_proactive_context(prompt, "")

        assert result == prompt

    def test_context_prepended_with_separator(self):
        """Test that context is prepended with separator."""
        prompt = "Analyze this code."
        context = "## Relevant Context\n\nSome memory content."

        result = inject_proactive_context(prompt, context)

        assert result.startswith(context)
        assert "\n---\n\n" in result
        assert result.endswith(prompt)

    def test_full_injection_format(self):
        """Test the complete injection format."""
        prompt = "Original prompt here."
        context = "Memory context."

        result = inject_proactive_context(prompt, context)

        expected = "Memory context.\n---\n\nOriginal prompt here."
        assert result == expected


class TestIntegration:
    """Integration tests for proactive recall flow."""

    def test_format_then_inject_flow(self):
        """Test the typical format -> inject workflow."""
        # Create snippets
        snippets = [
            MemorySnippet(
                content="Always validate user input before database queries.",
                memory_type="best_practice",
                relevance=0.92,
                source_id=str(uuid.uuid4()),
            ),
        ]

        # Format to context
        context = format_memory_context(snippets)
        assert context != ""

        # Inject into prompt
        original_prompt = "Content Type: article\n\nContent:\nReact authentication..."
        enhanced_prompt = inject_proactive_context(original_prompt, context)

        # Verify structure
        assert enhanced_prompt.startswith("## Relevant Context")
        assert "---" in enhanced_prompt
        assert enhanced_prompt.endswith(original_prompt)

    def test_no_snippets_flow(self):
        """Test that no snippets results in unchanged prompt."""
        snippets: list[MemorySnippet] = []
        context = format_memory_context(snippets)
        original_prompt = "Original prompt."

        result = inject_proactive_context(original_prompt, context)

        assert result == original_prompt
