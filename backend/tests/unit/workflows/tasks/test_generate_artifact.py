"""Unit tests for generate_artifact task."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.template_utils import render_jinja_template
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


class TestGFMTemplateRendering:
    """Test GitHub Flavored Markdown template rendering."""

    @pytest.fixture
    def gfm_agent_findings(self):
        """Agent findings with data for GFM elements testing."""
        return [
            {
                "agent_type": "tech_comparator",
                "findings": {
                    "primary_tech": "LangGraph",
                    "alternatives": ["LangChain Agents", "Temporal", "Ray"],
                    "comparison": {
                        "LangGraph": {
                            "pros": ["Low-level control", "Durable execution"],
                            "cons": ["Steeper learning curve"],
                            "use_cases": ["Long-running agents", "Stateful workflows"],
                        },
                        "LangChain Agents": {
                            "pros": ["High-level abstraction", "Easy to use"],
                            "cons": ["Less control"],
                            "use_cases": ["Quick prototypes"],
                        },
                    },
                    "recommendation": "Use LangGraph for production workflows",
                },
                "confidence_score": 0.92,
            },
            {
                "agent_type": "security_auditor",
                "findings": {
                    "security_risks": [
                        {
                            "risk_type": "injection",
                            "severity": "high",
                            "description": "SQL injection vulnerability",
                            "mitigation": "Use parameterized queries",
                        },
                        {
                            "risk_type": "xss",
                            "severity": "medium",
                            "description": "Cross-site scripting risk",
                            "mitigation": "Sanitize user input",
                        },
                    ],
                    "recommendation": "Address high severity issues first",
                },
                "confidence_score": 0.88,
            },
            {
                "agent_type": "implementation_planner",
                "findings": {
                    "prerequisites": ["Python 3.11+", "PostgreSQL 15+", "Redis"],
                    "steps": [
                        {"step": 1, "action": "Install dependencies", "files": ["requirements.txt"]},
                        {"step": 2, "action": "Configure environment", "files": [".env", "config.py"]},
                        {"step": 3, "action": "Initialize database"},
                    ],
                    "recommendation": "Follow steps in order",
                },
                "confidence_score": 0.85,
            },
            {
                "agent_type": "dependency_mapper",
                "findings": {
                    "required_dependencies": [
                        {
                            "name": "langgraph",
                            "version": "^0.2.0",
                            "purpose": "Workflow orchestration",
                            "compatibility": "compatible",
                        },
                        {
                            "name": "fastapi",
                            "version": "^0.115.0",
                            "purpose": "API framework",
                            "compatibility": "compatible",
                        },
                    ],
                    "optional_dependencies": [
                        {
                            "name": "redis",
                            "version": "^5.0.0",
                            "purpose": "Caching layer",
                            "compatibility": "compatible",
                        },
                    ],
                    "version_conflicts": ["numpy 1.x conflicts with pandas 2.x"],
                    "peer_dependencies": ["Node.js 18+", "Python 3.11+"],
                    "recommendation": "Use exact versions in production",
                },
                "confidence_score": 0.90,
            },
        ]

    @pytest.fixture
    def gfm_template_context(self, sample_aggregated_insights, gfm_agent_findings):
        """Template context with GFM-compatible data."""
        return {
            "aggregated_insights": sample_aggregated_insights,
            "agent_findings": gfm_agent_findings,
            "analysis_metadata": {
                "title": "GFM Test Artifact",
                "url": "https://example.com/test",
                "generated_date": "2025-11-30",
                "analysis_id": "test-123",
            },
            "claude_code_prompt": "# Test prompt",
        }

    def test_renders_tech_comparison_table(self, gfm_template_context):
        """Test that tech comparison renders as markdown table."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check table structure
        assert "| Technology | Pros | Cons | Use Cases |" in result
        assert "|------------|------|------|-----------|" in result
        # Check inline code in table cells
        assert "| `LangGraph` |" in result
        assert "| `LangChain Agents` |" in result

    def test_renders_inline_code_for_tech_names(self, gfm_template_context):
        """Test that tech names use inline code formatting."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Primary tech should be wrapped in backticks
        assert "`LangGraph`" in result
        # Alternatives should be wrapped in backticks
        assert "`LangChain Agents`" in result
        assert "`Temporal`" in result
        assert "`Ray`" in result

    def test_renders_task_list_for_implementation_steps(self, gfm_template_context):
        """Test that implementation steps render as task list."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check task list syntax
        assert "- [ ] **Step 1:**" in result
        assert "- [ ] **Step 2:**" in result
        assert "- [ ] **Step 3:**" in result
        # Check inline code for files
        assert "`requirements.txt`" in result
        assert "`config.py`" in result

    def test_renders_security_risks_table(self, gfm_template_context):
        """Test that security risks render as markdown table."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check table structure
        assert "| Risk Type | Severity | Description | Mitigation |" in result
        assert "|-----------|----------|-------------|------------|" in result
        # Check severity formatting (bold uppercase)
        assert "**HIGH**" in result
        assert "**MEDIUM**" in result
        # Check risk content
        assert "SQL injection" in result
        assert "parameterized queries" in result

    def test_renders_dependency_tables(self, gfm_template_context):
        """Test that dependencies render as markdown tables."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check required dependencies table
        assert "| Package | Version | Purpose | Compatibility |" in result
        assert "`langgraph`" in result
        assert "`fastapi`" in result
        assert "`^0.2.0`" in result

        # Check optional dependencies table
        assert "#### Optional Dependencies" in result
        assert "`redis`" in result

    def test_renders_inline_code_for_prerequisites(self, gfm_template_context):
        """Test that prerequisites use inline code formatting."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        assert "`Python 3.11+`" in result
        assert "`PostgreSQL 15+`" in result
        assert "`Redis`" in result

    def test_renders_version_conflicts_with_warning(self, gfm_template_context):
        """Test that version conflicts are rendered with warning emoji."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        assert "⚠️" in result
        assert "numpy 1.x conflicts with pandas 2.x" in result

    def test_renders_peer_dependencies_with_inline_code(self, gfm_template_context):
        """Test that peer dependencies use inline code formatting."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        assert "`Node.js 18+`" in result
        assert "`Python 3.11+`" in result

    def test_renders_agents_involved_with_inline_code(self, gfm_template_context):
        """Test that agents involved list uses inline code formatting."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        assert "`tech_comparator`" in result
        assert "`implementation_planner`" in result
        assert "`security_auditor`" in result

    def test_handles_empty_comparison_gracefully(self, gfm_template_context):
        """Test that empty comparison dict doesn't break template."""
        gfm_template_context["agent_findings"][0]["findings"]["comparison"] = {}
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Should still render without errors
        assert "Tech Comparator" in result
        # Empty comparison should not render table
        assert "| Technology | Pros | Cons | Use Cases |" not in result

    def test_handles_missing_optional_fields(self, gfm_template_context):
        """Test that missing optional fields don't break template."""
        # Remove optional fields
        gfm_template_context["agent_findings"][3]["findings"].pop("optional_dependencies")
        gfm_template_context["agent_findings"][3]["findings"].pop("version_conflicts")

        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Should still render without errors
        assert "Dependency Mapper" in result
        assert "`langgraph`" in result
