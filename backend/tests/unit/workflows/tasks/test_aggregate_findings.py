"""Unit tests for aggregate_findings task."""

from unittest.mock import patch

import pytest

from app.workflows.state import AnalysisState
from app.workflows.tasks.aggregate_findings import aggregate_findings
from app.workflows.tasks.aggregation import validate_and_parse_findings
from app.workflows.tasks.aggregation_helpers import (
    calculate_coverage_score,
    detect_conflicts,
    detect_coverage_gaps,
    format_findings_for_llm,
)


@pytest.fixture
def sample_agent_findings():
    """Sample agent findings for testing."""
    return [
        {
            "agent_type": "tech_comparator",
            "findings": {
                "primary_tech": "LangGraph",
                "alternatives": ["LangChain Agents"],
                "comparison": {
                    "LangGraph": {
                        "pros": ["Low-level control"],
                        "cons": ["Steeper learning curve"],
                    }
                },
                "recommendation": "Use LangGraph for production workflows",
            },
            "confidence_score": 0.85,
            "processing_time_ms": 1234,
        },
        {
            "agent_type": "security_auditor",
            "findings": {
                "security_risks": [
                    {
                        "risk_type": "authentication",
                        "severity": "high",
                        "description": "Missing API key validation",
                    }
                ],
                "recommendation": "Address authentication before production",
            },
            "confidence_score": 0.90,
            "processing_time_ms": 987,
        },
        {
            "agent_type": "implementation_planner",
            "findings": {
                "prerequisites": ["Python 3.13"],
                "steps": [{"step": 1, "action": "Install dependencies"}],
                "recommendation": "Follow step-by-step implementation plan",
            },
            "confidence_score": 0.80,
            "processing_time_ms": 1456,
        },
    ]


@pytest.fixture
def sample_state(sample_agent_findings):
    """Sample analysis state for testing."""
    return AnalysisState(
        analysis_id="test-analysis-id",
        url="https://example.com",
        content_type="article",
        raw_content="Test content",
        extraction_metadata={},
        content_embedding=[],
        supervisor_decision={},
        agent_findings=sample_agent_findings,
    )


class TestValidateAndParseFindings:
    """Test findings validation and parsing."""

    def test_validate_all_findings_present(self, sample_agent_findings):
        """Test validation with all findings present."""
        validated, agent_types, confidence_scores = validate_and_parse_findings(
            sample_agent_findings
        )

        assert len(validated) == 3
        assert len(agent_types) == 3
        assert "tech_comparator" in agent_types
        assert "security_auditor" in agent_types
        assert "implementation_planner" in agent_types
        assert confidence_scores["tech_comparator"] == 0.85
        assert confidence_scores["security_auditor"] == 0.90

    def test_validate_empty_findings(self):
        """Test validation with empty findings list."""
        validated, agent_types, confidence_scores = validate_and_parse_findings([])

        assert len(validated) == 0
        assert len(agent_types) == 0
        assert len(confidence_scores) == 0

    def test_validate_missing_agent_type(self):
        """Test validation skips findings without agent_type."""
        findings = [{"findings": {"test": "data"}}]  # Missing agent_type

        validated, agent_types, _confidence_scores = validate_and_parse_findings(findings)

        assert len(validated) == 0
        assert len(agent_types) == 0

    def test_validate_empty_findings_data(self):
        """Test validation handles empty findings data."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {},  # Empty findings
                "confidence_score": 0.75,
            }
        ]

        validated, agent_types, confidence_scores = validate_and_parse_findings(findings)

        assert len(validated) == 1  # Still included, but marked as empty
        assert agent_types == ["tech_comparator"]
        assert confidence_scores["tech_comparator"] == 0.75

    def test_validate_invalid_finding_type(self):
        """Test validation skips invalid finding types."""
        findings = ["not a dict", {"agent_type": "valid", "findings": {}}]

        validated, agent_types, _confidence_scores = validate_and_parse_findings(findings)

        assert len(validated) == 1  # Only valid one included
        assert "valid" in agent_types


class TestDetectConflicts:
    """Test conflict detection."""

    def test_detect_no_conflicts(self, sample_agent_findings):
        """Test conflict detection with no conflicts."""
        conflicts = detect_conflicts(sample_agent_findings)

        # These findings don't have direct contradictions
        assert isinstance(conflicts, list)

    def test_detect_tech_security_conflict(self):
        """Test detection of tech vs security conflict."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {"recommendation": "Use LangGraph for production workflows"},
            },
            {
                "agent_type": "security_auditor",
                "findings": {
                    "recommendation": "Warning: LangGraph has authentication vulnerabilities"
                },
            },
        ]

        conflicts = detect_conflicts(findings)

        # Should detect conflict between tech recommendation and security warning
        assert len(conflicts) > 0
        assert any("tech_comparator" in str(c) for c in conflicts)
        assert any("security_auditor" in str(c) for c in conflicts)

    def test_detect_empty_findings(self):
        """Test conflict detection with empty findings."""
        conflicts = detect_conflicts([])

        assert conflicts == []

    def test_detect_missing_recommendations(self):
        """Test conflict detection when recommendations are missing."""
        findings = [
            {
                "agent_type": "tech_comparator",
                "findings": {"primary_tech": "LangGraph"},  # No recommendation
            }
        ]

        conflicts = detect_conflicts(findings)

        # No conflicts if no recommendations
        assert conflicts == []


