"""Unit tests for agent result processing rich details extraction."""

import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.result_processing import (

    _count_insights,
    _extract_findings_summary,
    process_agent_result,
)


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_analysis_id():
    """Sample analysis ID."""
    return uuid.uuid4()


def test_extract_findings_summary_tech_comparator():
    """Test _extract_findings_summary for tech_comparator."""
    findings = {
        "primary_tech": "React",
        "alternatives": ["Vue", "Angular", "Svelte"],
    }
    summary = _extract_findings_summary(findings, "tech_comparator")
    assert "React" in summary
    assert "Vue" in summary or "Angular" in summary


def test_extract_findings_summary_security_auditor():
    """Test _extract_findings_summary for security_auditor."""
    findings = {
        "vulnerabilities": [{"risk_type": "XSS", "severity": "high"}],
        "recommendations": [{"type": "input_validation", "priority": "high"}],
    }
    summary = _extract_findings_summary(findings, "security_auditor")
    assert "1" in summary  # 1 vulnerability
    assert "1" in summary  # 1 recommendation


def test_extract_findings_summary_implementation_planner():
    """Test _extract_findings_summary for implementation_planner."""
    findings = {
        "implementation_steps": [
            {"step": 1, "description": "Setup"},
            {"step": 2, "description": "Configure"},
            {"step": 3, "description": "Deploy"},
        ],
    }
    summary = _extract_findings_summary(findings, "implementation_planner")
    assert "3" in summary  # 3 steps


def test_count_insights_tech_comparator():
    """Test _count_insights for tech_comparator."""
    findings = {
        "alternatives": ["Vue", "Angular", "Svelte"],
    }
    count = _count_insights(findings, "tech_comparator")
    assert count == 3


def test_count_insights_security_auditor():
    """Test _count_insights for security_auditor."""
    findings = {
        "vulnerabilities": [{"risk_type": "XSS"}],
        "recommendations": [{"type": "input_validation"}, {"type": "encryption"}],
    }
    count = _count_insights(findings, "security_auditor")
    assert count == 3  # 1 vulnerability + 2 recommendations


def test_count_insights_implementation_planner():
    """Test _count_insights for implementation_planner."""
    findings = {
        "implementation_steps": [
            {"step": 1},
            {"step": 2},
            {"step": 3},
            {"step": 4},
        ],
    }
    count = _count_insights(findings, "implementation_planner")
    assert count == 4


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_emits_rich_details(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that process_agent_result emits findings_summary and insights_count."""
    findings = {
        "primary_tech": "React",
        "alternatives": ["Vue", "Angular"],
        "confidence_score": 0.85,
    }
    agent_type = "tech_comparator"
    start_time = time.time()

    await process_agent_result(
        findings=findings,
        analysis_id=sample_analysis_id,
        agent_type=agent_type,
        session=mock_session,
        start_time=start_time,
    )

    # Verify emit_agent_progress was called with rich details
    assert mock_emit.called
    call_kwargs = mock_emit.call_args.kwargs
    assert "findings_summary" in call_kwargs
    assert "insights_count" in call_kwargs
    assert "confidence_score" in call_kwargs

    # Verify findings_summary is human-readable
    assert isinstance(call_kwargs["findings_summary"], str)
    assert len(call_kwargs["findings_summary"]) > 0

    # Verify insights_count is correct
    assert call_kwargs["insights_count"] == 2  # 2 alternatives

    # Verify confidence_score is passed
    assert call_kwargs["confidence_score"] == 0.85


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_emits_rich_details_security_auditor(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test rich details emission for security_auditor."""
    findings = {
        "vulnerabilities": [
            {"risk_type": "XSS", "severity": "high"},
            {"risk_type": "CSRF", "severity": "medium"},
        ],
        "recommendations": [{"type": "input_validation", "priority": "high"}],
        "confidence_score": 0.90,
    }
    agent_type = "security_auditor"
    start_time = time.time()

    await process_agent_result(
        findings=findings,
        analysis_id=sample_analysis_id,
        agent_type=agent_type,
        session=mock_session,
        start_time=start_time,
    )

    # Verify emit_agent_progress was called with rich details
    call_kwargs = mock_emit.call_args.kwargs
    assert "findings_summary" in call_kwargs
    assert "insights_count" in call_kwargs
    assert call_kwargs["insights_count"] == 3  # 2 vulnerabilities + 1 recommendation
    assert "2" in call_kwargs["findings_summary"]  # 2 vulnerabilities
    assert "1" in call_kwargs["findings_summary"]  # 1 recommendation
