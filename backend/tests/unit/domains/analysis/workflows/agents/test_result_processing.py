"""Unit tests for agent result processing with confidence score extraction."""

import time
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.result_processing import process_agent_result


@pytest.fixture
def mock_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_analysis_id():
    """Sample analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
    # Verify confidence_score is at top level for template/validation access
    assert result["confidence_score"] == 0.85


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
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


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
async def test_process_agent_result_confidence_score_at_top_level_for_template(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that confidence_score is returned at top level for template/validation access.

    This test verifies the fix for issue #160 where confidence scores showed as 0.00
    in artifacts because the template expects finding.confidence_score at top level,
    but it was only nested inside findings dict.

    The result dict must have:
    - agent_type: str
    - findings: dict (with original content including confidence_score)
    - confidence_score: float | None (AT TOP LEVEL for template access)
    - processing_time_ms: int
    """
    findings = {
        "primary_tech": "LangGraph",
        "version": "0.6.7",
        "confidence_score": 0.92,
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

    # KEY ASSERTION: confidence_score must be at top level of result dict
    # This is what the template expects: finding.confidence_score
    assert "confidence_score" in result, "confidence_score must be at top level"
    assert result["confidence_score"] == 0.92

    # Verify the structure matches what template/validation expects
    # Template: {{ "%.2f" | format(finding.confidence_score | default(0.0)) }}
    # Validation: finding.get("confidence_score", 0.0)
    assert isinstance(result["confidence_score"], float)


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
async def test_process_agent_result_confidence_score_none_at_top_level(
    mock_emit, mock_save, mock_session, sample_analysis_id
):
    """Test that None confidence_score is returned at top level when not present."""
    findings = {
        "primary_tech": "React",
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

    # confidence_score should be at top level even when None
    assert "confidence_score" in result
    assert result["confidence_score"] is None


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.result_processing.score_agent_output")
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
async def test_process_agent_result_specificity_scoring(
    mock_emit, mock_save, mock_score_output, mock_session, sample_analysis_id
):
    """Test that specificity scoring is performed on agent results."""
    findings = {
        "performance_metrics": [
            {
                "metric_name": "latency",
                "current_value": "450ms",
                "target_value": "<200ms",
                "notes": "Reduce database query time.",
            }
        ],
        "confidence_score": 0.85,
    }
    agent_type = "performance_analyst"
    start_time = time.time()

    # Mock specificity score result
    from app.domains.analysis.workflows.agents.validation import SpecificityScore

    mock_specificity_score = SpecificityScore(
        overall_score=0.82,
        numeric_field_compliance=0.90,
        numeric_density=0.75,
        vague_penalty=0.80,
        vague_phrase_count=2,
        numeric_value_count=8,
        expected_numeric_count=10,
    )
    mock_score_output.return_value = mock_specificity_score

    result = await process_agent_result(
        findings=findings,
        analysis_id=sample_analysis_id,
        agent_type=agent_type,
        session=mock_session,
        start_time=start_time,
    )

    # Verify specificity scoring was called
    mock_score_output.assert_called_once_with(findings, agent_type=agent_type)

    # Verify specificity score is included in result
    assert "specificity_score" in result
    assert result["specificity_score"] == 0.82


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.result_processing.score_agent_output")
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
@patch("app.domains.analysis.workflows.agents.result_processing.logger")
async def test_process_agent_result_logs_specificity_score(
    mock_logger, mock_emit, mock_save, mock_score_output, mock_session, sample_analysis_id
):
    """Test that specificity score metrics are logged."""
    findings = {
        "primary_tech": "React",
        "confidence_score": 0.85,
    }
    agent_type = "tech_comparator"
    start_time = time.time()

    # Mock specificity score result
    from app.domains.analysis.workflows.agents.validation import SpecificityScore

    mock_specificity_score = SpecificityScore(
        overall_score=0.75,
        numeric_field_compliance=0.80,
        numeric_density=0.70,
        vague_penalty=0.75,
        vague_phrase_count=3,
        numeric_value_count=7,
        expected_numeric_count=10,
    )
    mock_score_output.return_value = mock_specificity_score

    await process_agent_result(
        findings=findings,
        analysis_id=sample_analysis_id,
        agent_type=agent_type,
        session=mock_session,
        start_time=start_time,
    )

    # Verify logging was called with specificity metrics
    # Find the info call with agent_specificity_score
    info_calls = [
        call for call in mock_logger.info.call_args_list if call[0][0] == "agent_specificity_score"
    ]
    assert len(info_calls) > 0, "Expected agent_specificity_score to be logged"

    # Check that specificity metrics are in the log call
    log_call = info_calls[0]
    assert log_call.kwargs["specificity_score"] == 0.75
    assert log_call.kwargs["quality_level"] == "good"
    assert log_call.kwargs["numeric_count"] == 7
    assert log_call.kwargs["vague_count"] == 3


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.result_processing.score_agent_output")
@patch(
    "app.domains.analysis.workflows.agents.result_processing.save_agent_finding",
    new_callable=AsyncMock,
)
@patch(
    "app.domains.analysis.workflows.agents.result_processing.emit_agent_progress",
    new_callable=AsyncMock,
)
@patch("app.domains.analysis.workflows.agents.result_processing.logger")
async def test_process_agent_result_warns_on_low_specificity(
    mock_logger, mock_emit, mock_save, mock_score_output, mock_session, sample_analysis_id
):
    """Test that low specificity outputs trigger warning logs."""
    findings = {
        "description": "Use appropriate caching for better performance.",
        "confidence_score": 0.70,
    }
    agent_type = "performance_analyst"
    start_time = time.time()

    # Mock low specificity score
    from app.domains.analysis.workflows.agents.validation import SpecificityScore, VaguePhrase

    mock_specificity_score = SpecificityScore(
        overall_score=0.45,  # Below 0.60 threshold
        numeric_field_compliance=0.30,
        numeric_density=0.40,
        vague_penalty=0.50,
        vague_phrase_count=8,
        numeric_value_count=2,
        expected_numeric_count=10,
        vague_phrases=[
            VaguePhrase("appropriate", "qualitative_adjectives", "use appropriate caching"),
            VaguePhrase("better", "improvement_verbs", "for better performance"),
            VaguePhrase("suitable", "qualitative_adjectives", "suitable approach"),
        ],
    )
    mock_score_output.return_value = mock_specificity_score

    await process_agent_result(
        findings=findings,
        analysis_id=sample_analysis_id,
        agent_type=agent_type,
        session=mock_session,
        start_time=start_time,
    )

    # Verify warning was logged for low specificity
    warning_calls = [
        call
        for call in mock_logger.warning.call_args_list
        if call[0][0] == "low_specificity_output"
    ]
    assert len(warning_calls) > 0, "Expected low_specificity_output warning to be logged"

    # Check warning details
    warning_call = warning_calls[0]
    assert warning_call.kwargs["specificity_score"] == 0.45
    assert warning_call.kwargs["quality_level"] == "poor"
    assert warning_call.kwargs["vague_phrases"] == 8
    assert "sample_vague_phrases" in warning_call.kwargs
    assert len(warning_call.kwargs["sample_vague_phrases"]) <= 3  # Max 3 samples


# Tests for _count_insights function
from app.domains.analysis.workflows.agents.result_processing import _count_insights


def test_count_insights_trend_validator_counts_all_fields():
    """Test that trend_validator insight counting includes all valuable fields."""
    findings = {
        "trend_assessments": [],
        "future_outlook": "Meta-content has no technologies",
        "recommendation": "Use key_insights agent instead",
        "modern_alternatives": [],
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 2  # future_outlook + recommendation


def test_count_insights_trend_validator_counts_trend_assessments():
    """Test that trend_validator counts trend_assessments correctly."""
    findings = {
        "trend_assessments": [
            {"technology": "React", "status": "current"},
            {"technology": "Vue", "status": "current"},
        ],
        "future_outlook": "",
        "recommendation": "",
        "modern_alternatives": [],
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 2  # 2 trend assessments


def test_count_insights_trend_validator_counts_modern_alternatives():
    """Test that trend_validator counts modern_alternatives."""
    findings = {
        "trend_assessments": [],
        "modern_alternatives": [
            {"old_tech": "jQuery", "new_tech": "React"},
            {"old_tech": "Backbone", "new_tech": "Vue"},
        ],
        "future_outlook": "",
        "recommendation": "",
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 2  # 2 modern alternatives


def test_count_insights_trend_validator_counts_all_fields_combined():
    """Test that trend_validator counts all fields correctly when all have content."""
    findings = {
        "trend_assessments": [{"technology": "React", "status": "current"}],
        "modern_alternatives": [{"old_tech": "jQuery", "new_tech": "React"}],
        "future_outlook": "React will remain stable until 2028+",
        "recommendation": "Adopt React for new projects",
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 4  # 1 trend + 1 alternative + 1 outlook + 1 recommendation


def test_count_insights_trend_validator_ignores_empty_strings():
    """Test that trend_validator ignores empty strings in future_outlook and recommendation."""
    findings = {
        "trend_assessments": [],
        "modern_alternatives": [],
        "future_outlook": "",  # Empty string
        "recommendation": "   ",  # Whitespace only
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 0  # Empty strings don't count


def test_count_insights_trend_validator_handles_missing_fields():
    """Test that trend_validator handles missing fields gracefully."""
    findings = {
        "trend_assessments": [],
        # Missing modern_alternatives, future_outlook, recommendation
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 0  # All fields empty or missing


def test_count_insights_trend_validator_handles_non_list_trend_assessments():
    """Test that trend_validator handles non-list trend_assessments gracefully."""
    findings = {
        "trend_assessments": "not a list",  # Invalid type
        "future_outlook": "Some outlook",
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 1  # Only future_outlook counts


def test_count_insights_trend_validator_handles_non_list_alternatives():
    """Test that trend_validator handles non-list modern_alternatives gracefully."""
    findings = {
        "trend_assessments": [],
        "modern_alternatives": "not a list",  # Invalid type
        "recommendation": "Some recommendation",
    }
    count = _count_insights(findings, "trend_validator")
    assert count == 1  # Only recommendation counts
