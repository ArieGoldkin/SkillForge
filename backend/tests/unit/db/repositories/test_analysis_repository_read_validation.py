"""Unit tests for read validation in AnalysisRepository."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.analysis import Analysis
from app.db.repositories.analysis_repository import AnalysisRepository


@pytest.fixture
def mock_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def repository(mock_session):
    """Create repository instance."""
    return AnalysisRepository(session=mock_session)


@pytest.fixture
def mock_analysis():
    """Create mock analysis with valid data."""
    analysis = MagicMock(spec=Analysis)
    analysis.id = uuid.uuid4()
    analysis.status = "complete"
    analysis.raw_content = "Test content"
    analysis.content_embedding = [0.1] * 1536
    analysis.extraction_metadata = {"title": "Test Article"}
    return analysis


# ============================================================================
# get_by_id Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_by_id_with_validation(repository, mock_session, mock_analysis):
    """Test validation enabled by default."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(mock_analysis.id, validate=True)

    assert result == mock_analysis
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id_without_validation(repository, mock_session, mock_analysis):
    """Test validation can be disabled."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(mock_analysis.id, validate=False)

    assert result == mock_analysis
    # Should not call _validate_analysis_data when validate=False


@pytest.mark.asyncio
async def test_get_by_id_valid_data(repository, mock_session, mock_analysis):
    """Test valid data passes validation."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(mock_analysis.id, validate=True)

    assert result == mock_analysis
    # No warnings should be logged for valid data


@pytest.mark.asyncio
async def test_get_by_id_invalid_data_logs_warning(repository, mock_session):
    """Test invalid data logs warning."""
    invalid_analysis = MagicMock(spec=Analysis)
    invalid_analysis.id = uuid.uuid4()
    invalid_analysis.status = "complete"
    invalid_analysis.raw_content = None  # Missing content
    invalid_analysis.content_embedding = None
    invalid_analysis.extraction_metadata = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = invalid_analysis
    mock_session.execute.return_value = mock_result

    with patch("app.db.repositories.analysis_repository.logger") as mock_logger:
        result = await repository.get_by_id(invalid_analysis.id, validate=True)

        assert result == invalid_analysis
        # Should log warning
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "read_validation_warning" in str(call_args)


@pytest.mark.asyncio
async def test_get_by_id_returns_data_even_if_invalid(repository, mock_session):
    """Test data returned even if invalid."""
    invalid_analysis = MagicMock(spec=Analysis)
    invalid_analysis.id = uuid.uuid4()
    invalid_analysis.status = "complete"
    invalid_analysis.raw_content = None  # Invalid

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = invalid_analysis
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(invalid_analysis.id, validate=True)

    # Should still return data (graceful degradation)
    assert result == invalid_analysis


@pytest.mark.asyncio
async def test_get_by_id_missing_analysis(repository, mock_session):
    """Test missing analysis returns None."""
    analysis_id = uuid.uuid4()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_by_id(analysis_id, validate=True)

    assert result is None


@pytest.mark.asyncio
async def test_get_by_id_validation_errors_format(repository, mock_session):
    """Test validation errors formatted."""
    invalid_analysis = MagicMock(spec=Analysis)
    invalid_analysis.id = uuid.uuid4()
    invalid_analysis.status = "complete"
    invalid_analysis.raw_content = None
    invalid_analysis.content_embedding = [0.1] * 100  # Wrong dimensions

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = invalid_analysis
    mock_session.execute.return_value = mock_result

    errors = repository._validate_analysis_data(invalid_analysis)

    assert len(errors) > 0
    assert all(isinstance(error, str) for error in errors)


@pytest.mark.asyncio
async def test_get_by_id_warning_logging(repository, mock_session):
    """Test warnings properly logged."""
    invalid_analysis = MagicMock(spec=Analysis)
    invalid_analysis.id = uuid.uuid4()
    invalid_analysis.status = "complete"
    invalid_analysis.raw_content = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = invalid_analysis
    mock_session.execute.return_value = mock_result

    with patch("app.db.repositories.analysis_repository.logger") as mock_logger:
        await repository.get_by_id(invalid_analysis.id, validate=True)

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert "analysis_id" in call_kwargs
        assert "errors" in call_kwargs
        assert "status" in call_kwargs


# ============================================================================
# _validate_analysis_data Tests
# ============================================================================


def test_validate_analysis_data_complete_valid(repository, mock_analysis):
    """Test complete valid data passes."""
    errors = repository._validate_analysis_data(mock_analysis)
    assert errors == []


def test_validate_analysis_data_complete_missing_content(repository):
    """Test missing content detected."""
    analysis = MagicMock(spec=Analysis)
    analysis.status = "complete"
    analysis.raw_content = None
    analysis.content_embedding = [0.1] * 1536
    analysis.extraction_metadata = {"title": "Test"}

    errors = repository._validate_analysis_data(analysis)
    assert "raw_content" in str(errors[0]).lower()


def test_validate_analysis_data_complete_missing_embedding(repository):
    """Test missing embedding detected."""
    analysis = MagicMock(spec=Analysis)
    analysis.status = "complete"
    analysis.raw_content = "Test content"
    analysis.content_embedding = None
    analysis.extraction_metadata = {"title": "Test"}

    errors = repository._validate_analysis_data(analysis)
    assert "embedding" in str(errors[0]).lower()


def test_validate_analysis_data_complete_missing_metadata(repository):
    """Test missing metadata detected."""
    analysis = MagicMock(spec=Analysis)
    analysis.status = "complete"
    analysis.raw_content = "Test content"
    analysis.content_embedding = [0.1] * 1536
    analysis.extraction_metadata = None

    errors = repository._validate_analysis_data(analysis)
    assert "metadata" in str(errors[0]).lower()


def test_validate_analysis_data_complete_wrong_embedding_dims(repository):
    """Test wrong embedding dimensions detected."""
    analysis = MagicMock(spec=Analysis)
    analysis.status = "complete"
    analysis.raw_content = "Test content"
    analysis.content_embedding = [0.1] * 768  # Wrong: 768 instead of 1536
    analysis.extraction_metadata = {"title": "Test"}

    errors = repository._validate_analysis_data(analysis)
    assert "1536" in str(errors[0]) or "dims" in str(errors[0]).lower()


def test_validate_analysis_data_failed_status(repository):
    """Test failed status allows missing fields."""
    analysis = MagicMock(spec=Analysis)
    analysis.status = "failed"
    analysis.raw_content = None
    analysis.content_embedding = None
    analysis.extraction_metadata = None

    errors = repository._validate_analysis_data(analysis)
    # Failed status doesn't require content fields
    assert errors == []


def test_validate_analysis_data_error_messages(repository):
    """Test error messages are clear."""
    analysis = MagicMock(spec=Analysis)
    analysis.status = "complete"
    analysis.raw_content = None
    analysis.content_embedding = [0.1] * 100
    analysis.extraction_metadata = None

    errors = repository._validate_analysis_data(analysis)
    assert len(errors) >= 2
    # Error messages should be descriptive
    assert all(len(error) > 10 for error in errors)