class TestFormatFindingsForLLM:
    """Test formatting findings for LLM prompt."""

    def test_format_findings(self, sample_agent_findings):
        """Test formatting with sample findings."""
        conflicts = []
        confidence_scores = {
            "tech_comparator": 0.85,
            "security_auditor": 0.90,
            "implementation_planner": 0.80,
        }

        formatted = format_findings_for_llm(sample_agent_findings, conflicts, confidence_scores)

        assert "AGENT FINDINGS" in formatted
        assert "TECH COMPARATOR" in formatted.upper() or "tech_comparator" in formatted
        assert "SECURITY AUDITOR" in formatted.upper() or "security_auditor" in formatted
        assert "0.85" in formatted
        assert "0.90" in formatted

    def test_format_with_conflicts(self, sample_agent_findings):
        """Test formatting includes conflicts."""
        conflicts = [
            {
                "agent_1": "tech_comparator",
                "agent_2": "security_auditor",
                "conflict": "Tech recommends, security warns",
            }
        ]
        confidence_scores = {"tech_comparator": 0.85, "security_auditor": 0.90}

        formatted = format_findings_for_llm(sample_agent_findings[:2], conflicts, confidence_scores)

        assert "CONFLICTS DETECTED" in formatted
        assert "Tech recommends" in formatted

    def test_format_confidence_scores(self, sample_agent_findings):
        """Test formatting includes confidence scores."""
        conflicts = []
        confidence_scores = {
            "tech_comparator": 0.85,
            "security_auditor": 0.90,
            "implementation_planner": 0.80,
        }

        formatted = format_findings_for_llm(sample_agent_findings, conflicts, confidence_scores)

        assert "CONFIDENCE SCORES" in formatted
        assert "0.90" in formatted  # Highest should appear


