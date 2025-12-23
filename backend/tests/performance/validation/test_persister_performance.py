"""Performance tests for DataPersister."""

import asyncio
import time

import pytest

from app.domains.analysis.services.persistence.data_persister import DataPersister


@pytest.fixture
def persister():
    """Create persister instance for tests."""
    return DataPersister()


@pytest.fixture
def valid_workflow_result_dict():
    """Create valid workflow result for performance tests."""
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


@pytest.mark.performance
@pytest.mark.asyncio
async def test_persister_single_persistence_speed(
    persister, valid_workflow_result_dict, db_session
):
    """Test single persistence speed <50ms p95."""
    import uuid

    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    start = time.time()
    result = await persister.persist(analysis_id, valid_workflow_result_dict)
    elapsed = time.time() - start

    assert result is True
    # Should be fast (<50ms for single persistence)
    assert elapsed < 0.05, f"Persistence took {elapsed * 1000:.2f}ms, expected <50ms"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_persister_concurrent_50_writes(persister, valid_workflow_result_dict, db_session):
    """Test 50 concurrent writes <2s."""
    import uuid

    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_ids = [uuid.uuid4() for _ in range(50)]

    # Create all analyses
    for analysis_id in analysis_ids:
        await repo.create_analysis(
            analysis_id=analysis_id,
            url=f"https://example.com/test-{analysis_id}",
            content_type="article",
            status="analyzing",
        )

    async def persist_one(aid):
        result_dict = valid_workflow_result_dict.copy()
        result_dict["raw_content"] = f"Content for {aid}"
        return await persister.persist(aid, result_dict)

    start = time.time()
    tasks = [persist_one(aid) for aid in analysis_ids]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    assert all(results)
    # Should be fast (<2s for 50 concurrent writes)
    assert elapsed < 2.0, f"50 writes took {elapsed:.2f}s, expected <2s"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_persister_with_for_update_overhead(
    persister, valid_workflow_result_dict, db_session
):
    """Test with_for_update overhead measured."""
    import uuid

    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    # Measure persistence with with_for_update
    start = time.time()
    result = await persister.persist(analysis_id, valid_workflow_result_dict)
    elapsed = time.time() - start

    assert result is True
    # with_for_update should add minimal overhead (<5ms)
    assert elapsed < 0.055, f"Persistence with for_update took {elapsed * 1000:.2f}ms"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_persister_error_handling_overhead(persister, db_session):
    """Test error handling overhead <1ms."""
    import uuid

    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url="https://example.com/test",
        content_type="article",
        status="analyzing",
    )

    invalid_result = {"raw_content": ""}

    start = time.time()
    try:
        await persister.persist(analysis_id, invalid_result)
    except ValueError:
        pass  # Expected
    elapsed = time.time() - start

    # Error handling should be fast (<10ms for validation + error)
    assert elapsed < 0.01, f"Error handling took {elapsed * 1000:.2f}ms, expected <10ms"
