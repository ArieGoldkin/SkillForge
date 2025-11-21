"""Tests for SQLAlchemy model relationships."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AgentFinding,
    Analysis,
    AnalysisProgress,
    Artifact,
    TutoringMessage,
    TutoringSession,
)


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
    await db_session.flush()

    # Create artifact
    artifact = Artifact(
        analysis_id=analysis.id,
        markdown_content="# Implementation Guide",
        version=1,
        artifact_metadata={"topics": ["python", "fastapi"]},
    )
    db_session.add(artifact)
    await db_session.flush()

    assert artifact.id is not None
    assert artifact.analysis_id == analysis.id
    assert artifact.markdown_content == "# Implementation Guide"
    assert artifact.version == 1
    assert artifact.download_count == 0  # Default


@pytest.mark.asyncio
async def test_tutoring_session_model_optional_relationship(db_session: AsyncSession):
    """Test TutoringSession model with optional Analysis relationship."""
    # Create analysis first
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.flush()

    # Create tutoring session with analysis
    session = TutoringSession(
        analysis_id=analysis.id,
        status="active",
        session_metadata={"topic": "python"},
    )
    db_session.add(session)
    await db_session.flush()

    assert session.id is not None
    assert session.analysis_id == analysis.id
    assert session.status == "active"

    # Test optional relationship (can exist without analysis)
    standalone_session = TutoringSession(status="active")
    db_session.add(standalone_session)
    await db_session.flush()

    assert standalone_session.analysis_id is None


@pytest.mark.asyncio
async def test_tutoring_message_model_relationship(db_session: AsyncSession):
    """Test TutoringMessage model relationship with TutoringSession."""
    # Create session first
    session = TutoringSession(status="active")
    db_session.add(session)
    await db_session.flush()

    # Create message
    message = TutoringMessage(
        session_id=session.id,
        role="user",
        content="How do I use FastAPI?",
    )
    db_session.add(message)
    await db_session.flush()

    assert message.id is not None
    assert message.session_id == session.id
    assert message.role == "user"
    assert message.content == "How do I use FastAPI?"


@pytest.mark.asyncio
async def test_analysis_progress_model_relationship(db_session: AsyncSession):
    """Test AnalysisProgress model relationship with Analysis."""
    # Create analysis first
    analysis = Analysis(url="https://example.com", content_type="article", status="pending")
    db_session.add(analysis)
    await db_session.flush()

    # Create progress entry
    progress = AnalysisProgress(
        analysis_id=analysis.id,
        stage="extraction",
        status="in_progress",
        progress_data={"percent": 50},
    )
    db_session.add(progress)
    await db_session.flush()

    assert progress.id is not None
    assert progress.analysis_id == analysis.id
    assert progress.stage == "extraction"
    assert progress.status == "in_progress"
    assert progress.progress_data == {"percent": 50}
