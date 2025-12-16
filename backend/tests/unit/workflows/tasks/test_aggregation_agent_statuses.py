"""Unit tests for agent status tracking in aggregation."""

from unittest.mock import AsyncMock, patch

import pytest

from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.tasks.aggregate_findings import aggregate_findings

@pytest.mark.unit


@pytest.fixture
def state_with_selected_agents():
    """State with supervisor_decision containing selected agents."""
    return {
        "analysis_id": "test-analysis-id",
        "supervisor_decision": {
            "agents": ["tech_comparator", "security_auditor", "implementation_planner"],
            "reasoning": "Tech content needs analysis",
            "confidence": 0.9,
        },
        "agent_findings": [
            {
                "agent_type": "tech_comparator",
                "findings": {"primary_tech": "React", "alternatives": ["Vue"]},
                "confidence_score": 0.85,
                "processing_time_ms": 1000,
            },
            {
                "agent_type": "security_auditor",
                "findings": {"vulnerabilities": [], "recommendations": []},
                "confidence_score": 0.90,
                "processing_time_ms": 1200,
            },
            # implementation_planner is selected but has no findings (failed)
        ],
    }


@pytest.fixture
def state_with_all_successful():
    """State where all selected agents succeeded."""
    return {
        "analysis_id": "test-analysis-id",
        "supervisor_decision": {
            "agents": ["tech_comparator", "security_auditor"],
            "reasoning": "Tech content needs analysis",
            "confidence": 0.9,
        },
        "agent_findings": [
            {
                "agent_type": "tech_comparator",
                "findings": {"primary_tech": "React"},
                "confidence_score": 0.85,
                "processing_time_ms": 1000,
            },
            {
                "agent_type": "security_auditor",
                "findings": {"vulnerabilities": []},
                "confidence_score": 0.90,
                "processing_time_ms": 1200,
            },
        ],
    }


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.emit_aggregation_started", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.synthesize_with_llm", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.extract_quick_reference")
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.detect_conflicts")
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.detect_coverage_gaps")
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.calculate_coverage_score")
async def test_aggregate_findings_tracks_agent_statuses(
    mock_coverage_score,
    mock_coverage_gaps,
    mock_conflicts,
    mock_quick_ref,
    mock_synthesize,
    mock_emit,
    state_with_selected_agents,
):
    """Test that aggregate_findings builds agent_statuses correctly."""
    # Mock dependencies
    mock_coverage_score.return_value = 0.85
    mock_coverage_gaps.return_value = []
    mock_conflicts.return_value = []
    mock_quick_ref.return_value = None
    mock_synthesize.return_value = {
        "summary": "Test summary",
        "key_insights": [],
        "recommendations": [],
    }

    result = await aggregate_findings(state_with_selected_agents)

    # Verify aggregated_insights contains agent_statuses
    assert "aggregated_insights" in result
    aggregated = result["aggregated_insights"]
    assert "agent_statuses" in aggregated

    agent_statuses = aggregated["agent_statuses"]
    # tech_comparator and security_auditor should be "success" (have findings)
    assert agent_statuses["tech_comparator"] == "success"
    assert agent_statuses["security_auditor"] == "success"
    # implementation_planner should be "failed" (selected but no findings)
    assert agent_statuses["implementation_planner"] == "failed"

    # Verify detect_coverage_gaps was called with selected_agents
    assert mock_coverage_gaps.called
    call_kwargs = mock_coverage_gaps.call_args.kwargs
    assert "selected_agents" in call_kwargs
    assert call_kwargs["selected_agents"] == [
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
    ]


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.emit_aggregation_started", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.synthesize_with_llm", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.extract_quick_reference")
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.detect_conflicts")
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.detect_coverage_gaps")
@patch("app.domains.analysis.workflows.tasks.aggregate_findings.calculate_coverage_score")
async def test_aggregate_findings_all_successful_agents(
    mock_coverage_score,
    mock_coverage_gaps,
    mock_conflicts,
    mock_quick_ref,
    mock_synthesize,
    mock_emit,
    state_with_all_successful,
):
    """Test agent_statuses when all selected agents succeeded."""
    # Mock dependencies
    mock_coverage_score.return_value = 1.0
    mock_coverage_gaps.return_value = []
    mock_conflicts.return_value = []
    mock_quick_ref.return_value = None
    mock_synthesize.return_value = {
        "summary": "Test summary",
        "key_insights": [],
        "recommendations": [],
    }

    result = await aggregate_findings(state_with_all_successful)

    # Verify all agents are marked as success
    aggregated = result["aggregated_insights"]
    agent_statuses = aggregated["agent_statuses"]
    assert agent_statuses["tech_comparator"] == "success"
    assert agent_statuses["security_auditor"] == "success"
    # No failed agents
    assert "failed" not in agent_statuses.values()
