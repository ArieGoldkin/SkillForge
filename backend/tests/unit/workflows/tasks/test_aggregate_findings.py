"""Unit tests for aggregate_findings task."""

from unittest.mock import patch

import pytest

from app.workflows.state import AnalysisState
from app.workflows.tasks.aggregate_findings import aggregate_findings
from app.workflows.tasks.aggregation_helpers import (
    detect_conflicts,
    format_findings_for_llm,
    validate_and_parse_findings,
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

        validated, agent_types, confidence_scores = validate_and_parse_findings(findings)

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

        validated, agent_types, confidence_scores = validate_and_parse_findings(findings)

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
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch(
                "app.workflows.tasks.aggregate_findings.extract_structured_response"
            ) as mock_extract,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event") as mock_sse,
        ):
            mock_invoke.return_value = {"structured_response": mock_structured_response}
            mock_extract.return_value = mock_structured_response

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
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch(
                "app.workflows.tasks.aggregate_findings.extract_structured_response"
            ) as mock_extract,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event"),
        ):
            mock_invoke.return_value = {"structured_response": mock_structured_response}
            mock_extract.return_value = mock_structured_response

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

        with patch("app.workflows.tasks.aggregate_findings.emit_streaming_event") as mock_sse:
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
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch(
                "app.workflows.tasks.aggregate_findings.extract_structured_response"
            ) as mock_extract,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event"),
        ):
            mock_invoke.return_value = {"structured_response": mock_structured_response}
            mock_extract.return_value = mock_structured_response

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
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch(
                "app.workflows.tasks.aggregate_findings.extract_structured_response"
            ) as mock_extract,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event"),
        ):
            mock_invoke.return_value = {"structured_response": mock_structured_response}
            mock_extract.return_value = mock_structured_response

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
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event"),
        ):
            # Simulate LLM error
            mock_invoke.side_effect = Exception("LLM API error")

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
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch(
                "app.workflows.tasks.aggregate_findings.extract_structured_response"
            ) as mock_extract,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event"),
        ):
            mock_invoke.return_value = {"structured_response": mock_structured_response}
            mock_extract.return_value = mock_structured_response

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
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch(
                "app.workflows.tasks.aggregate_findings.extract_structured_response"
            ) as mock_extract,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event"),
        ):
            mock_invoke.return_value = {"structured_response": mock_structured_response}
            mock_extract.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Should be truncated to 7 items
            assert len(insights["key_findings"]) <= 7

        # Test with too few items (should pad)
        mock_structured_response["key_findings"] = ["F1", "F2"]

        with (
            patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke,
            patch(
                "app.workflows.tasks.aggregate_findings.extract_structured_response"
            ) as mock_extract,
            patch("app.workflows.tasks.aggregate_findings.emit_streaming_event"),
        ):
            mock_invoke.return_value = {"structured_response": mock_structured_response}
            mock_extract.return_value = mock_structured_response

            result = await aggregate_findings(sample_state)

            insights = result["aggregated_insights"]
            # Should be padded to at least 3 items
            assert len(insights["key_findings"]) >= 3


@pytest.mark.asyncio
async def test_aggregate_findings_handles_generatorexit_gracefully(sample_state):
    """Test that GeneratorExit during LLM synthesis triggers fallback."""
    with patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke:
        # Mock invoke_agent to raise GeneratorExit (simulating timeout cancellation)
        mock_invoke.side_effect = GeneratorExit("Generator closed by timeout")

        result = await aggregate_findings(sample_state)

        # Should use fallback aggregated insights
        assert "aggregated_insights" in result
        assert isinstance(result["aggregated_insights"], dict)
        # Fallback should have basic structure
        assert "executive_summary" in result["aggregated_insights"]


@pytest.mark.asyncio
async def test_aggregate_findings_handles_timeouterror_gracefully(sample_state):
    """Test that TimeoutError during LLM synthesis triggers fallback."""
    with patch("app.workflows.tasks.aggregate_findings.invoke_agent") as mock_invoke:
        # Mock invoke_agent to raise TimeoutError
        mock_invoke.side_effect = TimeoutError("LLM synthesis exceeded timeout")

        result = await aggregate_findings(sample_state)

        # Should use fallback aggregated insights
        assert "aggregated_insights" in result
        assert isinstance(result["aggregated_insights"], dict)
        # Fallback should have basic structure
        assert "executive_summary" in result["aggregated_insights"]
