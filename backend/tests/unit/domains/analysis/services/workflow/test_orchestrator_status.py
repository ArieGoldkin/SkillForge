"""Unit tests for WorkflowOrchestrator status updates with granular statuses."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.schemas.api import AnalysisStatus
from app.domains.analysis.services.workflow import WorkflowOrchestrator


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.fixture
def test_url():
    """Create a test URL."""
    return "https://example.com/article"


@patch("app.core.tracing.get_current_trace_id")
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.persistence.data_persister.DataPersister.persist")
@patch("app.domains.analysis.services.persistence.status_updater.StatusUpdater.update")
@patch("app.db.repositories.artifact_repository.ArtifactRepository")
@patch("app.db.session.AsyncSessionLocal")
async def test_orchestrator_sets_artifact_failed_when_no_artifact(
    mock_session_local,
    mock_repo_class,
    mock_update_status,
    mock_persist,
    mock_workflow,
    mock_get_trace_id,
    mock_analysis_id,
    test_url,
):
    """Test workflow sets status to artifact_failed when artifact is missing."""
    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

    # Mock persistence to succeed
    mock_persist = AsyncMock(return_value=True)

    # Mock artifact repository to return None (no artifact)
    mock_repo_instance = AsyncMock()
    mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=None)
    mock_repo_class.return_value = mock_repo_instance

    # Mock database session
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_local.return_value = mock_session

    # Mock trace_id
    mock_get_trace_id.return_value = "test-trace-id"

    # Run workflow
    orchestrator = WorkflowOrchestrator()
    await orchestrator.run(mock_analysis_id, test_url)

    # Verify status was set to artifact_failed (not generic failed)
    mock_update_status.assert_called()
    calls = mock_update_status.call_args_list

    # Find the call that sets artifact_failed
    artifact_failed_call = None
    for call in calls:
        if len(call[0]) >= 2 and call[0][1] == AnalysisStatus.ARTIFACT_FAILED.value:
            artifact_failed_call = call
            break

    assert artifact_failed_call is not None, "Expected status to be set to artifact_failed"
    assert artifact_failed_call[0][0] == mock_analysis_id
    assert artifact_failed_call[0][1] == AnalysisStatus.ARTIFACT_FAILED.value


@patch("app.core.tracing.get_current_trace_id")
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.persistence.data_persister.DataPersister.persist")
@patch("app.domains.analysis.services.persistence.status_updater.StatusUpdater.update")
@patch("app.db.repositories.artifact_repository.ArtifactRepository")
@patch("app.db.session.AsyncSessionLocal")
async def test_orchestrator_sets_complete_when_artifact_exists(
    mock_session_local,
    mock_repo_class,
    mock_update_status,
    mock_persist,
    mock_workflow,
    mock_get_trace_id,
    mock_analysis_id,
    test_url,
):
    """Test workflow sets status to complete when artifact exists."""
    from app.db.models.artifact import Artifact

    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

    # Mock persistence to succeed
    mock_persist = AsyncMock(return_value=True)

    # Mock artifact repository to return artifact
    mock_artifact = MagicMock(spec=Artifact)
    mock_artifact.id = uuid.uuid4()
    mock_repo_instance = AsyncMock()
    mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)
    mock_repo_class.return_value = mock_repo_instance

    # Mock database session
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session_local.return_value = mock_session

    # Mock trace_id
    mock_get_trace_id.return_value = "test-trace-id"

    # Run workflow
    orchestrator = WorkflowOrchestrator()
    await orchestrator.run(mock_analysis_id, test_url)

    # Verify status was set to complete
    mock_update_status.assert_called()
    calls = mock_update_status.call_args_list

    # Find the call that sets complete
    complete_call = None
    for call in calls:
        if len(call[0]) >= 2 and call[0][1] == AnalysisStatus.COMPLETE.value:
            complete_call = call
            break

    assert complete_call is not None, "Expected status to be set to complete"
    assert complete_call[0][0] == mock_analysis_id
    assert complete_call[0][1] == AnalysisStatus.COMPLETE.value


@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.persistence.status_updater.StatusUpdater.update")
async def test_orchestrator_sets_analysis_failed_when_result_incomplete(
    mock_update_status,
    mock_workflow,
    mock_analysis_id,
    test_url,
):
    """Test workflow sets status to analysis_failed when result is incomplete."""
    # Mock workflow to return incomplete result (missing required fields)
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            # Missing extraction_metadata and content_embedding
        }
    )

    # Run workflow
    orchestrator = WorkflowOrchestrator()
    await orchestrator.run(mock_analysis_id, test_url)

    # Verify status was set to analysis_failed
    mock_update_status.assert_called()
    calls = mock_update_status.call_args_list

    # Find the call that sets analysis_failed
    analysis_failed_call = None
    for call in calls:
        if len(call[0]) >= 2 and call[0][1] == AnalysisStatus.ANALYSIS_FAILED.value:
            analysis_failed_call = call
            break

    assert analysis_failed_call is not None, "Expected status to be set to analysis_failed"
    assert analysis_failed_call[0][0] == mock_analysis_id
    assert analysis_failed_call[0][1] == AnalysisStatus.ANALYSIS_FAILED.value

