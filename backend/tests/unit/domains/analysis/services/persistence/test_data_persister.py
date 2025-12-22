"""Unit tests for DataPersister."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.services.persistence.data_persister import DataPersister


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_data_persister_persist_success(mock_analysis_id):
    """Test successful persistence of workflow data to analysis record."""
    # Mock analysis record
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.raw_content = None
    mock_analysis.title = None
    mock_analysis.extraction_metadata = None
    mock_analysis.content_embedding = None

    # Mock database session
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # Workflow result with all fields
    workflow_result = {
        "raw_content": "This is the extracted content about React hooks...",
        "extraction_metadata": {
            "title": "React Hooks Tutorial",
            "word_count": 1500,
            "author": "Test Author",
        },
        "content_embedding": [0.1] * 1536,  # 1536-dimensional vector
    }

    with patch("app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal", return_value=mock_db_session):
        persister = DataPersister()
        result = await persister.persist(mock_analysis_id, workflow_result)

    # Verify success
    assert result is True

    # Verify all fields were set
    assert mock_analysis.raw_content == workflow_result["raw_content"]
    assert mock_analysis.title == "React Hooks Tutorial"
    assert mock_analysis.extraction_metadata == workflow_result["extraction_metadata"]
    assert mock_analysis.content_embedding == workflow_result["content_embedding"]

    # Verify commit was called
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_data_persister_persist_partial_data(mock_analysis_id):
    """Test persistence with partial workflow data (only some fields present)."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.raw_content = None
    mock_analysis.title = None
    mock_analysis.extraction_metadata = None
    mock_analysis.content_embedding = None

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # Workflow result with only raw_content (no embedding, no metadata)
    workflow_result = {
        "raw_content": "Partial content...",
    }

    with patch("app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal", return_value=mock_db_session):
        persister = DataPersister()
        result = await persister.persist(mock_analysis_id, workflow_result)

    assert result is True
    assert mock_analysis.raw_content == "Partial content..."
    # Title and embedding should not be set (no metadata/embedding in result)
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_data_persister_persist_analysis_not_found(mock_analysis_id):
    """Test persistence when analysis record is not found."""
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Analysis not found
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    workflow_result = {"raw_content": "Content..."}

    with patch("app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal", return_value=mock_db_session):
        persister = DataPersister()
        result = await persister.persist(mock_analysis_id, workflow_result)

    # Should return False when analysis not found
    assert result is False
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_data_persister_persist_database_error(mock_analysis_id):
    """Test persistence handles database errors gracefully."""
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    workflow_result = {"raw_content": "Content..."}

    with patch("app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal", return_value=mock_db_session):
        persister = DataPersister()
        with pytest.raises(RuntimeError, match="Failed to persist analysis data"):
            await persister.persist(mock_analysis_id, workflow_result)


@pytest.mark.asyncio
async def test_data_persister_persist_empty_result(mock_analysis_id):
    """Test persistence with empty workflow result."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # Empty workflow result
    workflow_result = {}

    with patch("app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal", return_value=mock_db_session):
        persister = DataPersister()
        result = await persister.persist(mock_analysis_id, workflow_result)

    # Should still succeed (just no data to persist)
    assert result is True
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_data_persister_persist_extracts_title_from_metadata(mock_analysis_id):
    """Test that title is correctly extracted from extraction_metadata."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.title = None

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # extraction_metadata with title
    workflow_result = {
        "extraction_metadata": {
            "title": "My Amazing Article Title",
            "description": "Article description",
        },
    }

    with patch("app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal", return_value=mock_db_session):
        persister = DataPersister()
        await persister.persist(mock_analysis_id, workflow_result)

    # Verify title was extracted and set
    assert mock_analysis.title == "My Amazing Article Title"
    assert mock_analysis.extraction_metadata == workflow_result["extraction_metadata"]

