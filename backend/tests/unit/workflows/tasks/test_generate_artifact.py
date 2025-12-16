"""Unit tests for generate_artifact task."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.template_utils import render_jinja_template
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.artifact_helpers import (
    build_claude_code_prompt,
    extract_artifact_metadata,
    generate_filename,
)
from app.domains.analysis.workflows.tasks.generate_artifact import generate_artifact



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

                with pytest.raises(Exception, match="Database error"):
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
                        {
                            "step": 1,
                            "action": "Install dependencies",
                            "files": ["requirements.txt"],
                        },
                        {
                            "step": 2,
                            "action": "Configure environment",
                            "files": [".env", "config.py"],
                        },
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

    def test_renders_tech_comparator_findings(self, gfm_template_context):
        """Test that tech comparator findings render with primary tech and alternatives.

        Note: Issue #304 redesigned the template - tech comparison is now in
        agent_findings section with primary_tech and alternatives list format.
        """
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check agent findings section renders tech comparator
        assert "Tech Comparator" in result
        # Check primary technology is rendered with inline code
        assert "**Primary Technology:** `LangGraph`" in result
        # Check alternatives are rendered with inline code
        assert "`LangChain Agents`" in result
        assert "`Temporal`" in result
        assert "`Ray`" in result

    def test_renders_inline_code_for_tech_names(self, gfm_template_context):
        """Test that tech names use inline code formatting."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Primary tech should be wrapped in backticks
        assert "`LangGraph`" in result
        # Alternatives should be wrapped in backticks
        assert "`LangChain Agents`" in result
        assert "`Temporal`" in result
        assert "`Ray`" in result

    def test_renders_implementation_planner_findings(self, gfm_template_context):
        """Test that implementation planner findings render prerequisites.

        Note: Issue #304 redesigned the template - implementation steps are now
        in AI Assistant Prompt section as numbered list, not task checkboxes.
        Prerequisites render as inline code in agent_findings section.
        """
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check implementation planner section renders
        assert "Implementation Planner" in result
        # Check prerequisites are rendered with inline code
        assert "`Python 3.11+`" in result
        assert "`PostgreSQL 15+`" in result
        assert "`Redis`" in result
        # Check recommendation renders
        assert "Follow steps in order" in result

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
        """Test that dependencies render as markdown tables.

        Note: Issue #304 redesigned the template - dependencies table has
        3 columns (Package, Version, Purpose), not 4 (no Compatibility column).
        """
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check required dependencies table structure (3 columns)
        assert "| Package | Version | Purpose |" in result
        assert "`langgraph`" in result
        assert "`fastapi`" in result
        assert "`^0.2.0`" in result

        # Note: Optional dependencies and version_conflicts sections
        # were removed in Issue #304 template redesign

    def test_renders_inline_code_for_prerequisites(self, gfm_template_context):
        """Test that prerequisites use inline code formatting."""
        result = render_jinja_template("artifact.j2", gfm_template_context)

        assert "`Python 3.11+`" in result
        assert "`PostgreSQL 15+`" in result
        assert "`Redis`" in result

    def test_renders_dependency_mapper_recommendation(self, gfm_template_context):
        """Test that dependency mapper recommendation renders.

        Note: Issue #304 redesigned the template - version conflicts and peer
        dependencies sections were removed. Testing recommendation instead.
        """
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check dependency mapper section renders
        assert "Dependency Mapper" in result
        # Check recommendation renders
        assert "Use exact versions in production" in result

    def test_renders_confidence_scores(self, gfm_template_context):
        """Test that confidence scores render for each agent.

        Note: Added in Issue #304 - confidence scores with 2 decimal places.
        """
        result = render_jinja_template("artifact.j2", gfm_template_context)

        # Check confidence scores are rendered (format: "%.2f")
        assert "**Confidence Score:** 0.92" in result  # tech_comparator
        assert "**Confidence Score:** 0.88" in result  # security_auditor
        assert "**Confidence Score:** 0.85" in result  # implementation_planner
        assert "**Confidence Score:** 0.90" in result  # dependency_mapper

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


