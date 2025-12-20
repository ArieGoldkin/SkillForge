"""Unit tests for quality gate fail node.

Tests the _quality_gate_fail_node that handles quality failures with fail-open behavior.

Issue #299-304: Quality gate now uses FAIL-OPEN behavior - always generate artifact
even with low quality scores. Users prefer getting something over nothing.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.analysis.workflows.graph_builder import _quality_gate_fail_node
from app.domains.analysis.workflows.state import AnalysisState

# Use valid UUIDs for tests (annotation queue requires UUID format)
TEST_UUID_1 = str(uuid.uuid4())
TEST_UUID_2 = str(uuid.uuid4())
TEST_UUID_3 = str(uuid.uuid4())
TEST_UUID_4 = str(uuid.uuid4())


@pytest.mark.unit
@pytest.mark.asyncio
async def test_quality_gate_fail_node_sets_warning_status():
    """Test that fail node sets quality_gate_warning (fail-open behavior)."""
    state: AnalysisState = {
        "analysis_id": TEST_UUID_1,
        "quality_gate_passed": False,
        "quality_gate_retry_count": 2,
        "quality_gate_avg_score": 0.5,
        "quality_scores": {
            "relevance": {"score": 0.4, "comment": "Low relevance"},
            "depth": {"score": 0.5, "comment": "Shallow"},
            "coherence": {"score": 0.6, "comment": "OK"},
        },
    }

    with (
        patch(
            "app.shared.services.messaging.sse_helpers.emit_streaming_event",
            new_callable=AsyncMock,
        ) as mock_emit,
        patch("app.domains.analysis.workflows.graph_builder.logger") as mock_logger,
    ):
        result = await _quality_gate_fail_node(state)

        # Verify fail-open behavior: quality_gate_passed=False but no status="failed"
        assert result["quality_gate_passed"] is False
        assert "quality_gate_warning" in result
        assert "avg_score=0.5" in result["quality_gate_warning"]
        assert "after 2 retries" in result["quality_gate_warning"]


@pytest.mark.asyncio
async def test_quality_gate_fail_node_emits_progress_event():
    """Test that fail node emits SSE progress event (not error - fail-open)."""
    state: AnalysisState = {
        "analysis_id": TEST_UUID_2,
        "quality_gate_passed": False,
        "quality_gate_retry_count": 2,
        "quality_gate_avg_score": 0.45,
        "quality_scores": {
            "relevance": {"score": 0.3, "comment": "Not relevant"},
            "depth": {"score": 0.5, "comment": "Shallow"},
            "coherence": {"score": 0.55, "comment": "OK"},
        },
    }

    with (
        patch(
            "app.shared.services.messaging.sse_helpers.emit_streaming_event",
            new_callable=AsyncMock,
        ) as mock_emit,
        patch("app.domains.analysis.workflows.graph_builder.logger"),
    ):
        await _quality_gate_fail_node(state)

        # Verify SSE progress event (not error) was emitted - fail-open behavior
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args

        # Check event type is "progress" not "error" (fail-open)
        assert call_args[0][0] == "progress"
        kwargs = call_args[1]
        assert kwargs["analysis_id"] == TEST_UUID_2
        assert kwargs["stage"] == "quality_gate"
        assert kwargs["status"] == "low_quality"  # Not "failed"
        assert "score: 0.45" in kwargs["message"]

        # Verify quality scores are included
        assert "quality_scores" in kwargs
        scores = kwargs["quality_scores"]
        assert scores["relevance"] == 0.3
        assert scores["depth"] == 0.5
        assert scores["coherence"] == 0.55


@pytest.mark.asyncio
async def test_quality_gate_fail_node_logs_warning():
    """Test that fail node logs warning (not error) with proper fields."""
    state: AnalysisState = {
        "analysis_id": TEST_UUID_3,
        "quality_gate_passed": False,
        "quality_gate_retry_count": 2,
        "quality_gate_avg_score": 0.6,
        "quality_scores": {
            "relevance": {"score": 0.45, "comment": "Below minimum"},
            "depth": {"score": 0.7, "comment": "OK"},
            "coherence": {"score": 0.65, "comment": "OK"},
        },
    }

    with (
        patch(
            "app.shared.services.messaging.sse_helpers.emit_streaming_event",
            new_callable=AsyncMock,
        ),
        patch("app.domains.analysis.workflows.graph_builder.logger") as mock_logger,
    ):
        await _quality_gate_fail_node(state)

        # Verify warning was logged (not error - fail-open behavior)
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args

        # Check log event name and fields
        assert call_args[0][0] == "quality_gate_failed_continuing_to_artifact"
        kwargs = call_args[1]
        assert kwargs["analysis_id"] == TEST_UUID_3
        assert kwargs["avg_score"] == 0.6
        assert kwargs["retry_count"] == 2
        assert "quality_scores" in kwargs
        assert kwargs["quality_scores"]["relevance"] == 0.45
        assert "fail-open" in kwargs["message"]


@pytest.mark.asyncio
async def test_quality_gate_fail_node_handles_none_values():
    """Test that fail node handles None/missing values gracefully."""
    state: AnalysisState = {
        "analysis_id": TEST_UUID_4,
        # Missing quality_gate_avg_score, quality_scores, retry_count
    }

    with (
        patch(
            "app.shared.services.messaging.sse_helpers.emit_streaming_event",
            new_callable=AsyncMock,
        ) as mock_emit,
        patch("app.domains.analysis.workflows.graph_builder.logger") as mock_logger,
    ):
        # Should not raise exception
        result = await _quality_gate_fail_node(state)

        # Verify defaults are used (fail-open behavior)
        assert result["quality_gate_passed"] is False
        assert "quality_gate_warning" in result

        # Verify SSE and logging still work with defaults
        mock_emit.assert_called_once()
        mock_logger.warning.assert_called_once()

        # Check that 0 defaults are used
        emit_kwargs = mock_emit.call_args[1]
        assert "0 retries" in emit_kwargs["message"]
        assert "score: 0.00" in emit_kwargs["message"]
