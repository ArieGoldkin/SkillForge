"""Unit tests for task prompt builders.

Note: Issue #304 redesigned the prompts for triple-purpose artifacts.
Tests updated to match the new prompt format that explicitly mentions
AI coding assistants, tutor system, and human readers.
"""

import pytest

from app.domains.analysis.workflows.tasks.prompt_builders import build_synthesis_user_prompt


@pytest.mark.unit
class TestBuildSynthesisUserPrompt:
    """Test build_synthesis_user_prompt function."""

    def test_build_synthesis_prompt_with_findings(self):
        """Test building synthesis prompt with formatted findings.

        Issue #304: Prompt redesigned for triple-purpose artifacts.
        """
        formatted_findings = "AGENT FINDINGS:\n\n--- TECH COMPARATOR ---\nFindings: {...}"

        result = build_synthesis_user_prompt(formatted_findings)

        # Check for triple-purpose artifact prompt (Issue #304 redesign)
        assert "Analyze and synthesize the following agent findings" in result
        assert formatted_findings in result
        assert "TRIPLE-PURPOSE artifact" in result
        assert "executive_summary" in result  # Required section
        assert "key_findings" in result  # Required section

    def test_build_synthesis_prompt_with_empty_findings(self):
        """Test building synthesis prompt with empty findings.

        Issue #304: Prompt redesigned for triple-purpose artifacts.
        """
        formatted_findings = ""

        result = build_synthesis_user_prompt(formatted_findings)

        assert "Analyze and synthesize the following agent findings" in result
        assert "TRIPLE-PURPOSE artifact" in result
        assert "Generate the complete artifact now" in result

    def test_build_synthesis_prompt_structure(self):
        """Test synthesis prompt has correct structure.

        Issue #304: Prompt redesigned for triple-purpose artifacts with
        sections for AI coding assistants, tutor system, and human readers.
        """
        formatted_findings = "Test findings"

        result = build_synthesis_user_prompt(formatted_findings)

        lines = result.split("\n")
        # First line mentions triple-purpose artifact
        assert "TRIPLE-PURPOSE artifact" in lines[0]
        assert "Test findings" in result
        # Check all three audience sections are present
        assert "AI Coding Assistants" in result
        assert "Tutor System" in result
        assert "Human Readers" in result
        assert "executive_summary" in result
        assert "key_findings" in result

    def test_build_synthesis_prompt_with_multiline_findings(self):
        """Test building synthesis prompt with multiline findings."""
        formatted_findings = """AGENT FINDINGS:

--- TECH COMPARATOR ---
Confidence: 0.85
Findings: {
  "primary_tech": "LangGraph"
}

--- SECURITY AUDITOR ---
Confidence: 0.90
Findings: {
  "risks": []
}"""

        result = build_synthesis_user_prompt(formatted_findings)

        assert "Analyze and synthesize the following agent findings" in result
        assert "TECH COMPARATOR" in result
        assert "SECURITY AUDITOR" in result
        assert "0.85" in result
        assert "0.90" in result
        assert "LangGraph" in result
