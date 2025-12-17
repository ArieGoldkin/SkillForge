"""Unit tests for context scoping functionality.

Tests the context scoping system that reduces state size passed to agents
by including only the minimal fields each agent needs.

Reference: Issue #246 - Multi-Agent Context Scoping
"""

import pytest

from app.shared.workflows.context_scope import (
    AGENT_SCOPES,
    ContextScope,
    ScopedState,
    build_scoped_context,
    translate_findings,
)
from app.domains.analysis.workflows.state import AnalysisState, ContentRef


@pytest.fixture
def sample_full_state() -> AnalysisState:
    """Create a sample full AnalysisState for testing."""
    return AnalysisState(
        analysis_id="test-analysis-123",
        url="https://example.com/article",
        content_type="article",
        skill_level="intermediate",
        raw_content="This is very large content that would be expensive to pass around" * 100,
        content_ref=ContentRef(
            uri="analysis://test-analysis-123/content",
            summary="Article about testing context scoping",
            size_bytes=5000,
            content_type="text/markdown",
            available_sections=["summary", "full", "code_blocks"],
        ),
        extraction_metadata={
            "title": "Test Article",
            "word_count": 1500,
            "author": "Test Author",
        },
        agent_findings=[
            {
                "agent_type": "tech_comparator",
                "findings": {
                    "technologies": ["Python", "FastAPI", "PostgreSQL"],
                    "comparisons": ["FastAPI vs Flask", "PostgreSQL vs MySQL"],
                },
                "processing_time_ms": 1200,
            },
            {
                "agent_type": "security_auditor",
                "findings": {
                    "security_risks": [
                        {"type": "sql_injection", "severity": "high"},
                        {"type": "xss", "severity": "medium"},
                    ],
                    "best_practices": ["Use parameterized queries", "Sanitize inputs"],
                },
                "processing_time_ms": 1500,
            },
        ],
        supervisor_decision={
            "agents": ["security_auditor", "tech_comparator"],
            "reasoning": "Test reasoning",
        },
        content_embedding=[0.1, 0.2, 0.3],
    )


class TestContextScope:
    """Test ContextScope model."""

    def test_context_scope_defaults(self) -> None:
        """Test ContextScope with default values."""
        scope = ContextScope()

        assert scope.include == []
        assert scope.exclude == []
        assert scope.inject_memory is False
        assert scope.max_content_tokens is None
        assert scope.include_other_findings is False

    def test_context_scope_custom(self) -> None:
        """Test ContextScope with custom values."""
        scope = ContextScope(
            include=["analysis_id", "content_ref"],
            exclude=["raw_content"],
            inject_memory=True,
            max_content_tokens=5000,
            include_other_findings=True,
        )

        assert scope.include == ["analysis_id", "content_ref"]
        assert scope.exclude == ["raw_content"]
        assert scope.inject_memory is True
        assert scope.max_content_tokens == 5000
        assert scope.include_other_findings is True