class TestAggregateFindings:
    """Test aggregate_findings function."""

    @pytest.mark.asyncio
    async def test_aggregate_all_agents_present(self, sample_state):
        """Test aggregation with all agents present."""
        # Mock the LLM agent invocation
        mock_structured_response = {
            "executive_summary": "Test summary. Second sentence. Third sentence.",
            "key_findings": [
                "Finding 1",
                "Finding 2",
                "Finding 3",
            ],
            "synthesis": {
                "technical_analysis": "Technical insights",
                "implementation_guidance": "Implementation steps",
                "risk_assessment": "Risk analysis",
                "recommendations": "Final recommendations",
            },
            "conflicts_resolved": [],
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch(
                "app.workflows.tasks.aggregate_findings.emit_aggregation_started"
            ) as mock_sse_start,
            patch(
                "app.workflows.tasks.aggregate_findings.emit_aggregation_complete"
            ) as mock_sse_complete,
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            assert "aggregated_insights" in result
            insights = result["aggregated_insights"]
            assert insights["executive_summary"] == "Test summary. Second sentence. Third sentence."
            assert len(insights["key_findings"]) == 3
            assert "metadata" in insights
            assert insights["metadata"]["total_agents"] == 3

    @pytest.mark.asyncio
    async def test_aggregate_partial_agents(self):
        """Test aggregation with only some agents executed."""
        state = AnalysisState(
            analysis_id="test-id",
            url="https://example.com",
            content_type="article",
            raw_content="Test",
            extraction_metadata={},
            content_embedding=[],
            supervisor_decision={},
            agent_findings=[
                {
                    "agent_type": "tech_comparator",
                    "findings": {"recommendation": "Use LangGraph"},
                    "confidence_score": 0.85,
                }
            ],
        )

        mock_structured_response = {
            "executive_summary": "Summary. Second sentence.",
            "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(state)

            assert result["aggregated_insights"]["metadata"]["total_agents"] == 1

    @pytest.mark.asyncio
    async def test_aggregate_empty_findings(self):
        """Test aggregation with no agent findings."""
        state = AnalysisState(
            analysis_id="test-id",
            url="https://example.com",
            content_type="article",
            raw_content="Test",
            extraction_metadata={},
            content_embedding=[],
            supervisor_decision={},
            agent_findings=[],
        )

        with (
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            result = await aggregate_findings(state)

            assert "aggregated_insights" in result
            insights = result["aggregated_insights"]
            assert insights["metadata"]["total_agents"] == 0
            assert "No agent findings available" in insights["executive_summary"]

    @pytest.mark.asyncio
    async def test_aggregate_conflict_resolution(self, sample_state):
        """Test aggregation detects and resolves conflicts."""
        # Add conflicting findings
        sample_state["agent_findings"].append(
            {
                "agent_type": "performance_analyst",
                "findings": {"recommendation": "Avoid using LangGraph due to performance issues"},
                "confidence_score": 0.70,
            }
        )

        mock_structured_response = {
            "executive_summary": "Summary. Second. Third.",
            "key_findings": ["F1", "F2", "F3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [
                {
                    "conflict": "Tech recommends, performance warns",
                    "resolution": "Prioritized tech recommendation",
                    "priority_agent": "tech_comparator",
                    "reasoning": "Higher confidence score",
                }
            ],
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            assert len(insights["conflicts_resolved"]) > 0

    @pytest.mark.asyncio
    async def test_aggregate_confidence_prioritization(self, sample_state):
        """Test aggregation prioritizes higher confidence agents."""
        mock_structured_response = {
            "executive_summary": "Summary. Second. Third.",
            "key_findings": ["F1", "F2", "F3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            metadata = insights["metadata"]
            # security_auditor has highest confidence (0.90)
            assert metadata["confidence_max"] == 0.90
            assert metadata["confidence_avg"] > 0.80

    @pytest.mark.asyncio
    async def test_aggregate_llm_error_handling(self, sample_state):
        """Test graceful fallback when LLM synthesis fails."""
        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            # Simulate LLM error
            mock_synthesize.side_effect = Exception("LLM API error")

            result = await aggregate_findings(sample_state)

            # Should return fallback aggregation
            assert "aggregated_insights" in result
            insights = result["aggregated_insights"]
            assert insights["metadata"]["fallback_used"] is True
            assert insights["metadata"]["llm_synthesis_failed"] is True
            assert "Synthesized findings from" in insights["executive_summary"]

    @pytest.mark.asyncio
    async def test_aggregate_executive_summary_validation(self, sample_state):
        """Test executive summary is validated to 2-3 sentences."""
        # LLM returns 4 sentences
        mock_structured_response = {
            "executive_summary": (
                "First sentence. Second sentence. Third sentence. Fourth sentence."
            ),
            "key_findings": ["F1", "F2", "F3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Should be truncated to 3 sentences
            sentences = [s.strip() for s in insights["executive_summary"].split(".") if s.strip()]
            assert len(sentences) <= 3

    @pytest.mark.asyncio
    async def test_aggregate_key_findings_validation(self, sample_state):
        """Test key findings is validated to 3-7 items."""
        # LLM returns 8 items
        mock_structured_response = {
            "executive_summary": "Summary. Second. Third.",
            "key_findings": ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Should be truncated to 7 items
            assert len(insights["key_findings"]) <= 7

        # Test with too few items (should pad)
        mock_structured_response["key_findings"] = ["F1", "F2"]

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Should be padded to at least 3 items
            assert len(insights["key_findings"]) >= 3


class TestDetectCoverageGaps:
    """Test coverage gap detection."""

    def test_detect_coverage_gaps_with_partial_agents(self):
        """Test gap detection when only some agents contribute."""
        contributing_agents = ["implementation_planner", "security_auditor"]

        gaps = detect_coverage_gaps(contributing_agents)

        # Should detect gaps for all other agents (6 gaps for 2 contributing out of 8)
        assert len(gaps) == 6
        gap_agent_types = [gap["missing_agent"] for gap in gaps]
        assert "implementation_planner" not in gap_agent_types
        assert "security_auditor" not in gap_agent_types
        assert "tech_comparator" in gap_agent_types
        assert "performance_analyst" in gap_agent_types

        # Verify gap structure
        for gap in gaps:
            assert "missing_agent" in gap
            assert "missing_perspective" in gap
            assert "impact" in gap
            assert isinstance(gap["missing_agent"], str)
            assert isinstance(gap["missing_perspective"], str)
            assert isinstance(gap["impact"], str)

    def test_detect_coverage_gaps_with_all_agents(self):
        """Test gap detection when all agents contribute."""
        # Get all analysis agents (8 total)
        from app.core.agent_config import AGENT_REGISTRY
        from app.workflows.nodes.supervisor_config import WORKFLOW_STAGES

        all_agents = [
            agent_type
            for agent_type, config in AGENT_REGISTRY.items()
            if config.agent_type not in WORKFLOW_STAGES
        ]

        gaps = detect_coverage_gaps(all_agents)

        # Should have no gaps when all agents contribute
        assert len(gaps) == 0

    def test_detect_coverage_gaps_with_no_agents(self):
        """Test gap detection when no agents contribute."""
        gaps = detect_coverage_gaps([])

        # Should detect gaps for all 8 agents
        assert len(gaps) == 8


class TestCalculateCoverageScore:
    """Test coverage score calculation."""

    def test_calculate_coverage_score_partial(self):
        """Test coverage score with partial agent contribution."""
        contributing_agents = ["implementation_planner", "security_auditor"]

        score = calculate_coverage_score(contributing_agents)

        # 2 out of 8 agents = 0.25
        assert score == 0.25

    def test_calculate_coverage_score_all(self):
        """Test coverage score when all agents contribute."""
        from app.core.agent_config import AGENT_REGISTRY
        from app.workflows.nodes.supervisor_config import WORKFLOW_STAGES

        all_agents = [
            agent_type
            for agent_type, config in AGENT_REGISTRY.items()
            if config.agent_type not in WORKFLOW_STAGES
        ]

        score = calculate_coverage_score(all_agents)

        # All 8 agents = 1.0
        assert score == 1.0

    def test_calculate_coverage_score_none(self):
        """Test coverage score with no agents."""
        score = calculate_coverage_score([])

        # 0 out of 8 agents = 0.0
        assert score == 0.0

    def test_calculate_coverage_score_half(self):
        """Test coverage score with half the agents."""
        contributing_agents = [
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
        ]

        score = calculate_coverage_score(contributing_agents)

        # 4 out of 8 agents = 0.5
        assert score == 0.5


class TestAggregationCoverageFeatures:
    """Test coverage gaps and score in aggregation output."""

    @pytest.mark.asyncio
    async def test_aggregation_includes_coverage_gaps(self, sample_state):
        """Test that aggregation includes coverage gaps in output."""
        mock_structured_response = {
            "executive_summary": "Summary. Second sentence. Third sentence.",
            "key_findings": ["F1", "F2", "F3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
            "coverage_gaps": [],
            "cross_domain_connections": [],
            "coverage_score": 0.375,
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Coverage gaps should be present (even if empty)
            assert "coverage_gaps" in insights
            # Should have gaps for missing agents (3 contributing, 5 missing)
            assert len(insights["coverage_gaps"]) == 5

    @pytest.mark.asyncio
    async def test_aggregation_includes_coverage_score(self, sample_state):
        """Test that aggregation includes coverage score in output."""
        mock_structured_response = {
            "executive_summary": "Summary. Second sentence. Third sentence.",
            "key_findings": ["F1", "F2", "F3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
            "coverage_gaps": [],
            "cross_domain_connections": [],
            "coverage_score": 0.375,
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Coverage score should be present
            assert "coverage_score" in insights
            # 3 agents out of 8 = 0.375
            assert insights["coverage_score"] == 0.375
            assert isinstance(insights["coverage_score"], float)
            assert 0.0 <= insights["coverage_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_aggregation_coverage_gaps_structure(self, sample_state):
        """Test that coverage gaps have correct structure."""
        mock_structured_response = {
            "executive_summary": "Summary. Second sentence. Third sentence.",
            "key_findings": ["F1", "F2", "F3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
            "coverage_gaps": [],
            "cross_domain_connections": [],
            "coverage_score": 0.375,
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            gaps = insights["coverage_gaps"]

            # Verify gap structure
            for gap in gaps:
                assert "missing_agent" in gap
                assert "missing_perspective" in gap
                assert "impact" in gap
                assert isinstance(gap["missing_agent"], str)
                assert isinstance(gap["missing_perspective"], str)
                assert isinstance(gap["impact"], str)

    @pytest.mark.asyncio
    async def test_aggregation_cross_domain_connections_schema(self, sample_state):
        """Test that cross_domain_connections field is present in schema."""
        mock_structured_response = {
            "executive_summary": "Summary. Second sentence. Third sentence.",
            "key_findings": ["F1", "F2", "F3"],
            "synthesis": {
                "technical_analysis": "Analysis",
                "implementation_guidance": "Guidance",
                "risk_assessment": "Assessment",
                "recommendations": "Recommendations",
            },
            "conflicts_resolved": [],
            "coverage_gaps": [],
            "cross_domain_connections": [
                {
                    "domains": ["security", "performance"],
                    "connection": "Security measures add latency overhead",
                    "agents_involved": ["security_auditor", "performance_analyst"],
                }
            ],
            "coverage_score": 0.375,
        }

        with (
            patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
            patch("app.workflows.tasks.aggregate_findings.emit_aggregation_complete"),
        ):
            mock_synthesize.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Cross-domain connections should be present
            assert "cross_domain_connections" in insights
            assert isinstance(insights["cross_domain_connections"], list)

            # Verify connection structure if present
            if insights["cross_domain_connections"]:
                conn = insights["cross_domain_connections"][0]
                assert "domains" in conn
                assert "connection" in conn
                assert "agents_involved" in conn
                assert len(conn["domains"]) == 2
