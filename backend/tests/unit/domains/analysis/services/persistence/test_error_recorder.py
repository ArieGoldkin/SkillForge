"""Unit tests for ErrorRecorder."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.services.persistence.error_recorder import ErrorRecorder


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_error_recorder_record_success(mock_analysis_id):
    """Test successful error recording."""
    # Mock analysis record
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.error_code = None
    mock_analysis.error_message = None
    mock_analysis.failed_at_stage = None
    mock_analysis.updated_at = datetime.now(UTC)

    # Mock database session
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        recorder = ErrorRecorder()
        await recorder.record(
            analysis_id=mock_analysis_id,
            error_code="AGGREGATION_FAILED",
            error_message="Test error message",
            stage="aggregate_findings",
        )

    # Verify error fields were set
    assert mock_analysis.error_code == "AGGREGATION_FAILED"
    assert mock_analysis.error_message == "Test error message"
    assert mock_analysis.failed_at_stage == "aggregate_findings"
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_error_recorder_record_analysis_not_found(mock_analysis_id):
    """Test error recording when analysis record is not found."""
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Analysis not found
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        recorder = ErrorRecorder()
        # Should not raise - missing analysis is handled gracefully
        await recorder.record(
            analysis_id=mock_analysis_id,
            error_code="AGGREGATION_FAILED",
            error_message="Test error message",
            stage="aggregate_findings",
        )

    # Verify commit was not called (no analysis to update)
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_error_recorder_record_truncates_long_message(mock_analysis_id):
    """Test error recording truncates messages longer than 2000 chars."""
    # Create a very long error message
    long_message = "x" * 3000

    # Mock analysis record
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.error_code = None
    mock_analysis.error_message = None
    mock_analysis.failed_at_stage = None
    mock_analysis.updated_at = datetime.now(UTC)

    # Mock database session
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        recorder = ErrorRecorder()
        await recorder.record(
            analysis_id=mock_analysis_id,
            error_code="AGGREGATION_FAILED",
            error_message=long_message,
            stage="aggregate_findings",
        )

    # Verify message was truncated to 2000 chars
    assert len(mock_analysis.error_message) == 2000
    assert mock_analysis.error_message == "x" * 2000
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_error_recorder_record_database_error_graceful(mock_analysis_id):
    """Test error recording handles database errors gracefully (doesn't raise)."""
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.error_recorder.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        recorder = ErrorRecorder()
        # Should NOT raise - error recording must never break the workflow
        await recorder.record(
            analysis_id=mock_analysis_id,
            error_code="AGGREGATION_FAILED",
            error_message="Test error message",
            stage="aggregate_findings",
        )

    # Verify commit was not called (error occurred)
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_error_recorder_record_warning(mock_analysis_id):
    """Test warning recording (currently only logs)."""
    recorder = ErrorRecorder()

    # Should not raise - warnings are logged only
    await recorder.record_warning(
        analysis_id=mock_analysis_id,
        warning_code="ARTIFACT_G_EVAL_SCORING_FAILED",
        warning_message="G-Eval scoring failed",
        stage="artifact_generation",
    )

    # No database operations expected - warnings are logged only
    # This test just verifies the method executes without errors
