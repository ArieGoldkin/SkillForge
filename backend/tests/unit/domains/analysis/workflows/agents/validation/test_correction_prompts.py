"""Unit tests for correction prompts module.

Tests Issue #507: Agent self-correction prompt generation.
"""

from app.domains.analysis.workflows.agents.validation.correction_prompts import (
    AGENT_CORRECTION_TEMPLATES,
    build_correction_context,
    build_correction_prompt,
    get_agent_specific_guidance,
)


class TestBuildCorrectionPrompt:
    """Test build_correction_prompt() function."""

    def test_regular_format_basic(self):
        """Test regular prompt format with basic inputs."""
        issues = ["Only 2 insights, need >= 3"]
        hints = ["Provide at least 3 unique insights"]
        attempt = 2

        result = build_correction_prompt(issues, hints, attempt, compact=False)

        # Check structure
        assert "## Self-Correction Required (Attempt 2)" in result
        assert "### Issues Found:" in result
        assert "### Correction Guidelines:" in result
        assert "### Important:" in result

        # Check content
        assert "- Only 2 insights, need >= 3" in result
        assert "- Provide at least 3 unique insights" in result
        assert "Address ALL issues listed above" in result
        assert "Do NOT use placeholder text" in result

    def test_regular_format_multiple_issues(self):
        """Test regular format with multiple issues and hints."""
        issues = [
            "Only 2 insights, need >= 3",
            "Description too short: 20 chars",
            "Missing specific examples",
        ]
        hints = [
            "Provide at least 3 unique insights",
            "Write detailed descriptions (100+ chars)",
            "Include concrete examples from source",
        ]
        attempt = 3

        result = build_correction_prompt(issues, hints, attempt, compact=False)

        # All issues present
        assert "- Only 2 insights, need >= 3" in result
        assert "- Description too short: 20 chars" in result
        assert "- Missing specific examples" in result

        # All hints present
        assert "- Provide at least 3 unique insights" in result
        assert "- Write detailed descriptions (100+ chars)" in result
        assert "- Include concrete examples from source" in result

        # Correct attempt number
        assert "Attempt 3" in result

    def test_compact_format_basic(self):
        """Test compact prompt format saves tokens."""
        issues = ["Only 2 insights, need >= 3"]
        hints = ["Provide at least 3 unique insights"]
        attempt = 2

        result = build_correction_prompt(issues, hints, attempt, compact=True)

        # Check compact structure
        assert "## Fix Required (Attempt 2)" in result
        assert "Issues:" in result
        assert "Fix by:" in result

        # Issues/hints should be semicolon-separated, not bulleted
        assert "Only 2 insights, need >= 3" in result
        assert "Provide at least 3 unique insights" in result
        assert "Regenerate with fixes" in result

        # Should NOT have verbose sections
        assert "### Issues Found:" not in result
        assert "### Correction Guidelines:" not in result
        assert "### Important:" not in result

    def test_compact_format_multiple_items(self):
        """Test compact format joins multiple items with semicolons."""
        issues = ["Issue 1", "Issue 2", "Issue 3"]
        hints = ["Hint A", "Hint B"]
        attempt = 1

        result = build_correction_prompt(issues, hints, attempt, compact=True)

        # Check semicolon separation
        assert "Issue 1; Issue 2; Issue 3" in result
        assert "Hint A; Hint B" in result

    def test_different_attempt_numbers(self):
        """Test prompt reflects correct attempt number."""
        issues = ["Test issue"]
        hints = ["Test hint"]

        for attempt in [1, 2, 3, 5]:
            result_regular = build_correction_prompt(issues, hints, attempt, compact=False)
            result_compact = build_correction_prompt(issues, hints, attempt, compact=True)

            assert f"Attempt {attempt}" in result_regular
            assert f"Attempt {attempt}" in result_compact

    def test_empty_lists(self):
        """Test handling of empty issues/hints lists."""
        # Should still generate valid prompt structure
        result = build_correction_prompt([], [], 1, compact=False)

        assert "## Self-Correction Required" in result
        assert "### Issues Found:" in result
        assert "### Correction Guidelines:" in result

    def test_special_characters_in_issues(self):
        """Test issues with special characters are preserved."""
        issues = ['Field "title" is required', "Value must be >= 3", "Use 'quote' format"]
        hints = ["Check JSON schema", "Validate input"]

        result = build_correction_prompt(issues, hints, 1, compact=False)

        # Special characters preserved
        assert 'Field "title" is required' in result
        assert "Value must be >= 3" in result
        assert "Use 'quote' format" in result


