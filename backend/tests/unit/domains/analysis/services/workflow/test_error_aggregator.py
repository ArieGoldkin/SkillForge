"""Unit tests for workflow error aggregator (Issue #627, #628)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.analysis.services.workflow.error_aggregator import (
    MIN_EXPECTED_FINDINGS,
    TIER1_FAILURE_THRESHOLD,
    WorkflowErrorAggregator,
)


@pytest.fixture
def aggregator():
    """Create error aggregator instance."""
    return WorkflowErrorAggregator()


@pytest.fixture
def analysis_id():
    """Generate test analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_check_workflow_already_failed(aggregator, analysis_id):
    """Test detection of workflow already marked as failed.

    Issue #627 & #628: Should emit SSE and record to DB.
    """
    workflow_result = {
        "workflow_status": "failed",
        "final_error": "Synthesis stage timed out",
        "failed_at_stage": "synthesis",
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            assert result is True  # Critical failure detected
            mock_record.assert_called_once()
            assert mock_record.call_args[1]["error_code"] == "WORKFLOW_FAILED"
            mock_emit.assert_called_once()
            assert mock_emit.call_args[1]["error_code"] == "WORKFLOW_FAILED"


@pytest.mark.asyncio
async def test_check_workflow_aborted(aggregator, analysis_id):
    """Test detection of aborted workflow.

    Issue #627 & #628: Should emit SSE and record to DB.
    """
    workflow_result = {
        "should_abort": True,
        "abort_reason": "Extraction failed: 404 Not Found",
        "extraction_status": "failed",
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            assert result is True  # Critical failure detected
            mock_record.assert_called_once()
            assert mock_record.call_args[1]["error_code"] == "WORKFLOW_ABORTED"
            mock_emit.assert_called_once()


@pytest.mark.asyncio
async def test_check_tier1_critical_failure(aggregator, analysis_id):
    """Test detection of Tier 1 agent critical failure (>= 50% failed).

    Issue #627 & #628: Should emit SSE and record to DB when majority of
    foundational agents fail. Note: This check only applies to non-completed
    workflows (workflow_status != "completed").
    """
    workflow_result = {
        "workflow_status": "running",  # Not completed - allows tier1 check
        "dispatched_agents": ["key_insights", "pros_cons", "audience_fit", "actionable"],
        "agent_findings": [
            {"agent_type": "key_insights", "findings": ["Finding 1"]},
            # pros_cons, audience_fit, actionable all failed - no findings
        ],
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            # 3 out of 4 Tier 1 agents failed = 75% > 50% threshold
            assert result is True
            mock_record.assert_called_once()
            assert mock_record.call_args[1]["error_code"] == "TIER1_CRITICAL_FAILURE"
            mock_emit.assert_called_once()


@pytest.mark.asyncio
async def test_check_tier1_below_threshold(aggregator, analysis_id):
    """Test that Tier 1 failures below threshold don't trigger error.

    If only 1 out of 4 fails (25%), should not trigger critical failure.
    Also tests that completed workflows with low tier1 failure rate still pass.
    """
    workflow_result = {
        "workflow_status": "running",  # Not completed - allows tier1 check
        "dispatched_agents": ["key_insights", "pros_cons", "audience_fit", "actionable"],
        "agent_findings": [
            {"agent_type": "key_insights", "findings": ["Finding 1"]},
            {"agent_type": "pros_cons", "findings": ["Finding 2"]},
            {"agent_type": "audience_fit", "findings": ["Finding 3"]},
            # actionable failed - 1 out of 4 = 25% < 50% threshold
        ],
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            # 1 out of 4 = 25% < 50% threshold, and we have >= MIN_EXPECTED_FINDINGS
            assert result is False  # No critical failure
            mock_record.assert_not_called()
            mock_emit.assert_not_called()


@pytest.mark.asyncio
async def test_check_insufficient_findings(aggregator, analysis_id):
    """Test detection of insufficient findings.

    Issue #627 & #628: Should emit SSE and record to DB when findings
    are below minimum threshold. Note: This check only applies to
    non-completed workflows.
    """
    workflow_result = {
        "workflow_status": "running",  # Not completed - allows findings check
        "agent_findings": [
            {"agent_type": "key_insights", "findings": ["Finding 1"]},
            # Only 1 finding, below MIN_EXPECTED_FINDINGS (2)
        ],
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            assert result is True  # Critical failure detected
            mock_record.assert_called_once()
            assert mock_record.call_args[1]["error_code"] == "INSUFFICIENT_FINDINGS"
            mock_emit.assert_called_once()


@pytest.mark.asyncio
async def test_check_quality_gate_failed(aggregator, analysis_id):
    """Test detection of quality gate failure.

    Issue #627 & #628: Should emit SSE and record to DB when quality
    gate fails.
    """
    workflow_result = {
        "workflow_status": "completed",
        "agent_findings": [
            {"agent_type": "key_insights", "findings": ["Finding 1"]},
            {"agent_type": "pros_cons", "findings": ["Finding 2"]},
        ],
        "quality_gate_error": "LLM evaluation returned empty response",
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            assert result is True  # Critical failure detected
            mock_record.assert_called_once()
            assert mock_record.call_args[1]["error_code"] == "QUALITY_GATE_FAILED"
            mock_emit.assert_called_once()


@pytest.mark.asyncio
async def test_check_successful_workflow(aggregator, analysis_id):
    """Test that successful workflows don't trigger errors.

    Issue #627 & #628: Should not emit SSE or record to DB when
    workflow completes successfully.
    """
    workflow_result = {
        "workflow_status": "completed",
        "agent_findings": [
            {"agent_type": "key_insights", "findings": ["Finding 1"]},
            {"agent_type": "pros_cons", "findings": ["Finding 2"]},
            {"agent_type": "audience_fit", "findings": ["Finding 3"]},
        ],
        "aggregated_insights": {"summary": "Great article"},
        "quality_gate_passed": True,
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            assert result is False  # No critical failure
            mock_record.assert_not_called()
            mock_emit.assert_not_called()


@pytest.mark.asyncio
async def test_db_recording_failure_doesnt_block_sse(aggregator, analysis_id):
    """Test that DB recording failure doesn't prevent SSE emission.

    Issue #627 & #628: Graceful degradation - if DB fails, SSE should
    still be emitted.
    """
    workflow_result = {
        "workflow_status": "failed",
        "final_error": "Test error",
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
        side_effect=Exception("DB connection failed"),
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            assert result is True  # Critical failure still detected
            mock_record.assert_called_once()  # Attempted
            mock_emit.assert_called_once()  # SSE still emitted


@pytest.mark.asyncio
async def test_sse_failure_doesnt_break_flow(aggregator, analysis_id):
    """Test that SSE emission failure doesn't raise exception.

    Issue #627 & #628: Graceful degradation - if SSE fails, function
    should still return success.
    """
    workflow_result = {
        "workflow_status": "failed",
        "final_error": "Test error",
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
            side_effect=Exception("SSE channel closed"),
        ):
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            assert result is True  # Critical failure still detected
            mock_record.assert_called_once()  # DB recording succeeded


def test_threshold_constants():
    """Test that threshold constants have expected values."""
    assert TIER1_FAILURE_THRESHOLD == 0.5  # 50%
    assert MIN_EXPECTED_FINDINGS == 2


@pytest.mark.asyncio
async def test_empty_dispatched_agents_skips_tier1_check(aggregator, analysis_id):
    """Test that missing dispatched_agents doesn't cause Tier 1 check error."""
    workflow_result = {
        "workflow_status": "completed",
        "agent_findings": [
            {"agent_type": "key_insights", "findings": ["Finding 1"]},
            {"agent_type": "pros_cons", "findings": ["Finding 2"]},
        ],
        # No dispatched_agents field
    }

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.error_recorder.record",
        new_callable=AsyncMock,
    ) as mock_record:
        with patch(
            "app.shared.services.messaging.sse_helpers.emit_error_event",
            new_callable=AsyncMock,
        ) as mock_emit:
            result = await aggregator.check_and_record_errors(analysis_id, workflow_result)

            # Should pass without error (can't determine failure rate)
            assert result is False
            mock_record.assert_not_called()
            mock_emit.assert_not_called()
