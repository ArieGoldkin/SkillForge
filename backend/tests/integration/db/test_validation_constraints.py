"""Integration tests for database validation constraints."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.repositories.analysis_repository import AnalysisRepository


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_complete_must_have_content(db_session):
    """Test constraint prevents complete status without raw_content."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    # Create analysis without content
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/constraint-test-{analysis_id}",
        content_type="article",
        status="pending",
    )

    # Try to set status to complete without content - should fail
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("UPDATE analyses SET status = 'complete' WHERE id = :id").bindparams(
                id=analysis_id
            )
        )
        await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_embedding_dimensions(db_session):
    """Test constraint prevents wrong embedding dimensions."""
    from tests.integration.conftest import create_complete_analysis

    analysis_id = uuid.uuid4()
    # Create a valid complete analysis with all required fields
    analysis = await create_complete_analysis(
        db_session,
        id=analysis_id,
        url=f"https://example.com/embedding-test-{analysis_id}",
        content_embedding=[0.1] * 1536,  # Start with correct dimensions
    )
    await db_session.commit()

    # Try to set wrong dimension embedding - should fail dimension check
    # pgvector validates dimensions before constraint check, so we get DataError
    # Use raw SQL with vector literal format for pgvector
    # pgvector requires literal format: '[0.1,0.1,...]'::vector
    from sqlalchemy.exc import DBAPIError

    with pytest.raises((IntegrityError, DBAPIError)):
        # Convert list to PostgreSQL vector literal format
        wrong_embedding_list = [0.1] * 768
        wrong_embedding_str = "[" + ",".join(str(v) for v in wrong_embedding_list) + "]"
        # Use f-string for vector literal (safe here - values are controlled)
        await db_session.execute(
            text(
                f"""
                UPDATE analyses 
                SET content_embedding = '{wrong_embedding_str}'::vector 
                WHERE id = :analysis_id
                """
            ).bindparams(analysis_id=analysis_id)
        )
        await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_complete_must_have_metadata(db_session):
    """Test constraint prevents complete status without metadata."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/metadata-test-{analysis_id}",
        content_type="article",
        status="pending",
    )
    analysis.raw_content = "Test content"
    await db_session.commit()

    # Try to set status to complete without metadata - should fail
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text("UPDATE analyses SET status = 'complete' WHERE id = :id").bindparams(
                id=analysis_id
            )
        )
        await db_session.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_allows_valid_complete(db_session):
    """Test constraint allows valid complete status."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/valid-complete-{analysis_id}",
        content_type="article",
        status="pending",
    )
    analysis.raw_content = "Test content"
    analysis.content_embedding = [0.1] * 1536
    analysis.extraction_metadata = {"title": "Test Article"}
    await db_session.commit()

    # Set status to complete - should succeed
    await db_session.execute(
        text("UPDATE analyses SET status = 'complete' WHERE id = :id").bindparams(id=analysis_id)
    )
    await db_session.commit()

    # Verify status updated
    result = await db_session.execute(
        text("SELECT status FROM analyses WHERE id = :id").bindparams(id=analysis_id)
    )
    status = result.scalar_one()
    assert status == "complete"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_allows_failed_without_content(db_session):
    """Test constraint allows failed status without content."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/failed-test-{analysis_id}",
        content_type="article",
        status="pending",
    )
    # No content, no metadata
    await db_session.commit()

    # Set status to failed - should succeed (constraints don't apply)
    await db_session.execute(
        text("UPDATE analyses SET status = 'failed' WHERE id = :id").bindparams(id=analysis_id)
    )
    await db_session.commit()

    # Verify status updated
    result = await db_session.execute(
        text("SELECT status FROM analyses WHERE id = :id").bindparams(id=analysis_id)
    )
    status = result.scalar_one()
    assert status == "failed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_constraint_allows_null_embedding(db_session):
    """Test constraint allows NULL embedding."""
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()

    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/null-embedding-{analysis_id}",
        content_type="article",
        status="pending",
    )
    # Set required fields before changing to complete
    analysis.raw_content = "Test content"
    analysis.extraction_metadata = {"title": "Test"}
    analysis.status = "complete"  # type: ignore[assignment]
    # No embedding - should be allowed
    await db_session.commit()

    # Verify constraint allows NULL
    result = await db_session.execute(
        text("SELECT content_embedding FROM analyses WHERE id = :id").bindparams(id=analysis_id)
    )
    embedding = result.scalar_one()
    assert embedding is None
