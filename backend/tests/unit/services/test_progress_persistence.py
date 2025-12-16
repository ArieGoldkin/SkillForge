"""Unit tests for progress persistence service."""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.models.progress import AnalysisProgress
from app.services.persistence.progress import persist_progress_event, persist_progress_event_async


@pytest.fixture
def sample_event_data():
    """Sample SSE event data."""
    return {
        "type": "progress",
        "analysis_id": str(uuid.uuid4()),
        "stage": "extraction",
        "status": "running",
        "timestamp": "2024-01-01T00:00:00Z",
        "word_count": 5234,
    }


@pytest.mark.asyncio
@patch("app.services.persistence.progress.AsyncSessionLocal")
async def test_persist_progress_event_success(mock_session_local, sample_event_data):
    """Test successful persistence of progress event to database."""
    # Mock database session
    # Note: session.add() is synchronous, not async, so it's a MagicMock.
    # session.commit() is async, so it's AsyncMock.
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.add = MagicMock(return_value=None)  # add() is synchronous
    mock_session.commit = AsyncMock(return_value=None)  # commit() is async
    mock_session_local.return_value = mock_session

    await persist_progress_event(sample_event_data)

    # Verify session was used
    assert mock_session.add.called
    assert mock_session.commit.called

    # Verify AnalysisProgress was created with correct data
    add_call = mock_session.add.call_args[0][0]
    assert isinstance(add_call, AnalysisProgress)
    assert str(add_call.analysis_id) == sample_event_data["analysis_id"]
    assert add_call.stage == sample_event_data["stage"]
    assert add_call.status == sample_event_data["status"]
    assert add_call.progress_data == sample_event_data


@pytest.mark.asyncio
@patch("app.services.persistence.progress.AsyncSessionLocal")
@patch("app.services.persistence.progress.logger")
async def test_persist_progress_event_handles_errors(
    mock_logger, mock_session_local, sample_event_data
):
    """Test that persistence errors are logged but don't raise exceptions."""
    # Mock database session to raise error
    # Note: session.add() is synchronous, not async, so it's a MagicMock.
    # session.commit() is async, so it's AsyncMock.
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.add = MagicMock(return_value=None)  # add() is synchronous
    mock_session.commit = AsyncMock(return_value=None)  # commit() is async
    mock_session.commit.side_effect = SQLAlchemyError("Database connection failed")
    mock_session_local.return_value = mock_session

    # Should not raise - errors are logged but don't break SSE stream
    await persist_progress_event(sample_event_data)

    # Verify error was logged
    mock_logger.warning.assert_called()
    warning_call = mock_logger.warning.call_args
    assert "progress_persistence_failed" in str(warning_call)


@pytest.mark.asyncio
@patch("app.services.persistence.progress.persist_progress_event")
async def test_persist_progress_event_async_creates_task(mock_persist, sample_event_data):
    """Test that persist_progress_event_async creates background task."""
    # Clear any existing tasks
    from app.services.persistence.progress import _progress_tasks

    _progress_tasks.clear()

    # Call async persistence function
    persist_progress_event_async(sample_event_data)

    # Verify task was created
    assert len(_progress_tasks) == 1

    # Wait for task to complete
    task = next(iter(_progress_tasks))
    await task

    # Verify persist_progress_event was called
    assert mock_persist.called
    assert mock_persist.call_args[0][0] == sample_event_data

    # Verify task was removed from tracking set
    assert len(_progress_tasks) == 0


@pytest.mark.asyncio
@patch("app.services.persistence.progress.persist_progress_event")
@patch("app.services.persistence.progress.logger")
async def test_persist_progress_event_async_handles_task_errors(
    mock_logger, mock_persist, sample_event_data
):
    """Test that task errors are handled by completion callback."""
    # Make persistence function raise error
    mock_persist.side_effect = Exception("Persistence failed")

    # Clear tasks
    from app.services.persistence.progress import _progress_tasks

    _progress_tasks.clear()

    # Call async persistence function
    persist_progress_event_async(sample_event_data)

    # Wait for task to complete (with exception handling)
    task = next(iter(_progress_tasks))
    try:
        await task
    except Exception:
        # Exception is expected - it's handled by the completion callback
        pass

    # Give callback time to execute

    await asyncio.sleep(0.01)

    # Verify error was logged by completion callback
    mock_logger.warning.assert_called()
    warning_call = mock_logger.warning.call_args
    assert "progress_persistence_task_failed" in str(warning_call)

    # Verify task was removed from tracking set
    assert len(_progress_tasks) == 0


@pytest.mark.asyncio
@patch("app.services.persistence.progress.persist_progress_event")
@patch("app.services.persistence.progress.logger")
async def test_persist_progress_event_async_skips_in_benchmark_mode(
    mock_logger, mock_persist, sample_event_data
):
    """Test that persistence is skipped when in benchmark mode."""
    from app.evaluation.llm_benchmark import benchmark_model_context
    from app.services.persistence.progress import _progress_tasks

    _progress_tasks.clear()

    # Call persist within benchmark context - should be skipped
    with benchmark_model_context("gpt-4o-mini"):
        persist_progress_event_async(sample_event_data)

    # Verify no task was created (persistence was skipped)
    assert len(_progress_tasks) == 0

    # Verify persist_progress_event was NOT called
    assert not mock_persist.called

    # Verify skip was logged at debug level
    mock_logger.debug.assert_called()
    debug_call = mock_logger.debug.call_args
    assert "progress_persistence_skipped_benchmark_mode" in str(debug_call)


@pytest.mark.asyncio
@patch("app.services.persistence.progress.persist_progress_event")
async def test_persist_progress_event_async_works_outside_benchmark_mode(
    mock_persist, sample_event_data
):
    """Test that persistence works normally outside benchmark mode."""
    from app.services.persistence.progress import _progress_tasks

    _progress_tasks.clear()

    # Call persist outside benchmark context - should work normally
    persist_progress_event_async(sample_event_data)

    # Verify task was created
    assert len(_progress_tasks) == 1

    # Wait for task to complete
    task = next(iter(_progress_tasks))
    await task

    # Verify persist_progress_event WAS called
    assert mock_persist.called
    assert mock_persist.call_args[0][0] == sample_event_data


def test_benchmark_mode_context_variable_isolation():
    """Test that benchmark_mode context variable is properly isolated."""
    from app.evaluation.llm_benchmark import benchmark_model_context, is_benchmark_mode

    # Outside context - should be False
    assert is_benchmark_mode() is False

    # Inside context - should be True
    with benchmark_model_context("test-model"):
        assert is_benchmark_mode() is True

        # Nested context maintains True
        with benchmark_model_context("another-model"):
            assert is_benchmark_mode() is True

        # Still True after nested context exits
        assert is_benchmark_mode() is True

    # After context exits - should be False again
    assert is_benchmark_mode() is False


def test_benchmark_model_id_context_variable():
    """Test that benchmark model_id context variable works correctly."""
    from app.evaluation.llm_benchmark import (
        benchmark_model_context,
        get_benchmark_model_id,
    )

    # Outside context - should be None
    assert get_benchmark_model_id() is None

    # Inside context - should have model_id
    with benchmark_model_context("gpt-4o-mini"):
        assert get_benchmark_model_id() == "gpt-4o-mini"

        # Nested context updates model_id
        with benchmark_model_context("claude-sonnet-4"):
            assert get_benchmark_model_id() == "claude-sonnet-4"

        # After nested exits, returns to outer model_id
        assert get_benchmark_model_id() == "gpt-4o-mini"

    # After context exits - should be None again
    assert get_benchmark_model_id() is None
