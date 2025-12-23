"""Unit tests for abort signal helpers."""

from typing import TYPE_CHECKING

import pytest

from app.domains.analysis.workflows.utils.abort_helpers import check_should_abort

if TYPE_CHECKING:
    from app.domains.analysis.workflows.state import AnalysisState


@pytest.mark.unit
def test_check_should_abort_returns_none_when_abort_set():
    """Test that check_should_abort returns None when should_abort is True."""
    state: AnalysisState = {
        "analysis_id": "test-123",
        "should_abort": True,
        "abort_reason": "Extraction failed",
    }

    result = check_should_abort(state)

    assert result is None


@pytest.mark.unit
def test_check_should_abort_returns_empty_dict_when_no_abort():
    """Test that check_should_abort returns {} when should_abort is False or missing."""
    state: AnalysisState = {
        "analysis_id": "test-123",
        "should_abort": False,
    }

    result = check_should_abort(state)

    assert result == {}


@pytest.mark.unit
def test_check_should_abort_returns_empty_dict_when_abort_missing():
    """Test that check_should_abort returns {} when should_abort key is missing."""
    state: AnalysisState = {
        "analysis_id": "test-123",
    }

    result = check_should_abort(state)

    assert result == {}


@pytest.mark.unit
def test_check_should_abort_logs_when_aborting():
    """Test that check_should_abort logs debug message when aborting."""
    from unittest.mock import patch

    state: AnalysisState = {
        "analysis_id": "test-123",
        "should_abort": True,
        "abort_reason": "Test abort reason",
    }

    with patch("app.domains.analysis.workflows.utils.abort_helpers.logger") as mock_logger:
        check_should_abort(state)

        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "workflow_node_skipped_abort"
        assert call_args[1]["analysis_id"] == "test-123"
        assert call_args[1]["abort_reason"] == "Test abort reason"


@pytest.mark.unit
def test_check_should_abort_handles_missing_abort_reason():
    """Test that check_should_abort handles missing abort_reason gracefully."""
    state: AnalysisState = {
        "analysis_id": "test-123",
        "should_abort": True,
    }

    result = check_should_abort(state)

    assert result is None
