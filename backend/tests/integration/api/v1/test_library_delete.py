"""Integration tests for delete analysis endpoint."""

import uuid
from datetime import UTC, datetime

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.db.models.agent_finding import AgentFinding
from app.db.models.analysis import Analysis
from app.db.models.artifact import Artifact
from app.db.models.progress import AnalysisProgress


@pytest.mark.asyncio
async def test_delete_analysis_cascades(requires_database, reset_engine_connections, db_session):
    """DELETE /api/v1/analyses/{id} removes analysis and related rows."""
    analysis_id = uuid.uuid4()
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com/article",
        content_type="article",
        status="complete",
        created_at=datetime.now(UTC),
    )
    finding = AgentFinding(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        agent_type="implementation_planner",
        findings={"steps": []},
        created_at=datetime.now(UTC),
    )
    artifact = Artifact(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        markdown_content="# Test",
        version=1,
        artifact_metadata={},
        created_at=datetime.now(UTC),
    )
    progress = AnalysisProgress(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        stage="extraction",
        status="complete",
        progress_data={},
        created_at=datetime.now(UTC),
    )
    db_session.add_all([analysis, finding, artifact, progress])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/analyses/{analysis_id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify rows are gone
    result = await db_session.execute(select(Analysis).where(Analysis.id == analysis_id))
    assert result.scalars().first() is None

    for model in (AgentFinding, Artifact, AnalysisProgress):
        result = await db_session.execute(select(model).where(model.analysis_id == analysis_id))
        assert result.scalars().first() is None


@pytest.mark.asyncio
async def test_delete_analysis_not_found(reset_engine_connections):
    """DELETE /api/v1/analyses/{id} returns 404 when missing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/analyses/{uuid.uuid4()}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
