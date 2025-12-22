"""Unit tests for StatusUpdater."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.services.persistence.status_updater import StatusUpdater


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_status_updater_update_success(mock_analysis_id):
    """Test successful status update."""
    # Mock analysis record
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.status = "pending"

    # Mock database session
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal", return_value=mock_db_session):
        updater = StatusUpdater()
        await updater.update(mock_analysis_id, "extracting")

    # Verify status was updated
    assert mock_analysis.status == "complete"
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_status_updater_update_analysis_not_found(mock_analysis_id):
    """Test status update when analysis record is not found."""
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Analysis not found
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal", return_value=mock_db_session):
        updater = StatusUpdater()
        # Should not raise - missing analysis is handled gracefully
        await updater.update(mock_analysis_id, "extracting")

    # Verify commit was not called (no analysis to update)
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_status_updater_update_database_error(mock_analysis_id):
    """Test status update handles database errors gracefully."""
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal", return_value=mock_db_session):
        updater = StatusUpdater()
        # Should not raise - errors are logged but don't propagate
        await updater.update(mock_analysis_id, "extracting")

    # Verify commit was not called (error occurred)
    mock_db_session.commit.assert_not_called()

