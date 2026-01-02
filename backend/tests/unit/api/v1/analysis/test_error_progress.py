"""Unit tests for error summary and progress endpoints."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status


@pytest.mark.asyncio
async def test_get_error_summary_success():
    """Test successful error summary aggregation."""
    from app.api.v1.analysis.endpoints import get_error_summary

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo.session = mock_session

    mock_result = MagicMock()
    mock_row_1 = MagicMock()
    mock_row_1.error_code = "EXTRACTION_FAILED"
    mock_row_1.failed_at_stage = "extraction"
    mock_row_1.count = 5

    mock_row_2 = MagicMock()
    mock_row_2.error_code = "WORKFLOW_TIMEOUT"
    mock_row_2.failed_at_stage = "workflow_execution"
    mock_row_2.count = 3

    mock_result.fetchall.return_value = [mock_row_1, mock_row_2]
    mock_session.execute.return_value = mock_result

    response = await get_error_summary(analysis_repo=mock_repo)

    assert "error_summary" in response
    assert len(response["error_summary"]) == 2
    assert response["error_summary"][0]["error_code"] == "EXTRACTION_FAILED"
    assert response["error_summary"][0]["failed_at_stage"] == "extraction"
    assert response["error_summary"][0]["count"] == 5
    assert response["error_summary"][1]["error_code"] == "WORKFLOW_TIMEOUT"
    assert response["error_summary"][1]["failed_at_stage"] == "workflow_execution"
    assert response["error_summary"][1]["count"] == 3

    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_error_summary_empty():
    """Test error summary with no errors."""
    from app.api.v1.analysis.endpoints import get_error_summary

    mock_repo = AsyncMock()
    mock_session = AsyncMock()
    mock_repo.session = mock_session

    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_result

    response = await get_error_summary(analysis_repo=mock_repo)

    assert "error_summary" in response
    assert len(response["error_summary"]) == 0

    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_analysis_progress_success():
    """Test successful progress events retrieval."""
    from app.api.v1.analysis.endpoints import get_analysis_progress

    analysis_id = uuid.uuid4()

    mock_repo = AsyncMock()
    mock_analysis = MagicMock()
    mock_analysis.id = analysis_id
    mock_repo.get_by_id.return_value = mock_analysis

    mock_progress_1 = MagicMock()
    mock_progress_1.stage = "extraction"
    mock_progress_1.status = "complete"
    mock_progress_1.progress_data = {"extracted_chars": 5000}
    mock_progress_1.created_at = datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC)

    mock_progress_2 = MagicMock()
    mock_progress_2.stage = "analyzing"
    mock_progress_2.status = "running"
    mock_progress_2.progress_data = None
    mock_progress_2.created_at = datetime(2026, 1, 2, 10, 5, 0, tzinfo=UTC)

    mock_repo.get_progress_events.return_value = [mock_progress_1, mock_progress_2]

    response = await get_analysis_progress(analysis_id=analysis_id, analysis_repo=mock_repo)

    assert response.analysis_id == str(analysis_id)
    assert len(response.events) == 2
    assert response.events[0].stage == "extraction"
    assert response.events[0].status == "complete"
    assert response.events[0].progress_data == {"extracted_chars": 5000}
    assert response.events[0].timestamp == "2026-01-02T10:00:00+00:00"
    assert response.events[1].stage == "analyzing"
    assert response.events[1].status == "running"
    assert response.events[1].progress_data is None
    assert response.events[1].timestamp == "2026-01-02T10:05:00+00:00"

    mock_repo.get_by_id.assert_called_once_with(analysis_id)
    mock_repo.get_progress_events.assert_called_once_with(analysis_id)


@pytest.mark.asyncio
async def test_get_analysis_progress_not_found():
    """Test progress retrieval when analysis not found."""
    from fastapi import HTTPException

    from app.api.v1.analysis.endpoints import get_analysis_progress

    analysis_id = uuid.uuid4()

    mock_repo = AsyncMock()
    mock_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_analysis_progress(analysis_id=analysis_id, analysis_repo=mock_repo)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert f"Analysis {analysis_id} not found" in str(exc_info.value.detail)

    mock_repo.get_by_id.assert_called_once_with(analysis_id)
    mock_repo.get_progress_events.assert_not_called()


@pytest.mark.asyncio
async def test_get_analysis_progress_empty_events():
    """Test progress retrieval with no events."""
    from app.api.v1.analysis.endpoints import get_analysis_progress

    analysis_id = uuid.uuid4()

    mock_repo = AsyncMock()
    mock_analysis = MagicMock()
    mock_analysis.id = analysis_id
    mock_repo.get_by_id.return_value = mock_analysis
    mock_repo.get_progress_events.return_value = []

    response = await get_analysis_progress(analysis_id=analysis_id, analysis_repo=mock_repo)

    assert response.analysis_id == str(analysis_id)
    assert len(response.events) == 0

    mock_repo.get_by_id.assert_called_once_with(analysis_id)
    mock_repo.get_progress_events.assert_called_once_with(analysis_id)
