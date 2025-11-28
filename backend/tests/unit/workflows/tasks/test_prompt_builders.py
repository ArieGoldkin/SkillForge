"""Unit tests for task prompt builders."""

from app.workflows.tasks.prompt_builders import build_synthesis_user_prompt


class TestBuildSynthesisUserPrompt:
    """Test build_synthesis_user_prompt function."""

    def test_build_synthesis_prompt_with_findings(self):
        """Test building synthesis prompt with formatted findings."""
        formatted_findings = "AGENT FINDINGS:\n\n--- TECH COMPARATOR ---\nFindings: {...}"

        result = build_synthesis_user_prompt(formatted_findings)

        assert "Analyze and synthesize the following agent findings" in result
        assert formatted_findings in result
        assert "Generate a cohesive synthesis" in result
        assert "executive summary is 2-3 sentences" in result
        assert "key findings are 3-7 items" in result

    def test_build_synthesis_prompt_with_empty_findings(self):
        """Test building synthesis prompt with empty findings."""
        formatted_findings = ""

        result = build_synthesis_user_prompt(formatted_findings)

        assert "Analyze and synthesize the following agent findings" in result
        assert formatted_findings in result
        assert "Generate a cohesive synthesis" in result

    def test_build_synthesis_prompt_structure(self):
        """Test synthesis prompt has correct structure."""
        formatted_findings = "Test findings"

        result = build_synthesis_user_prompt(formatted_findings)

        lines = result.split("\n")
        assert "Analyze and synthesize the following agent findings:" in lines[0]
        assert lines[1] == ""  # Blank line
        assert "Test findings" in lines[2]
        assert "Generate a cohesive synthesis" in result
        assert "executive summary" in result.lower()
        assert "key findings" in result.lower()

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