class TestBuildScopedContext:
    """Test build_scoped_context function."""

    def test_basic_scoping(self, sample_full_state: AnalysisState) -> None:
        """Test that scoping includes only specified fields."""
        scope = ContextScope(include=["analysis_id", "content_ref", "content_type"])

        scoped = build_scoped_context(
            sample_full_state,
            "security_auditor",
            scope=scope,
        )

        # Should include only the specified fields
        assert "analysis_id" in scoped
        assert "content_ref" in scoped
        assert "content_type" in scoped

        # Should NOT include other fields
        assert "raw_content" not in scoped
        assert "extraction_metadata" not in scoped
        assert "agent_findings" not in scoped
        assert "supervisor_decision" not in scoped
        assert "content_embedding" not in scoped

        # Verify values are correct
        assert scoped["analysis_id"] == "test-analysis-123"
        assert scoped["content_type"] == "article"

    def test_exclusion(self, sample_full_state: AnalysisState) -> None:
        """Test that exclusion removes fields even if included."""
        scope = ContextScope(
            include=["analysis_id", "content_ref", "content_type"],
            exclude=["content_ref"],
        )

        scoped = build_scoped_context(
            sample_full_state,
            "security_auditor",
            scope=scope,
        )

        # Should include analysis_id and content_type
        assert "analysis_id" in scoped
        assert "content_type" in scoped

        # Should NOT include content_ref (excluded)
        assert "content_ref" not in scoped

    def test_inject_memory(self, sample_full_state: AnalysisState) -> None:
        """Test that inject_memory adds prior_context."""
        scope = ContextScope(
            include=["analysis_id"],
            inject_memory=True,
        )

        scoped = build_scoped_context(
            sample_full_state,
            "implementation_planner",
            scope=scope,
        )

        # Should include prior_context
        assert "prior_context" in scoped
        assert isinstance(scoped["prior_context"], str)
        assert "tech_comparator" in scoped["prior_context"]
        # Should NOT include findings from same agent type
        assert "implementation_planner" not in scoped["prior_context"]

    def test_include_other_findings(self, sample_full_state: AnalysisState) -> None:
        """Test that include_other_findings adds detailed prior_context."""
        scope = ContextScope(
            include=["analysis_id"],
            include_other_findings=True,
        )

        scoped = build_scoped_context(
            sample_full_state,
            "implementation_planner",
            scope=scope,
        )

        # Should include prior_context with findings
        assert "prior_context" in scoped
        prior_context = scoped["prior_context"]
        assert isinstance(prior_context, str)
        assert "tech_comparator" in prior_context
        assert "security_auditor" in prior_context

    def test_missing_fields(self, sample_full_state: AnalysisState) -> None:
        """Test handling of fields not present in state."""
        scope = ContextScope(include=["analysis_id", "nonexistent_field", "content_type"])

        scoped = build_scoped_context(
            sample_full_state,
            "security_auditor",
            scope=scope,
        )

        # Should include only fields that exist
        assert "analysis_id" in scoped
        assert "content_type" in scoped
        assert "nonexistent_field" not in scoped

    def test_empty_state(self) -> None:
        """Test scoping with empty state."""
        empty_state = AnalysisState()

        scope = ContextScope(include=["analysis_id", "content_ref"])

        scoped = build_scoped_context(
            empty_state,
            "security_auditor",
            scope=scope,
        )

        # Should return empty scoped state
        assert len(scoped) == 0

    def test_default_scope_for_known_agent(self, sample_full_state: AnalysisState) -> None:
        """Test that known agents use their configured scope."""
        scoped = build_scoped_context(
            sample_full_state,
            "security_auditor",
        )

        # Should use the configured scope from AGENT_SCOPES
        expected_scope = AGENT_SCOPES["security_auditor"]
        for field in expected_scope.include:
            if field in sample_full_state:
                assert field in scoped

    def test_default_scope_for_unknown_agent(self, sample_full_state: AnalysisState) -> None:
        """Test that unknown agents get a safe default scope."""
        scoped = build_scoped_context(
            sample_full_state,
            "unknown_agent_type",
        )

        # Should use default minimal scope
        assert "analysis_id" in scoped
        assert "content_ref" in scoped
        assert "content_type" in scoped
        assert "skill_level" in scoped

        # Should NOT include large fields
        assert "raw_content" not in scoped
        assert "extraction_metadata" not in scoped

    def test_size_reduction(self, sample_full_state: AnalysisState) -> None:
        """Test that scoped state is significantly smaller than full state."""
        scope = ContextScope(include=["analysis_id", "content_ref", "content_type"])

        scoped = build_scoped_context(
            sample_full_state,
            "security_auditor",
            scope=scope,
        )

        # Estimate sizes
        full_size = len(str(sample_full_state).encode("utf-8"))
        scoped_size = len(str(scoped).encode("utf-8"))

        # Scoped should be significantly smaller
        assert scoped_size < full_size
        # Should achieve at least 50% reduction for this test case
        reduction_pct = ((full_size - scoped_size) / full_size) * 100
        assert reduction_pct > 50


