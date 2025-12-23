"""Unit tests for DataPersister (Pydantic v2 validation)."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.schemas.workflow_result import WorkflowResult
from app.domains.analysis.services.persistence.data_persister import DataPersister


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.fixture
def valid_workflow_result_dict():
    """Create valid workflow result dict for tests."""
    return {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test Article",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }


# ============================================================================
# Valid Persistence Tests
# ============================================================================


@pytest.mark.asyncio
async def test_persister_valid_workflow_result(mock_analysis_id, valid_workflow_result_dict):
    """Test valid WorkflowResult persists."""
    from app.domains.analysis.schemas.workflow_result import ContentRef, ExtractionMetadata

    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test Article",
        word_count=1000,
        char_count=5000,
    )
    workflow_result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.raw_content = None
    mock_analysis.title = None

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        result = await persister.persist(mock_analysis_id, workflow_result)

    assert result is True
    assert mock_analysis.raw_content == "Test content"
    assert mock_analysis.title == "Test Article"
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_persister_valid_dict(mock_analysis_id, valid_workflow_result_dict):
    """Test valid dict validates and persists."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.raw_content = None
    mock_analysis.title = None

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        result = await persister.persist(mock_analysis_id, valid_workflow_result_dict)

    assert result is True
    assert mock_analysis.raw_content == "Test content"
    mock_db_session.commit.assert_called_once()


# ============================================================================
# Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_persister_invalid_dict_raises(mock_analysis_id):
    """Test invalid dict raises ValueError."""
    invalid_result = {
        "raw_content": "",  # Empty content
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 100,  # Wrong dimensions
    }

    mock_db_session = AsyncMock()
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(ValueError, match="Invalid workflow result"):
            await persister.persist(mock_analysis_id, invalid_result)

    mock_db_session.commit.assert_not_called()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_persister_missing_analysis(mock_analysis_id, valid_workflow_result_dict):
    """Test missing analysis raises ValueError."""
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(ValueError, match="not found"):
            await persister.persist(mock_analysis_id, valid_workflow_result_dict)

    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_persister_database_error(mock_analysis_id, valid_workflow_result_dict):
    """Test database errors handled."""
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(RuntimeError, match="Failed to persist analysis data"):
            await persister.persist(mock_analysis_id, valid_workflow_result_dict)


@pytest.mark.asyncio
async def test_persister_transaction_rollback(mock_analysis_id, valid_workflow_result_dict):
    """Test transaction rollback on error."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.commit.side_effect = RuntimeError("Commit failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(RuntimeError):
            await persister.persist(mock_analysis_id, valid_workflow_result_dict)


# ============================================================================
# Data Extraction Tests
# ============================================================================


@pytest.mark.asyncio
async def test_persister_title_extraction(mock_analysis_id, valid_workflow_result_dict):
    """Test title extracted from metadata."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.title = None

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        await persister.persist(mock_analysis_id, valid_workflow_result_dict)

    assert mock_analysis.title == "Test Article"


@pytest.mark.asyncio
async def test_persister_metadata_serialization(mock_analysis_id, valid_workflow_result_dict):
    """Test metadata properly serialized."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        await persister.persist(mock_analysis_id, valid_workflow_result_dict)

    assert isinstance(mock_analysis.extraction_metadata, dict)
    assert mock_analysis.extraction_metadata["title"] == "Test Article"


@pytest.mark.asyncio
async def test_persister_embedding_persistence(mock_analysis_id, valid_workflow_result_dict):
    """Test embedding properly persisted."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        await persister.persist(mock_analysis_id, valid_workflow_result_dict)

    assert mock_analysis.content_embedding == [0.1] * 1536
    assert len(mock_analysis.content_embedding) == 1536


@pytest.mark.asyncio
async def test_persister_raw_content_persistence(mock_analysis_id, valid_workflow_result_dict):
    """Test raw content properly persisted."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        await persister.persist(mock_analysis_id, valid_workflow_result_dict)

    assert mock_analysis.raw_content == "Test content"


# ============================================================================
# No Silent Warnings Tests
# ============================================================================


@pytest.mark.asyncio
async def test_persister_no_silent_warnings(mock_analysis_id):
    """Test no warnings logged, exceptions raised."""
    invalid_result = {
        "raw_content": "",  # Empty - should fail validation
    }

    mock_db_session = AsyncMock()
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(ValueError):
            await persister.persist(mock_analysis_id, invalid_result)

    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_persister_missing_raw_content_raises(mock_analysis_id):
    """Test missing raw_content raises."""
    invalid_result = {
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }

    mock_db_session = AsyncMock()
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(ValueError):
            await persister.persist(mock_analysis_id, invalid_result)


@pytest.mark.asyncio
async def test_persister_missing_metadata_raises(mock_analysis_id):
    """Test missing metadata raises."""
    invalid_result = {
        "raw_content": "Test content",
        "content_embedding": [0.1] * 1536,
    }

    mock_db_session = AsyncMock()
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(ValueError):
            await persister.persist(mock_analysis_id, invalid_result)


@pytest.mark.asyncio
async def test_persister_missing_embedding_raises(mock_analysis_id):
    """Test missing embedding raises."""
    invalid_result = {
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
    }

    mock_db_session = AsyncMock()
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(ValueError):
            await persister.persist(mock_analysis_id, invalid_result)


@pytest.mark.asyncio
async def test_persister_error_messages_clear(mock_analysis_id):
    """Test error messages are clear."""
    invalid_result = {
        "raw_content": "",
    }

    mock_db_session = AsyncMock()
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(ValueError) as exc_info:
            await persister.persist(mock_analysis_id, invalid_result)

        assert "Invalid workflow result" in str(exc_info.value)


@pytest.mark.asyncio
async def test_persister_all_or_nothing(mock_analysis_id, valid_workflow_result_dict):
    """Test all-or-nothing persistence."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.commit.side_effect = RuntimeError("Commit failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
        return_value=mock_db_session,
    ):
        persister = DataPersister()
        with pytest.raises(RuntimeError):
            await persister.persist(mock_analysis_id, valid_workflow_result_dict)
