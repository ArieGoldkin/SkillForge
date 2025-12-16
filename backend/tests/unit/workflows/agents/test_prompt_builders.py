"""Unit tests for agent prompt builders."""

from app.domains.analysis.workflows.agents.prompt_builders import (
import pytest

    build_agent_user_prompt,
    build_supervisor_user_prompt,
)


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
