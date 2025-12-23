"""Integration tests for artifact download endpoint."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import status
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.models.artifact import Artifact
from app.main import app
from tests.integration.conftest import create_complete_analysis


@pytest.mark.asyncio
async def test_download_endpoint_returns_markdown(
    requires_database, reset_engine_connections, db_session
):
    """Test that download endpoint returns markdown with proper headers."""
    # Create analysis
    analysis_id = uuid.uuid4()
    analysis = await create_complete_analysis(
        db_session,
        id=analysis_id,
        title="Test Article",
        extraction_metadata={"title": "Test Article"},
    )
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
    # Filename is generated from title "Test Article" -> "test-article.md"
    # or falls back to analysis ID if no title
    assert (
        "test-article.md" in content_disposition
        or "test-artifact.md" in content_disposition
        or "analysis-" in content_disposition
    )
    assert "# Test Artifact" in response.text

    # Verify download_count incremented (endpoint uses separate session, need to refresh)
    # The endpoint commits in its own session, so we need to expire and refresh
    result = await db_session.execute(select(Artifact).where(Artifact.id == artifact_id))
    updated_artifact = result.scalar_one_or_none()
    assert updated_artifact is not None
    # Expire the object to force a fresh query
    db_session.expire(updated_artifact)
    await db_session.refresh(updated_artifact)
    # Should be 1 (0 initial + 1 from download)
    assert updated_artifact.download_count == 1, (
        f"Expected download_count to be 1, got {updated_artifact.download_count}"
    )


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
    analysis = await create_complete_analysis(
        db_session,
        id=analysis_id,
    )
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

    # Get initial count before download
    initial_count = artifact.download_count
    assert initial_count == 5, f"Expected initial count to be 5, got {initial_count}"

    # Download artifact (this happens in a separate request/transaction)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/artifacts/{artifact_id}/download")

    assert response.status_code == status.HTTP_200_OK

    # The endpoint uses its own db session and commits, so we need to expire
    # the current object and re-query to see the updated value
    db_session.expire(artifact)
    await db_session.refresh(artifact)

    # Should be 6 (5 initial + 1 from download)
    assert artifact.download_count == initial_count + 1, (
        f"Expected download_count to be {initial_count + 1}, got {artifact.download_count}"
    )


@pytest.mark.asyncio
async def test_get_artifact_by_analysis_returns_latest(
    requires_database, reset_engine_connections, db_session
):
    """GET /api/v1/analyze/{id}/artifact returns latest artifact metadata."""
    analysis_id = uuid.uuid4()
    analysis = await create_complete_analysis(
        db_session,
        id=analysis_id,
    )
    await db_session.commit()

    older_artifact = Artifact(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        markdown_content="# Old",
        version=1,
        created_at=datetime.now(UTC) - timedelta(minutes=5),
    )
    newer_artifact = Artifact(
        id=uuid.uuid4(),
        analysis_id=analysis_id,
        markdown_content="# New",
        version=2,
        created_at=datetime.now(UTC),
    )
    db_session.add_all([older_artifact, newer_artifact])
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/analyze/{analysis_id}/artifact")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["artifact_id"] == str(newer_artifact.id)
    assert data["markdown_content"].startswith("# New")


@pytest.mark.asyncio
async def test_get_artifact_by_analysis_not_found(reset_engine_connections):
    """GET /api/v1/analyze/{id}/artifact returns 404 when missing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/v1/analyze/{uuid.uuid4()}/artifact")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "No artifact" in response.json()["detail"]


@pytest.mark.asyncio
async def test_full_workflow_generates_artifact(
    requires_database, reset_engine_connections, db_session
):
    """Test that full workflow generates artifact (mocked workflow execution)."""
    # This test verifies the artifact is created when workflow completes
    # In a real scenario, this would run the full workflow
    # For now, we'll test that the artifact can be created and retrieved

    analysis_id = uuid.uuid4()
    analysis = await create_complete_analysis(
        db_session,
        id=analysis_id,
        title="Full Workflow Test",
        extraction_metadata={"title": "Full Workflow Test"},
    )
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
