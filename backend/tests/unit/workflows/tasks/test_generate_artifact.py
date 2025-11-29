"""Unit tests for generate_artifact task."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.state import AnalysisState
from app.workflows.tasks.artifact_helpers import (
    build_claude_code_prompt,
    extract_artifact_metadata,
    generate_filename,
)
from app.workflows.tasks.generate_artifact import generate_artifact


@pytest.fixture
def sample_aggregated_insights():
    """Sample aggregated insights for testing."""
    return {
        "executive_summary": "This is a comprehensive analysis of React Server Components.",
        "key_findings": [
            "React Server Components enable server-side rendering",
            "Improves performance by reducing client bundle size",
            "Requires Next.js 13+ for full support",
        ],
        "synthesis": {
            "technical_analysis": "React Server Components represent a paradigm shift...",
            "implementation_guidance": "To implement RSC, start with Next.js 13...",
            "risk_assessment": "Main risks include migration complexity...",
            "recommendations": "Adopt RSC for new projects, migrate existing gradually.",
        },
        "conflicts_resolved": [],
        "metadata": {
            "total_agents": 3,
            "agents_executed": ["tech_comparator", "implementation_planner", "security_auditor"],
            "confidence_avg": 0.85,
        },
    }


@pytest.fixture
def sample_agent_findings():
    """Sample agent findings for testing."""
    return [
        {
            "agent_type": "tech_comparator",
            "findings": {
                "primary_tech": "React Server Components",
                "recommendation": "Use RSC for new projects",
            },
            "confidence_score": 0.90,
        },
        {
            "agent_type": "implementation_planner",
            "findings": {
                "prerequisites": ["Next.js 13+"],
                "steps": [{"step": 1, "action": "Install Next.js"}],
            },
            "confidence_score": 0.85,
        },
    ]


@pytest.fixture
def sample_state(sample_aggregated_insights, sample_agent_findings):
    """Sample analysis state for testing."""
    return AnalysisState(
        analysis_id="123e4567-e89b-12d3-a456-426614174000",  # Valid UUID string
        url="https://example.com/article",
        content_type="article",
        raw_content="Test content",
        extraction_metadata={"title": "React Server Components Guide", "word_count": 1000},
        content_embedding=[],
        supervisor_decision={},
        agent_findings=sample_agent_findings,
        aggregated_insights=sample_aggregated_insights,
    )


class TestExtractArtifactMetadata:
    """Test metadata extraction."""

    def test_extract_topics_from_key_findings(
        self, sample_aggregated_insights, sample_agent_findings
    ):
        """Test topic extraction from key findings."""
        metadata = extract_artifact_metadata(sample_aggregated_insights, sample_agent_findings)

        assert "topics" in metadata
        assert isinstance(metadata["topics"], list)
        assert len(metadata["topics"]) > 0

    def test_calculate_complexity_simple(self):
        """Test complexity calculation for simple case."""
        insights = {"key_findings": ["Finding 1"]}
        findings = [
            {"agent_type": "tech_comparator", "findings": {}, "confidence_score": 0.6},
        ]

        metadata = extract_artifact_metadata(insights, findings)

        assert metadata["complexity"] == "simple"
        assert metadata["agent_count"] == 1

    def test_calculate_complexity_advanced(self):
        """Test complexity calculation for advanced case."""
        insights = {"key_findings": ["Finding 1", "Finding 2"]}
        findings = [
            {"agent_type": f"agent_{i}", "findings": {}, "confidence_score": 0.90} for i in range(7)
        ]

        metadata = extract_artifact_metadata(insights, findings)

        assert metadata["complexity"] == "advanced"
        assert metadata["agent_count"] == 7

    def test_calculate_complexity_intermediate(self):
        """Test complexity calculation for intermediate case."""
        insights = {"key_findings": ["Finding 1"]}
        findings = [
            {"agent_type": f"agent_{i}", "findings": {}, "confidence_score": 0.80} for i in range(5)
        ]

        metadata = extract_artifact_metadata(insights, findings)

        assert metadata["complexity"] == "intermediate"
        assert metadata["agent_count"] == 5


class TestGenerateFilename:
    """Test filename generation."""

    def test_generate_filename_from_title(self):
        """Test filename generation from title."""
        filename = generate_filename("React Server Components Guide", "test-id")

        assert filename.endswith(".md")
        assert "react" in filename.lower()
        assert "server" in filename.lower()

    def test_generate_filename_fallback_to_id(self):
        """Test filename generation falls back to analysis ID."""
        filename = generate_filename(None, "abc12345-def6-7890")

        assert filename == "analysis-abc12345.md"

    def test_generate_filename_slugify_special_chars(self):
        """Test filename generation removes special characters."""
        filename = generate_filename("React 19: What's New?!", "test-id")

        assert filename.endswith(".md")
        assert "react" in filename.lower()
        assert ":" not in filename
        assert "?" not in filename
        assert "!" not in filename

    def test_generate_filename_limits_length(self):
        """Test filename generation limits length."""
        long_title = "A" * 150
        filename = generate_filename(long_title, "test-id")

        assert len(filename) <= 105  # 100 chars + ".md"
        assert filename.endswith(".md")


class TestBuildClaudeCodePrompt:
    """Test Claude Code prompt building."""

    def test_build_prompt_with_all_data(self, sample_aggregated_insights):
        """Test prompt building with all data."""
        metadata = {"title": "React Server Components", "url": "https://example.com"}

        prompt = build_claude_code_prompt(sample_aggregated_insights, metadata)

        assert "React Server Components" in prompt
        assert "https://example.com" in prompt
        assert "Executive Summary" in prompt or "Summary" in prompt
        assert "Key Findings" in prompt
        assert "Implementation Guidance" in prompt

    def test_build_prompt_with_missing_data(self):
        """Test prompt building with missing data."""
        insights = {"executive_summary": "Test summary", "key_findings": []}
        metadata = {"title": "Test", "url": "https://example.com"}

        prompt = build_claude_code_prompt(insights, metadata)

        assert "Test" in prompt
        assert "Test summary" in prompt


class TestGenerateArtifact:
    """Test artifact generation node."""

    @pytest.mark.asyncio
    async def test_generate_artifact_success(self, sample_state):
        """Test successful artifact generation."""
        with (
            patch("app.workflows.tasks.generate_artifact.render_jinja_template") as mock_render,
            patch("app.workflows.tasks.generate_artifact.get_session_factory") as mock_factory,
            patch("app.workflows.tasks.generate_artifact.emit_streaming_event") as mock_sse,
        ):
            # Setup mocks
            mock_render.return_value = "# Test Artifact\n\nContent here."
            mock_db_session = AsyncMock()
            mock_db_session.commit = AsyncMock()
            mock_db_session.refresh = AsyncMock()
            mock_session_factory = MagicMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db_session
            mock_factory.return_value = mock_session_factory

            # Mock repository
            with patch(
                "app.workflows.tasks.generate_artifact.ArtifactRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_artifact = MagicMock()
                mock_artifact.id = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
                mock_repo.create_artifact = AsyncMock(return_value=mock_artifact)
                mock_repo_class.return_value = mock_repo

                result = await generate_artifact(sample_state)

            # Verify result
            assert "artifact_id" in result
            assert result["artifact_id"] == str(mock_artifact.id)

            # Verify repository was used
            mock_repo.create_artifact.assert_called_once()

            # Verify SSE events
            assert mock_sse.call_count >= 2  # running and complete

    @pytest.mark.asyncio
    async def test_generate_artifact_empty_aggregated_insights(self, sample_state):
        """Test artifact generation with empty aggregated insights."""
        sample_state["aggregated_insights"] = {}

        with patch("app.workflows.tasks.generate_artifact.emit_streaming_event") as mock_sse:
            with pytest.raises(ValueError, match="aggregated_insights is missing or invalid"):
                await generate_artifact(sample_state)

            # Verify error SSE event was called
            assert mock_sse.called
            # Check that error event was emitted
            error_calls = [
                call
                for call in mock_sse.call_args_list
                if len(call[0]) > 0 and call[0][0] == "error"
            ]
            assert len(error_calls) > 0

    @pytest.mark.asyncio
    async def test_generate_artifact_missing_aggregated_insights(self, sample_state):
        """Test artifact generation with missing aggregated_insights."""
        del sample_state["aggregated_insights"]

        with patch("app.workflows.tasks.generate_artifact.emit_streaming_event") as mock_sse:
            with pytest.raises(ValueError, match="aggregated_insights is missing or invalid"):
                await generate_artifact(sample_state)

            # Verify error SSE event
            assert mock_sse.called

    @pytest.mark.asyncio
    async def test_generate_artifact_database_error(self, sample_state):
        """Test artifact generation handles database errors."""
        with (
            patch("app.workflows.tasks.generate_artifact.render_jinja_template") as mock_render,
            patch("app.workflows.tasks.generate_artifact.get_session_factory") as mock_factory,
            patch("app.workflows.tasks.generate_artifact.emit_streaming_event") as mock_sse,
        ):
            mock_render.return_value = "# Test\n\nContent."
            mock_db_session = AsyncMock()
            mock_session_factory = MagicMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db_session
            mock_factory.return_value = mock_session_factory

            with patch(
                "app.workflows.tasks.generate_artifact.ArtifactRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_repo.create_artifact.side_effect = Exception("Database error")
                mock_repo_class.return_value = mock_repo

                with pytest.raises(Exception):
                    await generate_artifact(sample_state)

            # Verify error SSE event was called
            assert mock_sse.called
            # Check that error event was emitted
            error_calls = [
                call
                for call in mock_sse.call_args_list
                if len(call[0]) > 0 and call[0][0] == "error"
            ]
            assert len(error_calls) > 0
