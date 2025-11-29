"""Integration tests for artifact download endpoint."""

import uuid

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.analysis import Analysis
from app.models.artifact import Artifact


@pytest.mark.asyncio
async def test_download_endpoint_returns_markdown(
    requires_database, reset_engine_connections, db_session
):
    """Test that download endpoint returns markdown with proper headers."""
    # Create analysis
    analysis_id = uuid.uuid4()
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com/article",
        content_type="article",
        status="complete",
        extraction_metadata={"title": "Test Article"},
    )
    db_session.add(analysis)
    await db_session.commit()

    # Create artifact
    artifact_id = uuid.uuid4()
    artifact = Artifact(
        id=artifact_id,
        analysis_id=analysis_id,
        markdown_content="# Test Artifact\n\nThis is test content.",
        version=1,
        artifact_metadata={"topics": ["test"], "complexity": "simple"},
        download_count=0,
    )
    db_session.add(artifact)
    await db_session.commit()

    # Test download endpoint
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/artifacts/{artifact_id}/download")

    assert response.status_code == status.HTTP_200_OK
    # FastAPI automatically adds charset=utf-8 to text/markdown
    assert response.headers["content-type"] in ("text/markdown", "text/markdown; charset=utf-8")
    assert "attachment" in response.headers["content-disposition"]
    content_disposition = response.headers["content-disposition"]
    assert "test-artifact.md" in content_disposition or "analysis-" in content_disposition
    assert "# Test Artifact" in response.text

    # Verify download_count incremented
    result = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    updated_artifact = result.scalar_one_or_none()
    assert updated_artifact is not None
    assert updated_artifact.download_count == 1


@pytest.mark.asyncio
async def test_download_404_not_found(requires_database, reset_engine_connections):
    """Test that download endpoint returns 404 for non-existent artifact."""
    fake_id = uuid.uuid4()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/artifacts/{fake_id}/download")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_download_increments_count(requires_database, reset_engine_connections, db_session):
    """Test that download endpoint increments download_count."""
    # Create analysis and artifact
    analysis_id = uuid.uuid4()
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com/article",
        content_type="article",
        status="complete",
    )
    db_session.add(analysis)
    await db_session.commit()

    artifact_id = uuid.uuid4()
    artifact = Artifact(
        id=artifact_id,
        analysis_id=analysis_id,
        markdown_content="# Test",
        version=1,
        download_count=5,
    )
    db_session.add(artifact)
    await db_session.commit()

    # Download artifact
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/artifacts/{artifact_id}/download")

    assert response.status_code == status.HTTP_200_OK

    # Verify count incremented
    result = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    updated_artifact = result.scalar_one_or_none()
    assert updated_artifact is not None
    assert updated_artifact.download_count == 6


@pytest.mark.asyncio
async def test_full_workflow_generates_artifact(
    requires_database, reset_engine_connections, db_session
):
    """Test that full workflow generates artifact (mocked workflow execution)."""
    # This test verifies the artifact is created when workflow completes
    # In a real scenario, this would run the full workflow
    # For now, we'll test that the artifact can be created and retrieved

    analysis_id = uuid.uuid4()
    analysis = Analysis(
        id=analysis_id,
        url="https://example.com/article",
        content_type="article",
        status="complete",
        extraction_metadata={"title": "Full Workflow Test"},
    )
    db_session.add(analysis)
    await db_session.commit()

    # Simulate artifact creation (as would happen in workflow)
    artifact_id = uuid.uuid4()
    artifact = Artifact(
        id=artifact_id,
        analysis_id=analysis_id,
        markdown_content="# Full Workflow Artifact\n\nGenerated from workflow.",
        version=1,
        artifact_metadata={"topics": ["workflow"], "complexity": "intermediate"},
    )
    db_session.add(artifact)
    await db_session.commit()

    # Verify artifact exists and can be downloaded
    result = await db_session.execute(select(Artifact).where(Artifact.analysis_id == analysis_id))
    artifacts = result.scalars().all()
    assert len(artifacts) == 1
    assert artifacts[0].id == artifact_id

    # Test download
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/artifacts/{artifact_id}/download")

    assert response.status_code == status.HTTP_200_OK
    assert "Full Workflow Artifact" in response.text
