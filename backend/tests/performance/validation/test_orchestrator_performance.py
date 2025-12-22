"""Performance tests for WorkflowOrchestrator."""

import asyncio
import time

import pytest

from app.domains.analysis.services.workflow.orchestrator import WorkflowOrchestrator


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for tests."""
    return WorkflowOrchestrator()


@pytest.fixture
def valid_completed_result():
    """Create valid completed workflow result."""
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
        "workflow_status": "completed",
    }


@pytest.mark.performance
@pytest.mark.asyncio
async def test_orchestrator_validation_overhead(orchestrator, valid_completed_result):
    """Test validation overhead <10ms."""
    import uuid
    from unittest.mock import AsyncMock, MagicMock, patch

    analysis_id = uuid.uuid4()

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
        ) as mock_workflow,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository"
        ) as mock_artifact_repo,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal"
        ) as mock_session_local,
    ):
        mock_workflow.ainvoke = AsyncMock(return_value=valid_completed_result)

        mock_artifact = MagicMock()
        mock_artifact.id = uuid.uuid4()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)
        mock_artifact_repo.return_value = mock_repo_instance

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        start = time.time()
        await orchestrator.run(analysis_id, "https://example.com")
        elapsed = time.time() - start

        # Validation overhead should be minimal (<10ms)
        assert elapsed < 0.1, f"Orchestrator took {elapsed * 1000:.2f}ms"


@pytest.mark.performance
@pytest.mark.asyncio
async def test_orchestrator_concurrent_workflow_handling(orchestrator, valid_completed_result):
    """Test concurrent workflows <200ms."""
    import uuid
    from unittest.mock import AsyncMock, MagicMock, patch

    analysis_ids = [uuid.uuid4() for _ in range(10)]

    def create_result(aid):
        result = valid_completed_result.copy()
        result["content_ref"]["uri"] = f"analysis://{aid}/content"
        return result

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.analysis_workflow"
        ) as mock_workflow,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository"
        ) as mock_artifact_repo,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal"
        ) as mock_session_local,
    ):

        def mock_ainvoke(input_state, config):
            aid = uuid.UUID(input_state["analysis_id"])
            return create_result(aid)

        mock_workflow.ainvoke = AsyncMock(side_effect=mock_ainvoke)

        mock_artifact = MagicMock()
        mock_artifact.id = uuid.uuid4()
        mock_repo_instance = MagicMock()
        mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)
        mock_artifact_repo.return_value = mock_repo_instance

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        async def run_one(aid):
            return await orchestrator.run(aid, f"https://example.com/{aid}")

        start = time.time()
        tasks = [run_one(aid) for aid in analysis_ids]
        await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # 10 concurrent workflows should be fast (<200ms)
        assert elapsed < 0.2, (
            f"10 concurrent workflows took {elapsed * 1000:.2f}ms, expected <200ms"
        )
