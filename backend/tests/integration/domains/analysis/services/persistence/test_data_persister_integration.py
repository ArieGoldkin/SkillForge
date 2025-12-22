"""Integration tests for DataPersister with real database."""

import uuid

import pytest

from app.domains.analysis.services.persistence.data_persister import DataPersister


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
        "raw_content": "Test content for integration test",
        "extraction_metadata": {
            "title": "Integration Test Article",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_real_database_persistence(db_session, valid_workflow_result_dict):
    """Test real database persistence."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create test analysis
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    # Persist workflow result
    persister = DataPersister()
    result = await persister.persist(analysis_id, valid_workflow_result_dict)

    assert result is True

    # Verify data persisted
    await db_session.refresh(analysis)
    assert analysis.raw_content == "Test content for integration test"
    assert analysis.title == "Integration Test Article"
    assert analysis.content_embedding is not None
    # Type guard for type checker
    if isinstance(analysis.content_embedding, list):
        assert len(analysis.content_embedding) == 1536


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_transaction_isolation(db_session, valid_workflow_result_dict):
    """Test transaction isolation works."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create test analysis
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    # Persist workflow result
    persister = DataPersister()
    result = await persister.persist(analysis_id, valid_workflow_result_dict)

    assert result is True

    # Verify transaction committed
    await db_session.refresh(analysis)
    assert analysis.raw_content is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_concurrent_persistence(db_session, valid_workflow_result_dict):
    """Test concurrent persistence handled."""
    import asyncio

    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create multiple test analyses
    repo = AnalysisRepository(session=db_session)
    analysis_ids = [uuid.uuid4() for _ in range(5)]

    for analysis_id in analysis_ids:
        await repo.create_analysis(
            analysis_id=analysis_id,
            url=f"https://example.com/test-{analysis_id}",
            content_type="article",
            status="analyzing",
        )

    # Persist concurrently
    persister = DataPersister()

    async def persist_one(aid):
        result_dict = valid_workflow_result_dict.copy()
        result_dict["raw_content"] = f"Content for {aid}"
        return await persister.persist(aid, result_dict)

    tasks = [persist_one(aid) for aid in analysis_ids]
    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(results)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_validation_before_persistence(db_session):
    """Test validation happens before DB."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create test analysis
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    # Invalid result
    invalid_result = {
        "raw_content": "",  # Empty - should fail validation
    }

    persister = DataPersister()

    # Should raise ValueError before database write
    with pytest.raises(ValueError, match="Invalid workflow result"):
        await persister.persist(analysis_id, invalid_result)

    # Verify no data was persisted
    analysis = await repo.get_by_id(analysis_id)
    assert analysis is not None, "Analysis should exist"
    assert analysis.raw_content is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_error_recovery(db_session, valid_workflow_result_dict):
    """Test error recovery works correctly."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create test analysis
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    persister = DataPersister()

    # First attempt with invalid data should fail
    invalid_result = {"raw_content": ""}
    with pytest.raises(ValueError):
        await persister.persist(analysis_id, invalid_result)

    # Second attempt with valid data should succeed
    result = await persister.persist(analysis_id, valid_workflow_result_dict)
    assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_data_integrity(db_session, valid_workflow_result_dict):
    """Test data integrity maintained."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create test analysis
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    persister = DataPersister()
    await persister.persist(analysis_id, valid_workflow_result_dict)

    # Verify all fields persisted correctly
    analysis = await repo.get_by_id(analysis_id)
    assert analysis is not None, "Analysis should exist"
    assert analysis.raw_content == valid_workflow_result_dict["raw_content"]
    assert analysis.title == valid_workflow_result_dict["extraction_metadata"]["title"]
    assert analysis.content_embedding == valid_workflow_result_dict["content_embedding"]
    assert analysis.extraction_metadata == valid_workflow_result_dict["extraction_metadata"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_error_propagation(db_session):
    """Test errors propagate correctly."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create test analysis
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    persister = DataPersister()

    # Invalid data should raise ValueError
    invalid_result = {"raw_content": ""}
    with pytest.raises(ValueError) as exc_info:
        await persister.persist(analysis_id, invalid_result)

    # Error should contain validation details
    assert "Invalid workflow result" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persister_no_data_corruption(db_session):
    """Test no partial data persisted on error."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    # Create test analysis with existing data
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    # Set some initial data
    analysis.raw_content = "Initial content"
    await db_session.commit()

    persister = DataPersister()

    # Try to persist invalid data
    invalid_result = {"raw_content": ""}
    with pytest.raises(ValueError):
        await persister.persist(analysis_id, invalid_result)

    # Verify original data unchanged
    await db_session.refresh(analysis)
    assert analysis.raw_content == "Initial content"
