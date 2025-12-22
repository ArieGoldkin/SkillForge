"""Integration tests for read validation in AnalysisRepository."""

import uuid
from unittest.mock import patch

import pytest

from app.db.repositories.analysis_repository import AnalysisRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_by_id_real_database(db_session):
    """Test real database read."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    # Create test analysis
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/read-test-{analysis_id}",
        content_type="article",
        status="pending",
    )
    # Set required fields before changing to complete
    analysis.raw_content = "Test content"
    analysis.content_embedding = [0.1] * 1536
    analysis.extraction_metadata = {"title": "Test Article"}
    analysis.status = "complete"  # type: ignore[assignment]
    await db_session.commit()

    # Read with validation
    result = await repo.get_by_id(analysis_id, validate=True)

    assert result is not None
    assert result.raw_content == "Test content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_by_id_legacy_data(db_session):
    """Test legacy data handled gracefully."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    # Create legacy analysis (missing some fields)
    # Note: This test intentionally creates invalid data to test validation
    # We need to bypass the constraint by using SQL directly
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/legacy-{analysis_id}",
        content_type="article",
        status="pending",
    )
    await db_session.commit()
    # Use SQL to set status to complete without required fields (simulating legacy data)
    from sqlalchemy import text
    await db_session.execute(
        text("UPDATE analyses SET status = 'complete' WHERE id = :id").bindparams(id=analysis_id)
    )
    await db_session.commit()

    # Read with validation
    with patch("app.db.repositories.analysis_repository.logger") as mock_logger:
        result = await repo.get_by_id(analysis_id, validate=True)

        # Should return data but log warning
        assert result is not None
        mock_logger.warning.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_by_id_corrupted_data(db_session):
    """Test corrupted data handled."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    # Create analysis with wrong embedding dimensions
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/corrupted-{analysis_id}",
        content_type="article",
        status="pending",
    )
    # Set required fields before changing to complete
    analysis.raw_content = "Test content"
    analysis.extraction_metadata = {"title": "Test"}
    analysis.status = "complete"  # type: ignore[assignment]
    # Set wrong dimensions after status change (will fail constraint check)
    analysis.content_embedding = [0.1] * 768  # Wrong dimensions
    await db_session.commit()

    # Read with validation
    with patch("app.db.repositories.analysis_repository.logger") as mock_logger:
        result = await repo.get_by_id(analysis_id, validate=True)

        # Should return data but log warning
        assert result is not None
        mock_logger.warning.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_by_id_concurrent_reads(db_session):
    """Test concurrent reads handled."""
    import asyncio

    repo = AnalysisRepository(session=db_session)
    analysis_ids = [uuid.uuid4() for _ in range(10)]

    # Create multiple analyses
    for analysis_id in analysis_ids:
        analysis = await repo.create_analysis(
            analysis_id=analysis_id,
            url=f"https://example.com/concurrent-{analysis_id}",
            content_type="article",
            status="complete",
        )
        analysis.raw_content = f"Content {analysis_id}"
        analysis.content_embedding = [0.1] * 1536
        analysis.extraction_metadata = {"title": "Test"}

    await db_session.commit()

    # Read concurrently
    async def read_one(aid):
        async with db_session.begin():
            repo_instance = AnalysisRepository(session=db_session)
            return await repo_instance.get_by_id(aid, validate=True)

    tasks = [read_one(aid) for aid in analysis_ids]
    results = await asyncio.gather(*tasks)

    # All should succeed
    assert all(r is not None for r in results)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_by_id_validation_performance(db_session):
    """Test validation performance acceptable."""
    import time

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/perf-{analysis_id}",
        content_type="article",
        status="pending",
    )
    # Set required fields before changing to complete
    analysis.raw_content = "Test content"
    analysis.content_embedding = [0.1] * 1536
    analysis.extraction_metadata = {"title": "Test"}
    analysis.status = "complete"  # type: ignore[assignment]
    await db_session.commit()

    # Measure read with validation
    start = time.time()
    result = await repo.get_by_id(analysis_id, validate=True)
    elapsed = time.time() - start

    assert result is not None
    # Should be fast (<20ms for read + validation)
    assert elapsed < 0.02, f"Read with validation took {elapsed * 1000:.2f}ms, expected <20ms"
