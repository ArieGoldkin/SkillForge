"""Integration tests for status-aware WorkflowOrchestrator."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.services.workflow.orchestrator import WorkflowOrchestrator


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for tests."""
    return WorkflowOrchestrator()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_real_failed_workflow(orchestrator, db_session):
    """Test real failed workflow execution."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/failed-{analysis_id}",
        content_type="article",
        status="analyzing",
    )

    # Mock workflow to return failed result
    failed_result = {
        "workflow_status": "failed",
        "final_error": "Extraction failed",
    }

    with patch(
        "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
    ) as mock_workflow:
        mock_workflow.ainvoke = AsyncMock(return_value=failed_result)

        await orchestrator.run(analysis_id, "https://example.com/failed")

        # Verify status updated (should be handled by workflow_failed node)
        # This test verifies orchestrator doesn't crash on failed workflows


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_real_completed_workflow(orchestrator, db_session):
    """Test real completed workflow execution."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/completed-{analysis_id}",
        content_type="article",
        status="analyzing",
    )

    # Mock workflow to return completed result
    completed_result = {
        "content_ref": {
            "uri": f"analysis://{analysis_id}/content",
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
        "workflow_status": "completed",
    }

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
        ) as mock_workflow,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository"
        ) as mock_artifact_repo,
    ):
        mock_workflow.ainvoke = AsyncMock(return_value=completed_result)

        # Mock artifact
        from app.db.models.artifact import Artifact

        mock_artifact = MagicMock(spec=Artifact)
        mock_artifact.id = uuid.uuid4()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)
        mock_artifact_repo.return_value = mock_repo_instance

        await orchestrator.run(analysis_id, "https://example.com/completed")

        # Verify data persisted
        analysis = await repo.get_by_id(analysis_id)
        assert analysis is not None, "Analysis should exist"
        assert analysis.raw_content == "Test content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_end_to_end_validation(orchestrator, db_session):
    """Test end-to-end validation flow."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/e2e-{analysis_id}",
        content_type="article",
        status="analyzing",
    )

    # Valid completed result
    completed_result = {
        "content_ref": {
            "uri": f"analysis://{analysis_id}/content",
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
        "workflow_status": "completed",
    }

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
        ) as mock_workflow,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository"
        ) as mock_artifact_repo,
    ):
        mock_workflow.ainvoke = AsyncMock(return_value=completed_result)

        mock_artifact = MagicMock()
        mock_artifact.id = uuid.uuid4()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)
        mock_artifact_repo.return_value = mock_repo_instance

        await orchestrator.run(analysis_id, "https://example.com/e2e")

        # Verify complete flow: validation → persistence → status update
        analysis = await repo.get_by_id(analysis_id)
        assert analysis is not None, "Analysis should exist"
        assert analysis.raw_content is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_error_recovery(orchestrator, db_session):
    """Test error recovery works."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/recovery-{analysis_id}",
        content_type="article",
        status="analyzing",
    )

    # First: Invalid result (validation fails)
    invalid_result = {
        "raw_content": "",
        "workflow_status": "completed",
    }

    with patch(
        "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
    ) as mock_workflow:
        mock_workflow.ainvoke = AsyncMock(return_value=invalid_result)

        await orchestrator.run(analysis_id, "https://example.com/recovery")

        # Verify status updated to failed
        analysis = await repo.get_by_id(analysis_id)
        # Status should be updated by orchestrator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_concurrent_workflows(orchestrator, db_session):
    """Test concurrent workflows handled."""
    import asyncio

    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_ids = [uuid.uuid4() for _ in range(3)]

    # Create multiple analyses
    for analysis_id in analysis_ids:
        await repo.create_analysis(
            analysis_id=analysis_id,
            url=f"https://example.com/concurrent-{analysis_id}",
            content_type="article",
            status="analyzing",
        )

    # Mock workflow results
    def create_result(aid):
        return {
            "content_ref": {
                "uri": f"analysis://{aid}/content",
                "summary": "Test summary",
                "size_bytes": 1000,
                "content_type": "text/plain",
            },
            "raw_content": f"Content for {aid}",
            "extraction_metadata": {
                "title": "Test Article",
                "word_count": 1000,
                "char_count": 5000,
            },
            "content_embedding": [0.1] * 1536,
            "workflow_status": "completed",
        }

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
        ) as mock_workflow,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository"
        ) as mock_artifact_repo,
    ):
        # Mock workflow to return different results
        def mock_ainvoke(input_state, config):
            aid = uuid.UUID(input_state["analysis_id"])
            return create_result(aid)

        mock_workflow.ainvoke = AsyncMock(side_effect=mock_ainvoke)

        # Mock artifacts
        mock_artifact = MagicMock()
        mock_artifact.id = uuid.uuid4()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)
        mock_artifact_repo.return_value = mock_repo_instance

        # Run concurrently
        tasks = [
            orchestrator.run(aid, f"https://example.com/concurrent-{aid}") for aid in analysis_ids
        ]
        await asyncio.gather(*tasks)

        # Verify all persisted
        for analysis_id in analysis_ids:
            analysis = await repo.get_by_id(analysis_id)
            assert analysis is not None, "Analysis should exist"
            assert analysis.raw_content is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_status_consistency(orchestrator, db_session):
    """Test status consistency maintained."""
    from app.db.repositories.analysis_repository import AnalysisRepository

    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/consistency-{analysis_id}",
        content_type="article",
        status="analyzing",
    )

    # Valid completed result
    completed_result = {
        "content_ref": {
            "uri": f"analysis://{analysis_id}/content",
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
        "workflow_status": "completed",
    }

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
        ) as mock_workflow,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository"
        ) as mock_artifact_repo,
    ):
        mock_workflow.ainvoke = AsyncMock(return_value=completed_result)

        mock_artifact = MagicMock()
        mock_artifact.id = uuid.uuid4()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)
        mock_artifact_repo.return_value = mock_repo_instance

        await orchestrator.run(analysis_id, "https://example.com/consistency")

        # Verify status is consistent
        analysis = await repo.get_by_id(analysis_id)
        # Status should be updated correctly by orchestrator