class TestBuildCorrectionContext:
    """Test build_correction_context() function."""

    def test_basic_context_structure(self):
        """Test context dict has all required keys."""
        original = {"key_insights": [], "summary": "test"}
        issues = ["Issue 1", "Issue 2"]
        agent_type = "key_insights"

        result = build_correction_context(original, issues, agent_type)

        # Check required keys
        assert "agent_type" in result
        assert "issues_count" in result
        assert "issues" in result
        assert "output_keys" in result
        assert "correction_triggered" in result

        # Check values
        assert result["agent_type"] == "key_insights"
        assert result["issues_count"] == 2
        assert result["issues"] == ["Issue 1", "Issue 2"]
        assert result["output_keys"] == ["key_insights", "summary"]
        assert result["correction_triggered"] is True

    def test_limits_issues_to_five(self):
        """Test context limits issues list to first 5."""
        original = {}
        issues = [f"Issue {i}" for i in range(10)]
        agent_type = "test_agent"

        result = build_correction_context(original, issues, agent_type)

        # Count should be full 10
        assert result["issues_count"] == 10

        # But issues list should only have first 5
        assert len(result["issues"]) == 5
        assert result["issues"] == ["Issue 0", "Issue 1", "Issue 2", "Issue 3", "Issue 4"]

    def test_empty_original_output(self):
        """Test handling when original output is None or empty."""
        result_none = build_correction_context(None, ["Issue"], "agent")
        result_empty = build_correction_context({}, ["Issue"], "agent")

        # None original
        assert result_none["output_keys"] == []

        # Empty dict original
        assert result_empty["output_keys"] == []

    def test_complex_output_keys(self):
        """Test extraction of keys from complex nested output."""
        original = {
            "insights": [{"title": "A", "description": "B"}],
            "metadata": {"count": 5},
            "summary": "text",
            "nested": {"deep": {"value": 1}},
        }
        issues = ["Test"]
        agent_type = "test"

        result = build_correction_context(original, issues, agent_type)

        # Should have top-level keys only
        assert set(result["output_keys"]) == {"insights", "metadata", "summary", "nested"}

    def test_zero_issues(self):
        """Test context when no issues present."""
        result = build_correction_context({"test": "data"}, [], "agent")

        assert result["issues_count"] == 0
        assert result["issues"] == []
        assert result["correction_triggered"] is True  # Still triggered


class TestGetAgentSpecificGuidance:
    """Test get_agent_specific_guidance() function."""

    def test_returns_guidance_for_known_agents(self):
        """Test returns template for known agent types."""
        # Check all known agents
        for agent_type in ["key_insights", "security_auditor", "tech_comparator"]:
            result = get_agent_specific_guidance(agent_type)

            assert result != ""
            assert isinstance(result, str)
            # Should be the template from dict
            assert result == AGENT_CORRECTION_TEMPLATES[agent_type]

    def test_key_insights_guidance_content(self):
        """Test key_insights guidance has expected content."""
        result = get_agent_specific_guidance("key_insights")

        assert "Extract" in result
        assert "unique insights" in result
        assert "specific title" in result
        assert "WHY this insight matters" in result

    def test_security_auditor_guidance_content(self):
        """Test security_auditor guidance has expected content."""
        result = get_agent_specific_guidance("security_auditor")

        assert "severity levels" in result
        assert "low, medium, high, critical" in result
        assert "OWASP" in result
        assert "actionable" in result

    def test_tech_comparator_guidance_content(self):
        """Test tech_comparator guidance has expected content."""
        result = get_agent_specific_guidance("tech_comparator")

        assert "specific technologies" in result
        assert "pros AND cons" in result
        assert "use cases" in result
        assert "version numbers" in result

    def test_returns_empty_for_unknown_agent(self):
        """Test returns empty string for unknown agent types."""
        unknown_agents = ["unknown_agent", "random_type", "not_real", ""]

        for agent in unknown_agents:
            result = get_agent_specific_guidance(agent)
            assert result == ""

    def test_handles_template_variables_with_context(self):
        """Test template variable substitution when context provided."""
        # key_insights template has {min_count} variable
        context = {"min_count": 5}
        result = get_agent_specific_guidance("key_insights", context)

        # Should have substituted the variable
        assert "5+ unique insights" in result
        assert "{min_count}" not in result

    def test_handles_missing_template_variables_gracefully(self):
        """Test returns template as-is when context missing required vars."""
        # key_insights needs min_count, but we don't provide it
        context = {"other_key": "value"}
        result = get_agent_specific_guidance("key_insights", context)

        # Should return template as-is (with unreplaced variable)
        assert result == AGENT_CORRECTION_TEMPLATES["key_insights"]
        assert "{min_count}" in result

    def test_context_none_returns_template_as_is(self):
        """Test None context returns unformatted template."""
        result = get_agent_specific_guidance("key_insights", None)

        # Should be raw template
        assert result == AGENT_CORRECTION_TEMPLATES["key_insights"]
        assert "{min_count}" in result  # Variable not replaced

    def test_empty_context_returns_template_as_is(self):
        """Test empty context dict returns unformatted template."""
        result = get_agent_specific_guidance("key_insights", {})

        # Should be raw template (format() will fail on missing key)
        assert result == AGENT_CORRECTION_TEMPLATES["key_insights"]
        assert "{min_count}" in result
