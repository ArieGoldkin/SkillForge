"""Tests for mark_failed repository method in AnalysisRepository."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.analysis_repository import AnalysisRepository


@pytest.mark.unit
class TestMarkFailed:
    """Test cases for AnalysisRepository.mark_failed()."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create AnalysisRepository instance with mock session."""
        return AnalysisRepository(mock_session)

    @pytest.mark.asyncio
    async def test_mark_failed_success(self, repository, mock_session):
        """Test successful marking of analysis as failed."""
        # Create mock result with rowcount indicating success
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()

        await repository.mark_failed(
            analysis_id=analysis_id,
            error_code="HTTP_404",
            error_message="Page not found",
            failed_at_stage="extraction",
        )

        # Verify execute was called once
        mock_session.execute.assert_called_once()
        # Verify commit was called
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_failed_not_found(self, repository, mock_session):
        """Test mark_failed raises NoResultFound when analysis doesn't exist."""
        # Mock result with rowcount 0 (no rows updated)
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()

        with pytest.raises(NoResultFound) as exc_info:
            await repository.mark_failed(
                analysis_id=analysis_id,
                error_code="HTTP_404",
                error_message="Page not found",
            )

        # Verify error message contains analysis ID
        assert str(analysis_id) in str(exc_info.value)

        # Verify execute was called but commit was not
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_mark_failed_with_all_fields(self, repository, mock_session):
        """Test mark_failed with all optional fields provided."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()

        await repository.mark_failed(
            analysis_id=analysis_id,
            error_code="TIMEOUT",
            error_message="Request timed out after 30s",
            failed_at_stage="extraction",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_failed_default_stage(self, repository, mock_session):
        """Test mark_failed uses default 'extraction' stage when not provided."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()

        # Call without failed_at_stage (should default to "extraction")
        await repository.mark_failed(
            analysis_id=analysis_id,
            error_code="HTTP_404",
            error_message="Not found",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_failed_with_http_5xx_error(self, repository, mock_session):
        """Test mark_failed with HTTP_5XX error code."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()

        await repository.mark_failed(
            analysis_id=analysis_id,
            error_code="HTTP_5XX",
            error_message="HTTP 503 Service Unavailable",
            failed_at_stage="extraction",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_failed_with_error_page_code(self, repository, mock_session):
        """Test mark_failed with ERROR_PAGE error code."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        analysis_id = uuid.uuid4()

        await repository.mark_failed(
            analysis_id=analysis_id,
            error_code="ERROR_PAGE",
            error_message="Detected error page: 404 - Page Not Found",
            failed_at_stage="extraction",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_failed_multiple_analyses(self, repository, mock_session):
        """Test mark_failed can be called multiple times for different analyses."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        analysis_id_1 = uuid.uuid4()
        analysis_id_2 = uuid.uuid4()

        # Mark first analysis as failed
        await repository.mark_failed(
            analysis_id=analysis_id_1,
            error_code="HTTP_404",
            error_message="First error",
        )

        # Mark second analysis as failed
        await repository.mark_failed(
            analysis_id=analysis_id_2,
            error_code="TIMEOUT",
            error_message="Second error",
        )

        # Verify both were executed
        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_mark_failed_database_error_propagates(self, repository, mock_session):
        """Test that database errors propagate correctly."""
        # Mock database error during execute
        mock_session.execute.side_effect = Exception("Database connection lost")

        analysis_id = uuid.uuid4()

        with pytest.raises(Exception, match="Database connection lost"):
            await repository.mark_failed(
                analysis_id=analysis_id,
                error_code="HTTP_404",
                error_message="Test error",
            )

        # Verify commit was not called due to error
        mock_session.commit.assert_not_called()