class TestTranslateFindings:
    """Test translate_findings function."""

    def test_empty_findings(self) -> None:
        """Test with no findings."""
        result = translate_findings([], "security_auditor")
        assert result == ""

    def test_single_finding(self) -> None:
        """Test with single finding from another agent."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {
                    "technologies": ["Python", "FastAPI"],
                    "comparisons": ["FastAPI vs Flask"],
                },
            }
        ]

        result = translate_findings(findings, "security_auditor", include_findings=False)

        assert "Prior Analysis Context" in result
        assert "tech_comparator" in result
        assert "key insights" in result

    def test_multiple_findings(self) -> None:
        """Test with multiple findings."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {"technologies": ["Python", "FastAPI"]},
            },
            {
                "agent_type": "dependency_mapper",
                "findings": {"dependencies": ["fastapi", "pydantic", "sqlalchemy"]},
            },
        ]

        result = translate_findings(findings, "security_auditor", include_findings=False)

        assert "tech_comparator" in result
        assert "dependency_mapper" in result
        assert result.count("\n") >= 2  # Should have multiple lines

    def test_exclude_same_agent(self) -> None:
        """Test that findings from the same agent are excluded."""
        findings = [
            {
                "agent_type": "security_auditor",
                "findings": {"security_risks": []},
            },
            {
                "agent_type": "tech_comparator",
                "findings": {"technologies": []},
            },
        ]

        result = translate_findings(findings, "security_auditor")

        # Should NOT include security_auditor (same agent)
        assert "security_auditor" not in result
        # Should include tech_comparator
        assert "tech_comparator" in result

    def test_include_findings_detailed(self) -> None:
        """Test with include_findings=True for detailed summary."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {
                    "technologies": ["Python", "FastAPI", "PostgreSQL"],
                    "comparisons": ["FastAPI vs Flask"],
                },
            }
        ]

        result = translate_findings(findings, "security_auditor", include_findings=True)

        assert "tech_comparator" in result
        # Should include summary of findings
        assert "technologies" in result or "comparisons" in result

    def test_include_findings_summary_only(self) -> None:
        """Test with include_findings=False for summary only."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {
                    "technologies": ["Python", "FastAPI", "PostgreSQL"],
                    "comparisons": ["FastAPI vs Flask"],
                },
            }
        ]

        result = translate_findings(findings, "security_auditor", include_findings=False)

        assert "tech_comparator" in result
        assert "key insights" in result

    def test_missing_agent_type(self) -> None:
        """Test handling of findings without agent_type."""
        findings = [
            {
                "findings": {"some_data": ["value"]},
            }
        ]

        result = translate_findings(findings, "security_auditor")

        # Should handle gracefully
        assert "unknown" in result.lower() or result == ""

    def test_empty_findings_dict(self) -> None:
        """Test with findings that have empty data."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {},
            }
        ]

        result = translate_findings(findings, "security_auditor")

        # Should still create context mentioning the agent
        assert "tech_comparator" in result


class TestAgentScopes:
    """Test AGENT_SCOPES configuration."""

    def test_all_agents_have_scopes(self) -> None:
        """Test that all expected agents have scope configurations."""
        expected_agents = [
            "security_auditor",
            "tech_comparator",
            "implementation_planner",
            "code_quality_critic",
            "dependency_mapper",
            "practical_applicator",
            "learning_path_designer",
            "reporter",
        ]

        for agent in expected_agents:
            assert agent in AGENT_SCOPES, f"Agent {agent} missing from AGENT_SCOPES"

    def test_all_scopes_valid(self) -> None:
        """Test that all scope configurations are valid."""
        for agent_type, scope in AGENT_SCOPES.items():
            # Should be a ContextScope instance
            assert isinstance(scope, ContextScope)

            # Should have include fields
            assert isinstance(scope.include, list)
            assert len(scope.include) > 0, f"Agent {agent_type} has no included fields"

            # All should include analysis_id (required)
            assert "analysis_id" in scope.include, f"Agent {agent_type} missing analysis_id"

    def test_scopes_minimal(self) -> None:
        """Test that scopes are minimal (typically 3-5 fields)."""
        for agent_type, scope in AGENT_SCOPES.items():
            # Most agents should need only 3-5 fields
            assert len(scope.include) <= 6, (
                f"Agent {agent_type} includes too many fields: {len(scope.include)}"
            )

    def test_no_raw_content_in_scopes(self) -> None:
        """Test that no agent scope includes raw_content (should use content_ref)."""
        for agent_type, scope in AGENT_SCOPES.items():
            assert "raw_content" not in scope.include, (
                f"Agent {agent_type} includes deprecated raw_content field"
            )


class TestContentSignalsInjection:
    """Test content_signals injection for comparison-aware thresholds (Issue #299-304)."""

    def test_content_signals_injected_when_in_scope(self) -> None:
        """Test that content_signals is injected when agent scope includes it."""
        # Create state with supervisor_decision containing content_signals
        state = AnalysisState(
            analysis_id="test-123",
            url="https://example.com",
            content_type="article",
            skill_level="intermediate",
            content_ref=ContentRef(
                uri="analysis://test-123/content",
                summary="LangChain vs LlamaIndex comparison",
                size_bytes=5000,
                content_type="text/markdown",
                available_sections=["summary", "full"],
            ),
            supervisor_decision={
                "agents": ["tech_comparator"],
                "agent_expectations": {
                    "tech_comparator": "full_analysis",
                },
                "content_signals": {
                    "richness_score": 6.2,
                    "genre": "research",
                    "has_comparisons": True,  # Key field for threshold adjustment
                    "coverage_summary": "technology comparisons",
                },
            },
        )

        # tech_comparator scope includes content_signals
        scoped = build_scoped_context(state, "tech_comparator")

        # Should include content_signals
        assert "content_signals" in scoped, "content_signals should be injected for tech_comparator"
        assert scoped["content_signals"]["has_comparisons"] is True
        assert scoped["content_signals"]["richness_score"] == 6.2

    def test_content_signals_not_injected_when_not_in_scope(self) -> None:
        """Test that content_signals is NOT injected when agent scope doesn't include it."""
        state = AnalysisState(
            analysis_id="test-123",
            url="https://example.com",
            content_type="article",
            skill_level="intermediate",
            content_ref=ContentRef(
                uri="analysis://test-123/content",
                summary="Test article",
                size_bytes=5000,
                content_type="text/markdown",
                available_sections=["summary", "full"],
            ),
            supervisor_decision={
                "agents": ["security_auditor"],
                "agent_expectations": {
                    "security_auditor": "full_analysis",
                },
                "content_signals": {
                    "has_comparisons": True,
                },
            },
        )

        # security_auditor scope does NOT include content_signals
        scoped = build_scoped_context(state, "security_auditor")

        # Should NOT include content_signals
        assert "content_signals" not in scoped, "content_signals should NOT be injected for security_auditor"

    def test_agents_with_content_signals_in_scope(self) -> None:
        """Test that expected agents have content_signals in their scope."""
        # These agents need content_signals for comparison-aware thresholds
        agents_needing_content_signals = [
            "tech_comparator",
            "trend_validator",
            "implementation_planner",
            "dependency_mapper",
        ]

        for agent in agents_needing_content_signals:
            scope = AGENT_SCOPES.get(agent)
            assert scope is not None, f"Agent {agent} should have a scope"
            assert "content_signals" in scope.include, (
                f"Agent {agent} should have content_signals in scope for comparison-aware thresholds"
            )


class TestScopedState:
    """Test ScopedState type."""

    def test_scoped_state_is_dict(self) -> None:
        """Test that ScopedState is a dict."""
        scoped = ScopedState()
        assert isinstance(scoped, dict)

    def test_scoped_state_usage(self) -> None:
        """Test ScopedState can be used like a normal dict."""
        scoped = ScopedState()
        scoped["analysis_id"] = "test-123"
        scoped["content_type"] = "article"

        assert scoped["analysis_id"] == "test-123"
        assert scoped["content_type"] == "article"
        assert len(scoped) == 2
