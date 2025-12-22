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
        url=f"https://example.com/test-{analysis_id}",
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
        url=f"https://example.com/test-{analysis_id}",
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
        url=f"https://example.com/test-{analysis_id}",
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
        url=f"https://example.com/test-{analysis_id}",
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
        url=f"https://example.com/test-{analysis_id}",
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
    # Compare embeddings properly (pgvector may return different array types and floating point precision)
    expected_embedding = valid_workflow_result_dict["content_embedding"]
    if hasattr(analysis.content_embedding, "tolist"):
        # Convert numpy array to list for comparison
        actual_embedding = analysis.content_embedding.tolist()
    else:
        actual_embedding = list(analysis.content_embedding) if analysis.content_embedding else None
    
    # Use approximate comparison for floating point values
    assert actual_embedding is not None, "Embedding should be persisted"
    assert len(actual_embedding) == len(expected_embedding), (
        f"Embedding dimensions don't match. Expected {len(expected_embedding)}, got {len(actual_embedding)}"
    )
    # Check values are approximately equal (floating point precision)
    for i, (actual, expected) in enumerate(zip(actual_embedding, expected_embedding)):
        assert abs(actual - expected) < 1e-6, (
            f"Embedding value at index {i} differs: {actual} != {expected}"
        )
    # Compare metadata (Pydantic may add None values for optional fields)
    expected_metadata = valid_workflow_result_dict["extraction_metadata"]
    actual_metadata = analysis.extraction_metadata
    # Check required fields match
    assert actual_metadata["title"] == expected_metadata["title"]
    assert actual_metadata["word_count"] == expected_metadata["word_count"]
    assert actual_metadata["char_count"] == expected_metadata["char_count"]


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
        url=f"https://example.com/test-{analysis_id}",
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
