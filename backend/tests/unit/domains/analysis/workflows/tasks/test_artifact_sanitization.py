"""Tests for markdown sanitization in artifact generation.

This module tests that the markdown sanitizer is properly integrated
into the artifact generation workflow and fixes LLM-generated formatting issues.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.generate_artifact import generate_artifact


@pytest.fixture
def sample_state():
    """Sample analysis state for testing."""
    return AnalysisState(
        analysis_id="123e4567-e89b-12d3-a456-426614174000",
        url="https://example.com",
        content_type="article",
        raw_content="Test content",
        extraction_metadata={},
        content_embedding=[],
        supervisor_decision={},
        agent_findings=[],
        aggregated_insights={"key_findings": []},
    )


@pytest.mark.asyncio
class TestArtifactSanitization:
    """Tests for markdown sanitization integration."""

    async def test_artifact_sanitizes_tables_with_blank_lines(
        self, sample_state: AnalysisState
    ) -> None:
        """Should remove blank lines from tables in generated artifacts."""
        markdown_with_issues = """# Analysis

| File | Description |
|------|-------------|

| a.py | First file |

| b.py | Second file |
"""
        expected_table = "| a.py | First file |\n| b.py | Second file |"

        with (
            patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.render_jinja_template"
            ) as mock_render,
            patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.get_session_factory"
            ) as mock_factory,
            patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.emit_streaming_event"
            ) as mock_sse,
        ):
            mock_render.return_value = markdown_with_issues
            mock_db_session = AsyncMock()
            mock_session_factory = MagicMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db_session
            mock_factory.return_value = mock_session_factory

            with patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.ArtifactRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_artifact = MagicMock()
                mock_artifact.id = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
                mock_repo.create_artifact = AsyncMock(return_value=mock_artifact)
                mock_repo_class.return_value = mock_repo

                await generate_artifact(sample_state)

                # Get the markdown content that was saved
                call_args = mock_repo.create_artifact.call_args[0][0]
                saved_content = call_args["markdown_content"]

                # Should have removed blank lines between table rows
                assert expected_table in saved_content
                # Should not have double newlines within table
                assert "| a.py | First file |\n\n| b.py" not in saved_content

    async def test_artifact_sanitizes_complex_markdown(self, sample_state: AnalysisState) -> None:
        """Should handle complex documents with tables, bullets, and inline bullets."""
        markdown_complex = """# Technical Analysis

## Quick Reference

• **Framework**: React 19
• **Dependencies**: react, react-dom

## File Structure

| File | Purpose | Size |
|------|---------|------|

| index.ts | Entry | 2KB |

| App.tsx | Root | 5KB |

## Risks

Security concerns • Performance issues • Migration complexity
"""

        with (
            patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.render_jinja_template"
            ) as mock_render,
            patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.get_session_factory"
            ) as mock_factory,
            patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.emit_streaming_event"
            ) as mock_sse,
        ):
            mock_render.return_value = markdown_complex
            mock_db_session = AsyncMock()
            mock_session_factory = MagicMock()
            mock_session_factory.return_value.__aenter__.return_value = mock_db_session
            mock_factory.return_value = mock_session_factory

            with patch(
                "app.domains.analysis.workflows.tasks.generate_artifact.ArtifactRepository"
            ) as mock_repo_class:
                mock_repo = AsyncMock()
                mock_artifact = MagicMock()
                mock_artifact.id = uuid.UUID("123e4567-e89b-12d3-a456-426614174000")
                mock_repo.create_artifact = AsyncMock(return_value=mock_artifact)
                mock_repo_class.return_value = mock_repo

                await generate_artifact(sample_state)

                # Get the markdown content that was saved
                call_args = mock_repo.create_artifact.call_args[0][0]
                saved_content = call_args["markdown_content"]

                # Should fix bullets
                assert "- **Framework**: React 19" in saved_content
                assert "- **Dependencies**: react, react-dom" in saved_content

                # Should fix table blank lines
                assert "| index.ts | Entry | 2KB |\n| App.tsx | Root | 5KB |" in saved_content

                # Should split inline risks
                assert "- Security concerns" in saved_content
                assert "- Performance issues" in saved_content
                assert "- Migration complexity" in saved_content
