"""Tests for SQLAlchemy models - basic model creation and validation."""

import uuid
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AgentFinding,
    Analysis,
    AnalysisProgress,
    Artifact,
    TutoringMessage,
    TutoringSession,
)
from tests.integration.conftest import create_pending_analysis

# db_session fixture is in conftest.py


@pytest.mark.asyncio
async def test_analysis_model_creation(db_session: AsyncSession):
    """Test Analysis model can be created and saved."""
    test_url = f"https://example.com/article-{uuid4()}"
    analysis = Analysis(
        url=test_url,
        content_type="article",
        title="Test Article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.flush()  # Flush to get ID without committing

    assert analysis.id is not None
    assert analysis.url == test_url
    assert analysis.content_type == "article"
    assert analysis.title == "Test Article"
    assert analysis.status == "pending"
    assert analysis.created_at is not None
    assert analysis.updated_at is not None


@pytest.mark.asyncio
async def test_analysis_model_defaults(db_session: AsyncSession):
    """Test Analysis model uses correct default values."""
    test_url = f"https://example.com/test-{uuid4()}"
    analysis = Analysis(url=test_url, content_type="article")
    db_session.add(analysis)
    await db_session.flush()  # Flush to trigger defaults

    assert analysis.status == "pending"
    assert analysis.created_at is not None
    assert analysis.updated_at is not None


# Relationship tests moved to test_models_relationships.py to keep file size under 300 lines


# Cascade/SET NULL delete tests moved to test_models_relationships.py


@pytest.mark.asyncio
async def test_all_models_have_uuid_primary_keys(db_session: AsyncSession):
    """Test all models use UUID primary keys."""
    # Test Analysis model
    analysis = Analysis(url="https://test.com", content_type="article")
    db_session.add(analysis)
    await db_session.flush()
    assert isinstance(analysis.id, uuid.UUID)

    # Test AgentFinding model
    finding = AgentFinding(analysis_id=analysis.id, agent_type="test", findings={"key": "value"})
    db_session.add(finding)
    await db_session.flush()
    assert isinstance(finding.id, uuid.UUID)

    # Test Artifact model
    artifact = Artifact(analysis_id=analysis.id, markdown_content="# Test")
    db_session.add(artifact)
    await db_session.flush()
    assert isinstance(artifact.id, uuid.UUID)

    # Test TutoringSession model
    session = TutoringSession(status="active")
    db_session.add(session)
    await db_session.flush()
    assert isinstance(session.id, uuid.UUID)

    # Test TutoringMessage model
    message = TutoringMessage(session_id=session.id, role="user", content="test")
    db_session.add(message)
    await db_session.flush()
    assert isinstance(message.id, uuid.UUID)

    # Test AnalysisProgress model
    progress = AnalysisProgress(analysis_id=analysis.id, stage="test", status="test")
    db_session.add(progress)
    await db_session.flush()
    assert isinstance(progress.id, uuid.UUID)


@pytest.mark.asyncio
async def test_analysis_vector_embedding_column(db_session: AsyncSession):
    """Test Analysis model can store vector embeddings."""
    test_url = f"https://example.com/test-{uuid4()}"
    analysis = Analysis(
        url=test_url,
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.flush()

    # content_embedding can be None initially
    assert analysis.content_embedding is None

    # In real usage, embeddings would be set as numpy arrays or lists
    # This is just to verify the column exists and works


@pytest.mark.asyncio
async def test_jsonb_columns_store_dict_data(db_session: AsyncSession):
    """Test JSONB columns can store dictionary data."""
    test_url = f"https://example.com/test-{uuid4()}"
    analysis = Analysis(
        url=test_url,
        content_type="article",
        extraction_metadata={"source": "jina", "word_count": 1000},
    )
    db_session.add(analysis)
    await db_session.flush()

    assert analysis.extraction_metadata == {"source": "jina", "word_count": 1000}

    # Test nested JSONB
    finding = AgentFinding(
        analysis_id=analysis.id,
        agent_type="tech_comparator",
        findings={"technologies": ["python", "fastapi"], "complexity": "medium"},
    )
    db_session.add(finding)
    await db_session.flush()

    assert finding.findings["technologies"] == ["python", "fastapi"]
    assert finding.findings["complexity"] == "medium"
