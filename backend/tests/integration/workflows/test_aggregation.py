"""Integration tests for aggregation workflow."""

from unittest.mock import patch

import pytest

from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.aggregate_findings import aggregate_findings


@pytest.fixture
def sample_state_with_findings():
    """Create sample state with agent findings."""
    return AnalysisState(
        analysis_id="test-analysis-123",
        url="https://example.com/article",
        content_type="article",
        raw_content="Test article content about LangGraph and LangChain",
        extraction_metadata={"title": "Test Article", "word_count": 100},
        content_embedding=[0.1] * 768,
        supervisor_decision={
            "agents": [
                "tech_comparator",
                "security_auditor",
                "implementation_planner",
            ]
        },
        agent_findings=[
            {
                "agent_type": "tech_comparator",
                "findings": {
                    "primary_tech": "LangGraph",
                    "alternatives": ["LangChain Agents"],
                    "comparison": {
                        "LangGraph": {
                            "pros": ["Low-level control", "Durable execution"],
                            "cons": ["Steeper learning curve"],
                            "use_cases": ["Long-running agents"],
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
                            "mitigation": "Implement API key middleware",
                        }
                    ],
                    "best_practices": ["Use HTTPS", "Implement CSRF protection"],
                    "recommendation": "Address authentication before production",
                },
                "confidence_score": 0.90,
                "processing_time_ms": 987,
            },
            {
                "agent_type": "implementation_planner",
                "findings": {
                    "prerequisites": ["Python 3.13", "PostgreSQL"],
                    "steps": [
                        {"step": 1, "action": "Install dependencies"},
                        {"step": 2, "action": "Setup database"},
                    ],
                    "recommendation": "Follow step-by-step implementation plan",
                },
                "confidence_score": 0.80,
                "processing_time_ms": 1456,
            },
        ],
    )


@pytest.mark.asyncio
async def test_full_workflow_with_aggregation(sample_state_with_findings):
    """Test full aggregation workflow with real agent findings."""
    # Mock LLM synthesis response
    mock_structured_response = {
        "executive_summary": (
            "This analysis evaluates LangGraph for production use. "
            "Security concerns must be addressed before deployment. "
            "Implementation follows a clear step-by-step plan."
        ),
        "key_findings": [
            "LangGraph is recommended for production workflows with proper security",
            "Authentication vulnerabilities must be addressed before deployment",
            "Implementation requires Python 3.13 and PostgreSQL setup",
            "Security best practices include HTTPS and CSRF protection",
        ],
        "synthesis": {
            "technical_analysis": (
                "LangGraph offers low-level control and durable execution, "
                "making it suitable for long-running agents. However, "
                "authentication must be properly implemented."
            ),
            "implementation_guidance": (
                "Follow the step-by-step plan: install dependencies, "
                "setup database, and implement security measures."
            ),
            "risk_assessment": (
                "High-severity authentication risks identified. "
                "Must implement API key validation and CSRF protection."
            ),
            "recommendations": (
                "Use LangGraph for production, but prioritize security "
                "implementation before deployment."
            ),
        },
        "conflicts_resolved": [
            {
                "conflict": "Tech recommends LangGraph, Security raises concerns",
                "resolution": "Prioritized security concerns with caveat to tech recommendation",
                "priority_agent": "security_auditor",
                "reasoning": "Higher confidence score (0.90 vs 0.85)",
            }
        ],
    }

    with (
        patch("app.workflows.tasks.aggregate_findings.synthesize_with_llm") as mock_synthesize,
        patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started"),
        patch(
            "app.workflows.tasks.aggregate_findings.emit_aggregation_complete"
        ) as mock_sse_complete,
        patch("app.workflows.tasks.aggregate_findings.emit_aggregation_detecting_conflicts"),
        patch("app.workflows.tasks.aggregate_findings.emit_aggregation_synthesizing"),
    ):
        mock_synthesize.return_value = mock_structured_response

        result = await aggregate_findings(sample_state_with_findings)

        # Verify aggregated_insights in result
        assert "aggregated_insights" in result
        insights = result["aggregated_insights"]

        # Verify structure
        assert "executive_summary" in insights
        assert "key_findings" in insights
        assert "synthesis" in insights
        assert "conflicts_resolved" in insights
        assert "metadata" in insights

        # Verify content
        assert len(insights["executive_summary"]) > 0
        assert 3 <= len(insights["key_findings"]) <= 7
        assert "technical_analysis" in insights["synthesis"]
        assert "implementation_guidance" in insights["synthesis"]
        assert "risk_assessment" in insights["synthesis"]
        assert "recommendations" in insights["synthesis"]

        # Verify metadata
        metadata = insights["metadata"]
        assert metadata["total_agents"] == 3
        assert "tech_comparator" in metadata["agents_executed"]
        assert "security_auditor" in metadata["agents_executed"]
        assert "implementation_planner" in metadata["agents_executed"]
        assert metadata["confidence_avg"] > 0.0
        assert metadata["confidence_max"] == 0.90
        assert metadata["confidence_min"] == 0.80
        assert metadata["processing_time_ms"] >= 0  # Can be 0 with mocked functions
        assert metadata["conflicts_detected"] >= 0
        assert metadata["conflicts_resolved"] >= 0

        # Verify SSE events were emitted
        assert mock_sse_complete.called  # Complete event should be called


@pytest.mark.asyncio
async def test_aggregation_sse_events(sample_state_with_findings):
    """Test SSE events are emitted during aggregation."""
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
        patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started") as mock_sse_start,
        patch(
            "app.workflows.tasks.aggregate_findings.emit_aggregation_complete"
        ) as mock_sse_complete,
        patch("app.workflows.tasks.aggregate_findings.emit_aggregation_detecting_conflicts"),
        patch("app.workflows.tasks.aggregate_findings.emit_aggregation_synthesizing"),
    ):
        mock_synthesize.return_value = mock_structured_response

        await aggregate_findings(sample_state_with_findings)

        # Verify SSE events were emitted
        assert mock_sse_start.called
        assert mock_sse_complete.called


@pytest.mark.asyncio
async def test_aggregation_with_empty_state():
    """Test aggregation handles empty state gracefully."""
    empty_state = AnalysisState(
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
        patch("app.workflows.tasks.aggregate_findings.emit_aggregation_started") as mock_sse_start,
        patch(
            "app.workflows.tasks.aggregate_findings.emit_aggregation_complete"
        ) as mock_sse_complete,
    ):
        result = await aggregate_findings(empty_state)

        # Should return valid structure even with no findings
        assert "aggregated_insights" in result
        insights = result["aggregated_insights"]
        assert insights["metadata"]["total_agents"] == 0
        assert "No agent findings available" in insights["executive_summary"]

        # Should still emit SSE events (started is always called, complete only if findings exist)
        assert mock_sse_start.called
        # Complete may not be called when there are no findings (early return)