class TestTemplateSectionNullSafety:
    """Test null safety guards for each template section."""

    def test_tldr_section_null_safety(self):
        """Test TLDR section with missing summary/key_takeaways."""
        # Test 1: Empty TLDR should not render section
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "tldr": {},  # Empty TLDR
                "executive_summary": "Summary",
                "key_findings": ["Finding 1"],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Empty TLDR should not render section at all
        assert "Test" in result
        assert "## TL;DR" not in result

        # Test 2: TLDR with only summary should render
        context["aggregated_insights"]["tldr"] = {"summary": "Quick summary"}
        result = render_jinja_template("artifact.j2", context)
        assert "## TL;DR" in result
        assert "Quick summary" in result

    def test_quick_reference_null_safety(self):
        """Test Quick Reference with missing fields."""
        # Test 1: Empty quick reference should not render section
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "quick_reference": {},  # Empty quick reference
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Empty quick reference should not render section
        assert "## Quick Reference" not in result

        # Test 2: Quick reference with fields should render with N/A defaults
        context["quick_reference"] = {"primary_technology": "Python"}
        result = render_jinja_template("artifact.j2", context)
        assert "## Quick Reference" in result
        assert "Python" in result
        assert "N/A" in result  # For missing complexity field

    def test_ai_assistant_prompt_null_safety(self):
        """Test AI Assistant Prompt with missing sections."""
        # Test 1: Empty ai_assistant_prompt should not render section
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "ai_assistant_prompt": {
                    # Missing context, implementation_steps, code_snippets, etc.
                },
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Empty ai_assistant_prompt should not render section
        assert "Test" in result
        assert "## AI Assistant Implementation Guide" not in result

        # Test 2: ai_assistant_prompt with context should render
        context["aggregated_insights"]["ai_assistant_prompt"] = {"context": "Context for AI"}
        result = render_jinja_template("artifact.j2", context)
        assert "## AI Assistant Implementation Guide" in result
        assert "Context for AI" in result

    def test_diagrams_section_null_safety(self):
        """Test Diagrams section with missing mermaid_code."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "diagrams": [
                    {"title": "Architecture", "description": "System architecture"},
                    # Missing mermaid_code
                ],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render without errors
        assert "## Architecture & Flow Diagrams" in result
        assert "Architecture" in result

    def test_core_concepts_null_safety(self):
        """Test Core Concepts with missing fields."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "core_concepts": [
                    {
                        # Missing name, definition, complexity_level, etc.
                    },
                ],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render with "Concept" default
        assert "## Core Concepts" in result
        assert "Concept" in result

    def test_exercises_section_null_safety(self):
        """Test Exercises with missing hints/solution."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "exercises": [
                    {
                        "title": "Practice Problem",
                        # Missing hints, solution, learning_objectives
                    },
                ],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render without errors
        assert "## Practice Exercises" in result
        assert "Practice Problem" in result

    def test_self_assessment_null_safety(self):
        """Test Self Assessment with missing options/answers."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "self_assessment": {
                    "quiz_questions": [
                        {
                            # Missing question, options, correct_answer
                        },
                    ],
                },
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render with "Question" default
        assert "## Self-Assessment" in result
        assert "Question" in result

    def test_glossary_null_safety(self):
        """Test Glossary with missing see_also."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "glossary": [
                    {
                        # Missing term, definition, see_also
                    },
                ],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render with N/A defaults
        assert "## Glossary" in result
        assert "N/A" in result

    def test_agent_findings_null_safety(self):
        """Test Agent Findings with missing nested fields."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "agent_findings": [
                {
                    # Missing agent_type, findings, confidence_score
                },
            ],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render with "Unknown Agent" default
        assert "## Detailed Agent Findings" in result
        assert "Unknown Agent" in result

    def test_conflicts_resolved_null_safety(self):
        """Test Conflicts Resolved with missing resolution."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "conflicts_resolved": [
                    {
                        # Missing conflict, resolution, priority_agent, reasoning
                    },
                ],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render with defaults
        assert "## Conflicts Resolved" in result
        assert "N/A" in result

    def test_empty_aggregated_insights(self):
        """Test completely empty insights dict."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {},
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render minimal artifact with defaults
        assert "Test" in result
        assert "## Executive Summary" in result
        assert "Analysis summary not available." in result
        assert "No key findings available." in result

    def test_partial_synthesis_section(self):
        """Test only some synthesis fields present."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
                "synthesis": {
                    "technical_analysis": "Technical details here",
                    # Missing implementation_guidance, risk_assessment, recommendations
                },
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render available sections with "not available" for missing ones
        assert "Technical details here" in result
        assert "Implementation guidance not available." in result
        assert "Risk assessment not available." in result
        assert "Recommendations not available." in result

    def test_security_risks_table_null_safety(self):
        """Test Security Risks table with missing fields."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "agent_findings": [
                {
                    "agent_type": "security_auditor",
                    "findings": {
                        "security_risks": [
                            {
                                # Missing risk_type, severity, description, mitigation
                            },
                        ],
                    },
                    "confidence_score": 0.8,
                },
            ],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render table with defaults
        assert "## Detailed Agent Findings" in result
        assert "Security Auditor" in result
        assert "| Risk Type | Severity | Description | Mitigation |" in result
        assert "Unknown" in result
        assert "N/A" in result

    def test_dependencies_table_null_safety(self):
        """Test Dependencies table with missing fields."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "agent_findings": [
                {
                    "agent_type": "dependency_mapper",
                    "findings": {
                        "required_dependencies": [
                            {
                                # Missing name, version, purpose
                            },
                        ],
                    },
                    "confidence_score": 0.8,
                },
            ],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render table with N/A defaults
        assert "Dependency Mapper" in result
        assert "| Package | Version | Purpose |" in result
        assert "N/A" in result

    def test_metadata_section_null_safety(self):
        """Test Metadata section with missing fields."""
        context = {
            "analysis_metadata": {},  # Empty metadata
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render with N/A defaults
        assert "## Analysis Metadata" in result
        assert "N/A" in result

    def test_full_artifact_generation(self):
        """Test complete data renders all 13 sections."""
        context = {
            "analysis_metadata": {
                "title": "Complete Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "tldr": {
                    "summary": "Quick summary",
                    "key_takeaways": ["Takeaway 1"],
                    "time_to_implement": "2 hours",
                },
                "executive_summary": "Executive summary",
                "key_findings": ["Finding 1"],
                "synthesis": {
                    "technical_analysis": "Technical details",
                    "implementation_guidance": "Implementation guide",
                    "risk_assessment": "Risk analysis",
                    "recommendations": "Recommendations",
                },
                "ai_assistant_prompt": {
                    "context": "Context for AI",
                    "implementation_steps": ["Step 1"],
                    "code_snippets": {"example": "print('hello')"},
                    "success_criteria": ["Criterion 1"],
                },
                "diagrams": [{"title": "Diagram 1", "mermaid_code": "graph TD\nA-->B"}],
                "core_concepts": [{"name": "Concept 1", "definition": "Definition"}],
                "exercises": [{"title": "Exercise 1", "description": "Description"}],
                "self_assessment": {
                    "quiz_questions": [
                        {"question": "Q1", "options": ["A", "B"], "correct_answer": "A"}
                    ],
                    "mastery_checklist": ["Skill 1"],
                },
                "glossary": [{"term": "Term 1", "definition": "Definition 1"}],
                "conflicts_resolved": [{"conflict": "Conflict 1", "resolution": "Resolution 1"}],
                "cross_domain_connections": [{"domains": ["A", "B"], "connection": "Connection"}],
                "metadata": {
                    "total_agents": 2,
                    "agents_executed": ["agent1", "agent2"],
                    "confidence_avg": 0.85,
                },
                "coverage_score": 0.95,
            },
            "quick_reference": {
                "primary_technology": "Python",
                "complexity": "Intermediate",
                "prerequisites": ["Prereq 1"],
            },
            "agent_findings": [
                {
                    "agent_type": "tech_comparator",
                    "findings": {"recommendation": "Recommendation"},
                    "confidence_score": 0.9,
                },
            ],
        }

        result = render_jinja_template("artifact.j2", context)

        # Verify all major sections are present
        assert "## TL;DR" in result
        assert "## Quick Reference" in result
        assert "## Executive Summary" in result
        assert "## AI Assistant Implementation Guide" in result
        assert "## Architecture & Flow Diagrams" in result
        assert "## Technical Analysis" in result
        assert "## Implementation Plan" in result
        assert "## Risk Assessment" in result
        assert "## Recommendations" in result
        assert "## Core Concepts" in result
        assert "## Practice Exercises" in result
        assert "## Self-Assessment" in result
        assert "## Glossary" in result
        assert "## Detailed Agent Findings" in result
        assert "## Conflicts Resolved" in result
        assert "## Cross-Domain Insights" in result
        assert "## Analysis Metadata" in result

    def test_minimal_artifact_generation(self):
        """Test minimal data renders gracefully."""
        context = {
            "analysis_metadata": {
                "title": "Minimal",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Should render without errors
        assert "Minimal" in result
        assert "## Executive Summary" in result
        assert "No key findings available." in result
        assert "No agent findings available." in result

    def test_artifact_metadata_always_present(self):
        """Test header always renders."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Header should always be present
        assert "# Test" in result
        assert "**Source:** https://test.com" in result
        assert "**Generated:** 2025-01-01" in result
        assert "**Analysis ID:** `123`" in result

    def test_artifact_footer_always_present(self):
        """Test footer always renders."""
        context = {
            "analysis_metadata": {
                "title": "Test",
                "url": "https://test.com",
                "generated_date": "2025-01-01",
                "analysis_id": "123",
            },
            "aggregated_insights": {
                "executive_summary": "Summary",
                "key_findings": [],
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Footer should always be present
        assert "This triple-purpose artifact was generated by SkillForge" in result

    def test_artifact_no_jinja_errors(self):
        """Test no Jinja2 UndefinedError is thrown."""
        # Intentionally minimal context - everything optional should be missing
        context = {
            "analysis_metadata": {},
            "aggregated_insights": {},
            "agent_findings": [],
        }

        # This should not raise any exceptions
        result = render_jinja_template("artifact.j2", context)

        # Should render successfully
        assert isinstance(result, str)
        assert len(result) > 0

    def test_artifact_files_disclaimer_rendering(self):
        """Test that files disclaimer is rendered correctly (Issue #299-304)."""
        from app.domains.analysis.workflows.tasks.schemas.aggregated_insights import QuickReference

        quick_ref = QuickReference(
            primary_technology="Test Framework 1.0",
            complexity="Intermediate (Est. 3-4 hours)",
            files_to_modify=["src/index.ts", "src/config.ts"],
        )

        context = {
            "analysis_metadata": {
                "title": "Test Analysis",
                "url": "https://example.com",
                "generated_date": "2024-12-14",
                "analysis_id": "test-123",
            },
            "quick_reference": quick_ref,
            "aggregated_insights": {
                "executive_summary": "Test summary",
                "key_findings": ["Finding 1"],
                "synthesis": {
                    "technical_analysis": "Analysis",
                    "implementation_guidance": "Guidance",
                    "risk_assessment": "Risks",
                    "recommendations": "Recommendations",
                },
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Verify section title is renamed
        assert "📁 Suggested File Structure" in result

        # Verify disclaimer is present
        assert "AI-suggested" in result or "suggested" in result.lower()

        # Verify files are listed
        assert "src/index.ts" in result
        assert "src/config.ts" in result

    def test_artifact_files_section_hidden_when_empty(self):
        """Test that files section is not shown when files list is empty."""
        from app.domains.analysis.workflows.tasks.schemas.aggregated_insights import QuickReference

        quick_ref = QuickReference(
            primary_technology="Test Framework 1.0",
            complexity="Intermediate (Est. 3-4 hours)",
            files_to_modify=[],  # Empty list
        )

        context = {
            "analysis_metadata": {
                "title": "Test Analysis",
                "url": "https://example.com",
                "generated_date": "2024-12-14",
                "analysis_id": "test-123",
            },
            "quick_reference": quick_ref,
            "aggregated_insights": {
                "executive_summary": "Test summary",
                "key_findings": ["Finding 1"],
                "synthesis": {
                    "technical_analysis": "Analysis",
                    "implementation_guidance": "Guidance",
                    "risk_assessment": "Risks",
                    "recommendations": "Recommendations",
                },
            },
            "agent_findings": [],
        }

        result = render_jinja_template("artifact.j2", context)

        # Verify section title is NOT present when files list is empty
        assert "📁 Suggested File Structure" not in result
        assert "Files to Create/Modify" not in result
