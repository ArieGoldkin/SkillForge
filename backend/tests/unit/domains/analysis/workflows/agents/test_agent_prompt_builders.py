"""Unit tests for agent prompt builders."""

from app.domains.analysis.workflows.agents.prompt_builders import (
    build_agent_user_prompt,
    build_supervisor_user_prompt,
    format_content_signals_for_prompt,
)
from app.shared.workflows.utils.content_signals import ContentGenre, ContentSignals


class TestBuildAgentUserPrompt:
    """Test build_agent_user_prompt function."""

    def test_build_prompt_with_short_content(self):
        """Test building prompt with content shorter than max_length."""
        content = "Short content"
        content_type = "article"

        result = build_agent_user_prompt(content, content_type, max_length=1500)

        assert "Content Type: article" in result
        assert "Short content" in result
        assert len(result) > 0

    def test_build_prompt_with_long_content(self):
        """Test building prompt truncates content at max_length."""
        content = "A" * 2000  # 2000 characters
        content_type = "article"

        result = build_agent_user_prompt(content, content_type, max_length=1500)

        assert "Content Type: article" in result
        # Should be truncated to 1500 chars
        assert len(result) < len(content) + 50  # +50 for header text
        assert "A" * 1500 in result

    def test_build_prompt_with_different_content_types(self):
        """Test building prompt with different content types."""
        content = "Test content"
        content_types = ["article", "video", "repo"]

        for content_type in content_types:
            result = build_agent_user_prompt(content, content_type)
            assert f"Content Type: {content_type}" in result
            assert "Test content" in result

    def test_build_prompt_exact_max_length(self):
        """Test building prompt with content exactly at max_length."""
        content = "A" * 1500
        content_type = "article"

        result = build_agent_user_prompt(content, content_type, max_length=1500)

        assert "Content Type: article" in result
        assert content in result  # Should include full content

    def test_build_prompt_structure(self):
        """Test prompt has correct structure."""
        content = "Test content"
        content_type = "article"

        result = build_agent_user_prompt(content, content_type)

        lines = result.split("\n")
        assert lines[0] == "Content Type: article"
        assert lines[1] == ""  # Blank line
        assert lines[2] == "Content:"
        assert lines[3] == "Test content"


class TestBuildSupervisorUserPrompt:
    """Test build_supervisor_user_prompt function."""

    def test_build_supervisor_prompt(self):
        """Test building supervisor user prompt."""
        system_prompt = "You are a supervisor."
        content = "Test content"
        content_type = "article"

        result = build_supervisor_user_prompt(system_prompt, content, content_type)

        assert system_prompt in result
        assert f"Content Type: {content_type}" in result
        assert content in result

    def test_build_supervisor_prompt_structure(self):
        """Test supervisor prompt has correct structure."""
        system_prompt = "System prompt"
        content = "Test content"
        content_type = "video"

        result = build_supervisor_user_prompt(system_prompt, content, content_type)

        assert result.startswith(system_prompt)
        assert "Content Type: video" in result
        assert result.endswith(content)

    def test_build_supervisor_prompt_with_empty_content(self):
        """Test building supervisor prompt with empty content."""
        system_prompt = "System prompt"
        content = ""
        content_type = "article"

        result = build_supervisor_user_prompt(system_prompt, content, content_type)

        assert system_prompt in result
        assert "Content Type: article" in result

    def test_build_supervisor_prompt_with_content_signals(self):
        """Test building supervisor prompt with content signals."""
        system_prompt = "System prompt"
        content = "Test content"
        content_type = "article"
        signals = ContentSignals(
            has_code_patterns=True,
            has_benchmarks=True,
            detected_genre=ContentGenre.TUTORIAL,
            content_richness_score=7.5,
            word_count=1000,
        )

        result = build_supervisor_user_prompt(system_prompt, content, content_type, signals)

        # Verify content signals are included
        assert "CONTENT ANALYSIS" in result
        assert "Genre: tutorial" in result
        assert "Richness Score: 7.5/10" in result
        assert "Word Count: 1000" in result
        assert "code_patterns, benchmarks" in result
        assert "ROUTING GUIDELINES BY GENRE" in result
        assert "TUTORIAL: Expect code, steps, implementation" in result

    def test_build_supervisor_prompt_without_content_signals(self):
        """Test building supervisor prompt without content signals (backwards compatibility)."""
        system_prompt = "System prompt"
        content = "Test content"
        content_type = "article"

        result = build_supervisor_user_prompt(system_prompt, content, content_type)

        # Should not include content analysis when signals are None
        assert "CONTENT ANALYSIS" not in result
        assert system_prompt in result
        assert content in result


class TestFormatContentSignalsForPrompt:
    """Test format_content_signals_for_prompt function."""

    def test_format_signals_with_multiple_active_signals(self):
        """Test formatting with multiple active boolean signals."""
        signals = ContentSignals(
            has_code_patterns=True,
            has_benchmarks=True,
            has_security_patterns=True,
            detected_genre=ContentGenre.TUTORIAL,
            content_richness_score=8.2,
            word_count=2500,
        )

        result = format_content_signals_for_prompt(signals)

        assert "Genre: tutorial" in result
        assert "Richness Score: 8.2/10" in result
        assert "Word Count: 2500" in result
        assert "code_patterns" in result
        assert "benchmarks" in result
        assert "security" in result

    def test_format_signals_with_no_active_signals(self):
        """Test formatting when no signals are active."""
        signals = ContentSignals(
            detected_genre=ContentGenre.OPINION,
            content_richness_score=3.0,
            word_count=500,
        )

        result = format_content_signals_for_prompt(signals)

        assert "Genre: opinion" in result
        assert "Richness Score: 3.0/10" in result
        assert "Word Count: 500" in result
        assert "Active Signals: none" in result

    def test_format_signals_includes_genre_guidelines(self):
        """Test that genre-specific routing guidelines are included."""
        signals = ContentSignals(
            detected_genre=ContentGenre.RESEARCH,
            content_richness_score=5.0,
            word_count=1000,
        )

        result = format_content_signals_for_prompt(signals)

        assert "ROUTING GUIDELINES BY GENRE" in result
        assert "RESEARCH: Expect concepts, not metrics" in result
        assert "TUTORIAL: Expect code, steps, implementation" in result
        assert "OPINION: Expect subjective analysis" in result
        assert "NOTE: These signals were detected through fast regex patterns" in result

    def test_format_signals_research_genre(self):
        """Test formatting for research genre."""
        signals = ContentSignals(
            has_architecture=True,
            detected_genre=ContentGenre.RESEARCH,
            content_richness_score=6.0,
            word_count=3000,
        )

        result = format_content_signals_for_prompt(signals)

        assert "Genre: research" in result
        assert "architecture" in result
        assert "Minimum: 2 agents" in result

    def test_format_signals_conceptual_only(self):
        """Test formatting when content is conceptual only."""
        signals = ContentSignals(
            has_conceptual_only=True,
            detected_genre=ContentGenre.OPINION,
            content_richness_score=2.0,
            word_count=800,
        )

        result = format_content_signals_for_prompt(signals)

        assert "Conceptual Only: True" in result
        assert "Genre: opinion" in result
