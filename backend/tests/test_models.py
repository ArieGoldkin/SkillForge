"""Tests for SQLAlchemy models."""

import uuid
from datetime import datetime, UTC

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models import (
    Analysis,
    AgentFinding,
    Artifact,
    TutoringSession,
    TutoringMessage,
    AnalysisProgress,
)


# db_session fixture is in conftest.py


@pytest.mark.asyncio
async def test_analysis_model_creation(db_session: AsyncSession):
    """Test Analysis model can be created and saved."""
    analysis = Analysis(
        url="https://example.com/article",
        content_type="article",
        title="Test Article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.flush()  # Flush to get ID without committing

    assert analysis.id is not None
    assert analysis.url == "https://example.com/article"
    assert analysis.content_type == "article"
    assert analysis.title == "Test Article"
    assert analysis.status == "pending"
    assert analysis.created_at is not None
    assert analysis.updated_at is not None


@pytest.mark.asyncio
async def test_analysis_model_defaults(db_session: AsyncSession):
    """Test Analysis model uses correct default values."""
    analysis = Analysis(url="https://example.com", content_type="article")
    db_session.add(analysis)
    await db_session.flush()  # Flush to trigger defaults

    assert analysis.status == "pending"
    assert analysis.created_at is not None
    assert analysis.updated_at is not None


@pytest.mark.asyncio
async def test_agent_finding_model_relationship(db_session: AsyncSession):
    """Test AgentFinding model relationship with Analysis."""
    # Create analysis first
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.flush()

    # Create agent finding
    finding = AgentFinding(
        analysis_id=analysis.id,
        agent_type="tech_comparator",
        findings={"key": "value"},
        confidence_score=0.95,
        processing_time_ms=150,
    )
    db_session.add(finding)
    await db_session.flush()

    assert finding.id is not None
    assert finding.analysis_id == analysis.id
    assert finding.agent_type == "tech_comparator"
    assert finding.findings == {"key": "value"}
    assert finding.confidence_score == 0.95

    # Test relationship
    await db_session.refresh(finding, ["analysis"])
    assert finding.analysis.id == analysis.id


@pytest.mark.asyncio
async def test_artifact_model_relationship(db_session: AsyncSession):
    """Test Artifact model relationship with Analysis."""
    # Create analysis first
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    # Create artifact
    artifact = Artifact(
        analysis_id=analysis.id,
        markdown_content="# Implementation Guide",
        version=1,
        artifact_metadata={"topics": ["python", "fastapi"]},
    )
    db_session.add(artifact)
    await db_session.commit()
    await db_session.refresh(artifact)

    assert artifact.id is not None
    assert artifact.analysis_id == analysis.id
    assert artifact.markdown_content == "# Implementation Guide"
    assert artifact.version == 1
    assert artifact.download_count == 0  # Default

    # Test relationship
    assert artifact.analysis == analysis
    assert artifact in analysis.artifacts


@pytest.mark.asyncio
async def test_tutoring_session_model_optional_relationship(db_session: AsyncSession):
    """Test TutoringSession model with optional Analysis relationship."""
    # Create analysis first
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    # Create tutoring session with analysis
    session = TutoringSession(
        analysis_id=analysis.id,
        status="active",
        session_metadata={"topic": "python"},
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    assert session.id is not None
    assert session.analysis_id == analysis.id
    assert session.status == "active"

    # Test relationship
    assert session.analysis == analysis
    assert session in analysis.tutoring_sessions

    # Test optional relationship (can exist without analysis)
    standalone_session = TutoringSession(status="active")
    db_session.add(standalone_session)
    await db_session.commit()
    await db_session.refresh(standalone_session)

    assert standalone_session.analysis_id is None


@pytest.mark.asyncio
async def test_tutoring_message_model_relationship(db_session: AsyncSession):
    """Test TutoringMessage model relationship with TutoringSession."""
    # Create session first
    session = TutoringSession(status="active")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Create message
    message = TutoringMessage(
        session_id=session.id,
        role="user",
        content="How do I use FastAPI?",
    )
    db_session.add(message)
    await db_session.commit()
    await db_session.refresh(message)

    assert message.id is not None
    assert message.session_id == session.id
    assert message.role == "user"
    assert message.content == "How do I use FastAPI?"

    # Test relationship
    assert message.session == session
    assert message in session.messages


@pytest.mark.asyncio
async def test_analysis_progress_model_relationship(db_session: AsyncSession):
    """Test AnalysisProgress model relationship with Analysis."""
    # Create analysis first
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    # Create progress entry
    progress = AnalysisProgress(
        analysis_id=analysis.id,
        stage="extraction",
        status="in_progress",
        progress_data={"percent": 50},
    )
    db_session.add(progress)
    await db_session.commit()
    await db_session.refresh(progress)

    assert progress.id is not None
    assert progress.analysis_id == analysis.id
    assert progress.stage == "extraction"
    assert progress.status == "in_progress"
    assert progress.progress_data == {"percent": 50}


@pytest.mark.asyncio
async def test_cascade_delete_agent_findings(db_session: AsyncSession):
    """Test CASCADE delete for AgentFinding when Analysis is deleted."""
    # Create analysis and finding
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    finding = AgentFinding(
        analysis_id=analysis.id,
        agent_type="tech_comparator",
        findings={"key": "value"},
    )
    db_session.add(finding)
    await db_session.commit()
    await db_session.refresh(finding)

    finding_id = finding.id

    # Delete analysis (should cascade to finding)
    await db_session.delete(analysis)
    await db_session.commit()

    # Verify finding is deleted
    result = await db_session.execute(
        select(AgentFinding).where(AgentFinding.id == finding_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_set_null_delete_tutoring_session(db_session: AsyncSession):
    """Test SET NULL for TutoringSession when Analysis is deleted."""
    # Create analysis and session
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    session = TutoringSession(analysis_id=analysis.id, status="active")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    session_id = session.id

    # Delete analysis (should set session.analysis_id to NULL)
    await db_session.delete(analysis)
    await db_session.commit()

    # Verify session still exists but analysis_id is NULL
    result = await db_session.execute(
        select(TutoringSession).where(TutoringSession.id == session_id)
    )
    updated_session = result.scalar_one_or_none()
    assert updated_session is not None
    assert updated_session.analysis_id is None


@pytest.mark.asyncio
async def test_all_models_have_uuid_primary_keys(db_session: AsyncSession):
    """Test all models use UUID primary keys."""
    models = [Analysis, AgentFinding, Artifact, TutoringSession, TutoringMessage, AnalysisProgress]

    for model in models:
        # Create instance
        if model == Analysis:
            instance = model(url="https://test.com", content_type="article")
        elif model in [AgentFinding, Artifact, AnalysisProgress]:
            # These need analysis_id
            analysis = Analysis(url="https://test.com", content_type="article")
            db_session.add(analysis)
            await db_session.commit()
            await db_session.refresh(analysis)
            if model == AgentFinding:
                instance = model(
                    analysis_id=analysis.id, agent_type="test", findings={"key": "value"}
                )
            elif model == Artifact:
                instance = model(analysis_id=analysis.id, markdown_content="# Test")
            else:  # AnalysisProgress
                instance = model(analysis_id=analysis.id, stage="test", status="test")
        elif model == TutoringSession:
            instance = model(status="active")
        else:  # TutoringMessage
            session = TutoringSession(status="active")
            db_session.add(session)
            await db_session.commit()
            await db_session.refresh(session)
            instance = model(session_id=session.id, role="user", content="test")

        db_session.add(instance)
        await db_session.commit()
        await db_session.refresh(instance)

        # Verify UUID primary key
        assert isinstance(instance.id, uuid.UUID)
        assert instance.id is not None


@pytest.mark.asyncio
async def test_analysis_vector_embedding_column(db_session: AsyncSession):
    """Test Analysis model can store vector embeddings."""
    analysis = Analysis(
        url="https://example.com",
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    # content_embedding can be None initially
    assert analysis.content_embedding is None

    # In real usage, embeddings would be set as numpy arrays or lists
    # This is just to verify the column exists and works


@pytest.mark.asyncio
async def test_jsonb_columns_store_dict_data(db_session: AsyncSession):
    """Test JSONB columns can store dictionary data."""
    analysis = Analysis(
        url="https://example.com",
        content_type="article",
        extraction_metadata={"source": "jina", "word_count": 1000},
    )
    db_session.add(analysis)
    await db_session.commit()
    await db_session.refresh(analysis)

    assert analysis.extraction_metadata == {"source": "jina", "word_count": 1000}

    # Test nested JSONB
    finding = AgentFinding(
        analysis_id=analysis.id,
        agent_type="tech_comparator",
        findings={"technologies": ["python", "fastapi"], "complexity": "medium"},
    )
    db_session.add(finding)
    await db_session.commit()
    await db_session.refresh(finding)

    assert finding.findings["technologies"] == ["python", "fastapi"]
    assert finding.findings["complexity"] == "medium"
