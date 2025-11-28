"""Unit tests for workflow runner background task."""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Set DATABASE_URL before importing to avoid validation errors
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")

from app.api.v1.workflow_runner import run_workflow_task


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.fixture
def test_url():
    """Create a test URL."""
    return "https://example.com/article"


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_success(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test successful workflow execution."""
    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(return_value={})

    # Mock database session and status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow was called
    mock_workflow.ainvoke.assert_called_once()
    call_args = mock_workflow.ainvoke.call_args
    assert call_args[0][0]["url"] == test_url
    assert call_args[0][0]["analysis_id"] == str(mock_analysis_id)

    # Verify status was updated to complete
    assert mock_analysis.status == "complete"
    mock_db_session.commit.assert_called_once()

    # Verify events were emitted
    assert mock_emit_event.call_count >= 2  # At least running and complete


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_workflow_error(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution with workflow error."""
    # Mock workflow to raise an error
    mock_workflow.ainvoke = AsyncMock(side_effect=RuntimeError("Workflow failed"))

    # Mock database session for error status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify status was updated to failed
    assert mock_analysis.status == "failed"
    mock_db_session.commit.assert_called_once()

    # Verify error event was emitted
    error_calls = [call for call in mock_emit_event.call_args_list if call[0][0] == "error"]
    assert len(error_calls) == 1


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_status_update_fails(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution when status update fails."""
    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(return_value={})

    # Mock database session to fail on status update
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        # Should not raise - status update failure is logged but doesn't fail workflow
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify error was logged but workflow continued
    error_logs = [
        call
        for call in mock_logger.error.call_args_list
        if "workflow_task_status_update_failed" in str(call)
    ]
    assert len(error_logs) == 1


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_generatorexit(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution with GeneratorExit."""
    # Mock workflow to raise GeneratorExit
    mock_workflow.ainvoke = AsyncMock(side_effect=GeneratorExit())

    # Mock database session for error status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify status was updated to failed
    assert mock_analysis.status == "failed"

    # Verify error event was emitted
    error_calls = [call for call in mock_emit_event.call_args_list if call[0][0] == "error"]
    assert len(error_calls) == 1


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_analysis_not_found(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution when analysis record not found for status update."""
    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(return_value={})

    # Mock database session to return None (analysis not found)
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        # Should not raise - missing analysis is handled gracefully
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify commit was not called (no analysis to update)
    mock_db_session.commit.assert_not_called()
