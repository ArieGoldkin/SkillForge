"""Unit tests for artifact repository."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.repositories.artifact_repository import ArtifactRepository


@pytest.fixture
def mock_session():
    """Mock database session.

    Note: session.add() is synchronous, not async, so it's a MagicMock.
    session.execute(), commit(), and refresh() are async, so they're AsyncMock.
    """
    session = AsyncMock()
    # session.add() is synchronous, not async
    session.add = MagicMock(return_value=None)
    session.execute = AsyncMock()
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)
    return session


@pytest.fixture
def repository(mock_session):
    """Create repository instance."""
    return ArtifactRepository(session=mock_session)


@pytest.mark.asyncio
async def test_create_artifact(repository, mock_session):
    """Test artifact creation."""
    artifact_id = uuid.uuid4()
    analysis_id = uuid.uuid4()
    artifact_data = {
        "id": artifact_id,
        "analysis_id": analysis_id,
        "markdown_content": "# Test\n\nContent.",
        "version": 1,
        "artifact_metadata": {"topics": ["test"]},
        "download_count": 0,
    }

    # Mock Artifact model
    with patch("app.db.repositories.artifact_repository.Artifact") as mock_artifact_class:
        mock_artifact = MagicMock()
        mock_artifact.id = artifact_id
        mock_artifact.analysis_id = analysis_id
        mock_artifact_class.return_value = mock_artifact

        result = await repository.create_artifact(artifact_data)

        assert result == mock_artifact
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_artifact_by_id(repository, mock_session):
    """Test getting artifact by ID."""
    artifact_id = uuid.uuid4()
    mock_artifact = MagicMock()
    mock_artifact.id = artifact_id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_session.execute.return_value = mock_result

    result = await repository.get_artifact_by_id(artifact_id)

    assert result == mock_artifact
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_artifact_by_id_not_found(repository, mock_session):
    """Test getting non-existent artifact."""
    artifact_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_artifact_by_id(artifact_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_artifact_with_analysis(repository, mock_session):
    """Test getting artifact with analysis in single query."""
    artifact_id = uuid.uuid4()
    analysis_id = uuid.uuid4()

    mock_artifact = MagicMock()
    mock_artifact.id = artifact_id
    mock_analysis = MagicMock()
    mock_analysis.id = analysis_id

    mock_result = MagicMock()
    mock_result.one_or_none.return_value = (mock_artifact, mock_analysis)
    mock_session.execute.return_value = mock_result

    result = await repository.get_artifact_with_analysis(artifact_id)

    assert result == (mock_artifact, mock_analysis)
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_artifact_with_analysis_not_found(repository, mock_session):
    """Test getting artifact with analysis when not found."""
    artifact_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repository.get_artifact_with_analysis(artifact_id)

    assert result is None


@pytest.mark.asyncio
async def test_increment_download_count(repository, mock_session):
    """Test incrementing download count."""
    artifact_id = uuid.uuid4()
    mock_artifact = MagicMock()
    mock_artifact.download_count = 5

    # Mock get_artifact_by_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_artifact
    mock_session.execute.return_value = mock_result

    await repository.increment_download_count(artifact_id)

    assert mock_artifact.download_count == 6
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_increment_download_count_not_found(repository, mock_session):
    """Test incrementing download count when artifact not found."""
    artifact_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    await repository.increment_download_count(artifact_id)

    # Should not commit if artifact not found
    mock_session.commit.assert_not_awaited()
