"""Unit tests for agent result processing with confidence score extraction."""

import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.result_processing import process_agent_result


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def sample_analysis_id():
    """Sample analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_with_confidence_score(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score is extracted from findings and passed to save_agent_finding.

    This test verifies the fix for confidence score extraction where confidence_score
    is extracted from the findings dict and passed separately to save_agent_finding(),
    while being removed from the findings dict to avoid duplication.
    """
    findings = {
        "primary_tech": "React",
        "alternatives": ["Vue", "Angular"],
        "confidence_score": 0.85,  # Confidence score in findings
    }
    agent_type = "tech_comparator"
    start_time = time.time()

    result = await process_agent_result(
        findings=findings,
        analysis_id=sample_analysis_id,
        agent_type=agent_type,
        session=mock_session,
        start_time=start_time,
    )

    # Verify save_agent_finding was called with confidence_score
    assert mock_save.called
    call_kwargs = mock_save.call_args.kwargs
    assert "confidence_score" in call_kwargs
    assert call_kwargs["confidence_score"] == 0.85

    # Verify confidence_score was removed from findings dict
    findings_passed = call_kwargs["findings"]
    assert "confidence_score" not in findings_passed
    assert findings_passed["primary_tech"] == "React"
    assert findings_passed["alternatives"] == ["Vue", "Angular"]

    # Verify result structure
    assert result["agent_type"] == agent_type
    assert result["findings"] == findings  # Original findings preserved in return
    assert "processing_time_ms" in result


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_without_confidence_score(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that process_agent_result works correctly when confidence_score is not present."""
    findings = {
        "primary_tech": "React",
        "alternatives": ["Vue", "Angular"],
        # No confidence_score
    }
    agent_type = "tech_comparator"
    start_time = time.time()

    result = await process_agent_result(
        findings=findings,
        analysis_id=sample_analysis_id,
        agent_type=agent_type,
        session=mock_session,
        start_time=start_time,
    )

    # Verify save_agent_finding was called with None confidence_score
    assert mock_save.called
    call_kwargs = mock_save.call_args.kwargs
    assert "confidence_score" in call_kwargs
    assert call_kwargs["confidence_score"] is None

    # Verify findings unchanged (no confidence_score to remove)
    findings_passed = call_kwargs["findings"]
    assert findings_passed == findings


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_confidence_score_type_conversion(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score is converted to float from int."""
    findings = {
        "primary_tech": "React",
        "confidence_score": 85,  # Integer confidence score
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

    # Verify confidence_score was converted to float
    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["confidence_score"] == 85.0
    assert isinstance(call_kwargs["confidence_score"], float)


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_invalid_confidence_score_ignored(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that invalid confidence_score values are ignored (not int/float)."""
    findings = {
        "primary_tech": "React",
        "confidence_score": "high",  # Invalid type (string)
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

    # Verify confidence_score is None (invalid value ignored)
    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["confidence_score"] is None

    # Verify invalid confidence_score was removed from findings
    findings_passed = call_kwargs["findings"]
    assert "confidence_score" not in findings_passed


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_with_confidence_score_boundary_0(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score boundary value 0.0 is extracted correctly."""
    findings = {
        "primary_tech": "React",
        "confidence_score": 0.0,  # Minimum boundary
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

    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["confidence_score"] == 0.0
    assert isinstance(call_kwargs["confidence_score"], float)


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_with_confidence_score_boundary_1(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score boundary value 1.0 is extracted correctly."""
    findings = {
        "primary_tech": "React",
        "confidence_score": 1.0,  # Maximum boundary
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

    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["confidence_score"] == 1.0
    assert isinstance(call_kwargs["confidence_score"], float)


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
@pytest.mark.parametrize("confidence_value", [0.25, 0.5, 0.75, 0.999])
async def test_process_agent_result_with_confidence_score_mid_range(
    mock_emit, mock_save, mock_session, sample_analysis_id, confidence_value
):
    """Test that mid-range confidence_score values are extracted correctly."""
    findings = {
        "primary_tech": "React",
        "confidence_score": confidence_value,
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

    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["confidence_score"] == confidence_value
    assert isinstance(call_kwargs["confidence_score"], float)


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_confidence_score_precision_preserved(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score precision is preserved (e.g., 0.123456 stays 0.123456)."""
    precision_value = 0.123456
    findings = {
        "primary_tech": "React",
        "confidence_score": precision_value,
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

    call_kwargs = mock_save.call_args.kwargs
    assert call_kwargs["confidence_score"] == precision_value
    # Verify precision is preserved (not rounded)
    assert abs(call_kwargs["confidence_score"] - precision_value) < 0.000001


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_confidence_score_removed_from_findings(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score is removed from findings dict to avoid duplication."""
    findings = {
        "primary_tech": "React",
        "alternatives": ["Vue"],
        "confidence_score": 0.85,
        "other_field": "value",
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

    call_kwargs = mock_save.call_args.kwargs
    findings_passed = call_kwargs["findings"]

    # Verify confidence_score is NOT in findings dict
    assert "confidence_score" not in findings_passed

    # Verify other fields are preserved
    assert findings_passed["primary_tech"] == "React"
    assert findings_passed["alternatives"] == ["Vue"]
    assert findings_passed["other_field"] == "value"

    # Verify confidence_score is passed separately
    assert call_kwargs["confidence_score"] == 0.85


@pytest.mark.asyncio
@patch("app.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
async def test_process_agent_result_confidence_score_passed_to_save(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score is correctly passed to save_agent_finding."""
    findings = {
        "primary_tech": "React",
        "confidence_score": 0.92,
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

    # Verify save_agent_finding was called with correct parameters
    assert mock_save.called
    call_kwargs = mock_save.call_args.kwargs

    # Verify confidence_score is in kwargs
    assert "confidence_score" in call_kwargs
    assert call_kwargs["confidence_score"] == 0.92

    # Verify other required parameters are present
    assert "analysis_id" in call_kwargs or call_kwargs.get("analysis_id") is not None
    assert call_kwargs.get("agent_type") == agent_type
    assert "findings" in call_kwargs
    assert "processing_time_ms" in call_kwargs
