"""Unit tests for quality gate fail node.

Tests the new _quality_gate_fail_node that handles permanent quality failures.

Issue #ARTIFACT-QUALITY: Quality gate now fails closed to prevent garbage artifacts.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.workflows.graph_builder import _quality_gate_fail_node
from app.workflows.state import AnalysisState


@pytest.mark.asyncio
async def test_quality_gate_fail_node_sets_failed_status():
    """Test that fail node sets status to 'failed'."""
    state: AnalysisState = {
        "analysis_id": "test-analysis-123",
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
            "app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
        patch("app.workflows.graph_builder.logger") as mock_logger,
    ):
        result = await _quality_gate_fail_node(state)

        # Verify status is set to failed
        assert result["status"] == "failed"
        assert "error" in result
        assert "Quality gate failed" in result["error"]
        assert "avg_score=0.5" in result["error"]
        assert "after 2 retries" in result["error"]


@pytest.mark.asyncio
async def test_quality_gate_fail_node_emits_sse_error():
    """Test that fail node emits SSE error event."""
    state: AnalysisState = {
        "analysis_id": "test-analysis-456",
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
<<<<<<< Updated upstream
        patch("app.services.sse_helpers.emit_streaming_event", new_callable=AsyncMock) as mock_emit,
=======
        patch(
            "app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
>>>>>>> Stashed changes
        patch("app.workflows.graph_builder.logger"),
    ):
        await _quality_gate_fail_node(state)

        # Verify SSE error event was emitted
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args

        # Check event type and fields
        assert call_args[0][0] == "error"
        kwargs = call_args[1]
        assert kwargs["analysis_id"] == "test-analysis-456"
        assert kwargs["stage"] == "quality_gate"
        assert kwargs["status"] == "failed"
        assert "Quality gate failed after 2 retries" in kwargs["error_message"]
        assert "Average score: 0.45" in kwargs["error_message"]
        assert "threshold: 0.7" in kwargs["error_message"]

        # Verify quality scores are included
        assert "quality_scores" in kwargs
        scores = kwargs["quality_scores"]
        assert scores["relevance"] == 0.3
        assert scores["depth"] == 0.5
        assert scores["coherence"] == 0.55


@pytest.mark.asyncio
async def test_quality_gate_fail_node_logs_error():
    """Test that fail node logs error with proper fields."""
    state: AnalysisState = {
        "analysis_id": "test-analysis-789",
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
            "app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock
        ),
        patch("app.workflows.graph_builder.logger") as mock_logger,
    ):
        await _quality_gate_fail_node(state)

        # Verify error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args

        # Check log event name and fields
        assert call_args[0][0] == "quality_gate_failed_permanently"
        kwargs = call_args[1]
        assert kwargs["analysis_id"] == "test-analysis-789"
        assert kwargs["avg_score"] == 0.6
        assert kwargs["retry_count"] == 2
        assert "quality_scores" in kwargs
        assert kwargs["quality_scores"]["relevance"] == 0.45
        assert "Analysis failed due to quality gate" in kwargs["message"]


@pytest.mark.asyncio
async def test_quality_gate_fail_node_handles_none_values():
    """Test that fail node handles None/missing values gracefully."""
    state: AnalysisState = {
        "analysis_id": "test-analysis-000",
        # Missing quality_gate_avg_score, quality_scores, retry_count
    }

    with (
        patch(
            "app.services.messaging.sse_helpers.emit_streaming_event", new_callable=AsyncMock
        ) as mock_emit,
        patch("app.workflows.graph_builder.logger") as mock_logger,
    ):
        # Should not raise exception
        result = await _quality_gate_fail_node(state)

        # Verify defaults are used
        assert result["status"] == "failed"
        assert "error" in result

        # Verify SSE and logging still work with defaults
        mock_emit.assert_called_once()
        mock_logger.error.assert_called_once()

        # Check that 0 defaults are used
        emit_kwargs = mock_emit.call_args[1]
        assert "after 0 retries" in emit_kwargs["error_message"]
        assert "Average score: 0.0" in emit_kwargs["error_message"]
