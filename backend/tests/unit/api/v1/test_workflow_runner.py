"""Unit tests for workflow runner background task."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.workflow_runner import run_workflow_task


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.fixture
def test_url():
    """Create a test URL."""
    return "https://example.com/article"


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_success(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test successful workflow execution."""
    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(return_value={})

    # Mock database session and status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_db_session_analysis = AsyncMock()
    mock_result_analysis = MagicMock()
    mock_result_analysis.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_analysis.execute.return_value = mock_result_analysis
    mock_db_session_analysis.__aenter__ = AsyncMock(return_value=mock_db_session_analysis)
    mock_db_session_analysis.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for artifact query (second AsyncSessionLocal call)
    mock_db_session_artifact = AsyncMock()
    mock_db_session_artifact.__aenter__ = AsyncMock(return_value=mock_db_session_artifact)
    mock_db_session_artifact.__aexit__ = AsyncMock(return_value=False)

    # Mock repository - return None (artifact not found) for this test
    mock_repository = AsyncMock()
    mock_repository.get_artifact_by_analysis_id = AsyncMock(return_value=None)

    # Track session calls to return different sessions
    session_calls = [mock_db_session_analysis, mock_db_session_artifact]

    def session_factory():
        return session_calls.pop(0) if session_calls else mock_db_session_artifact

    # Patch AsyncSessionLocal at the source (app.db.session)
    # AsyncSessionLocal is a callable, so we make it return our mock session when called
    with (
        patch("app.db.session.AsyncSessionLocal", side_effect=session_factory),
        patch(
            "app.db.repositories.artifact_repository.ArtifactRepository",
            return_value=mock_repository,
        ),
    ):
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow was called
    mock_workflow.ainvoke.assert_called_once()
    call_args = mock_workflow.ainvoke.call_args
    assert call_args[0][0]["url"] == test_url
    assert call_args[0][0]["analysis_id"] == str(mock_analysis_id)

    # Verify status was updated to complete
    assert mock_analysis.status == "complete"
    mock_db_session_analysis.commit.assert_called_once()

    # Verify complete event was emitted (initial "workflow" event removed per schema)
    complete_calls = [call for call in mock_emit_event.call_args_list if call[0][0] == "complete"]
    assert len(complete_calls) >= 1, "Complete event should be emitted"


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_workflow_error(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution with workflow error."""
    # Mock workflow to raise an error
    mock_workflow.ainvoke = AsyncMock(side_effect=RuntimeError("Workflow failed"))

    # Mock database session for error status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # Patch AsyncSessionLocal at the source (app.db.session)
    # AsyncSessionLocal is a callable, so we make it return our mock session when called
    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        # The exception handler updates status and emits error event, then re-raises
        # This is correct behavior - exceptions should propagate after handling
        with pytest.raises(RuntimeError, match="Workflow failed"):
            await run_workflow_task(mock_analysis_id, test_url)

    # Verify status was updated to failed (happens before re-raising)
    assert mock_analysis.status == "failed"
    mock_db_session.commit.assert_called_once()

    # Verify error event was emitted
    error_calls = [call for call in mock_emit_event.call_args_list if call[0][0] == "error"]
    assert len(error_calls) == 1


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_status_update_fails(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution when status update fails."""
    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(return_value={})

    # Mock database session to fail on status update
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        # Should not raise - status update failure is logged but doesn't fail workflow
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify error was logged but workflow continued
    error_logs = [
        call
        for call in mock_logger.error.call_args_list
        if "workflow_task_status_update_failed" in str(call)
    ]
    assert len(error_logs) == 1


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_analysis_not_found(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution when analysis record not found for status update."""
    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(return_value={})

    # Mock database session to return None (analysis not found)
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        # Should not raise - missing analysis is handled gracefully
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify commit was not called (no analysis to update)
    mock_db_session.commit.assert_not_called()


@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
async def test_run_workflow_task_emits_complete_event_with_artifact_id(
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test workflow emits proper complete event with artifact_id per SSE_SCHEMA.md."""
    import uuid

    from app.models.artifact import Artifact

    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(return_value={})

    # Mock analysis for status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_analysis.id = mock_analysis_id

    # Mock artifact for complete event
    artifact_id = uuid.uuid4()
    mock_artifact = MagicMock(spec=Artifact)
    mock_artifact.id = artifact_id

    # Mock database session for analysis status update
    mock_db_session_analysis = AsyncMock()
    mock_result_analysis = MagicMock()
    mock_result_analysis.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_analysis.execute.return_value = mock_result_analysis
    mock_db_session_analysis.__aenter__ = AsyncMock(return_value=mock_db_session_analysis)
    mock_db_session_analysis.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for artifact query (second AsyncSessionLocal call)
    mock_db_session_artifact = AsyncMock()
    mock_db_session_artifact.__aenter__ = AsyncMock(return_value=mock_db_session_artifact)
    mock_db_session_artifact.__aexit__ = AsyncMock(return_value=False)

    # Mock repository instance
    mock_repository_instance = AsyncMock()
    mock_repository_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    # Track session calls to return different sessions
    session_calls = [mock_db_session_analysis, mock_db_session_artifact]

    def session_factory():
        return session_calls.pop(0) if session_calls else mock_db_session_artifact

    # Patch ArtifactRepository at the import location (inside the function)
    with (
        patch("app.db.session.AsyncSessionLocal", side_effect=session_factory),
        patch(
            "app.db.repositories.artifact_repository.ArtifactRepository",
        ) as mock_repo_class,
    ):
        # Make the class constructor return our mock instance
        mock_repo_class.return_value = mock_repository_instance
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow was called
    mock_workflow.ainvoke.assert_called_once()

    # Verify complete event was emitted with correct format
    # Check all calls to debug
    all_calls = list(mock_emit_event.call_args_list)
    complete_calls = [
        call for call in all_calls if len(call.args) > 0 and call.args[0] == "complete"
    ]

    if not complete_calls:
        # Debug: print all calls
        print(f"All calls: {[(c.args, c.kwargs) for c in all_calls]}")
        assert False, (
            f"No complete event found. All calls: {[(c.args, c.kwargs) for c in all_calls]}"
        )

    assert len(complete_calls) == 1, (
        f"Complete event should be emitted exactly once, got {len(complete_calls)} calls"
    )

    complete_call = complete_calls[0]
    call_args = complete_call.args  # positional args (event_type, analysis_id, stage, status)
    call_kwargs = complete_call.kwargs  # kwargs

    # Verify event type (first positional arg: event_type)
    assert call_args[0] == "complete", f"Event type should be 'complete', got {call_args[0]}"
    # Verify stage (third positional arg: stage) - check if passed as positional or kwarg
    stage_value = call_args[2] if len(call_args) > 2 else call_kwargs.get("stage")
    assert stage_value == "artifact_generation", (
        f"Stage should be 'artifact_generation', got {stage_value} "
        f"in args={call_args}, kwargs={call_kwargs}"
    )
    # Verify status (fourth positional arg: status) - check if passed as positional or kwarg
    status_value = call_args[3] if len(call_args) > 3 else call_kwargs.get("status")
    assert status_value == "complete", (
        f"Status should be 'complete', got {status_value} in args={call_args}, kwargs={call_kwargs}"
    )
    # Verify artifact_id is included in kwargs
    assert "artifact_id" in call_kwargs, f"artifact_id should be in event kwargs, got {call_kwargs}"
    assert call_kwargs["artifact_id"] == str(artifact_id), (
        f"artifact_id should match artifact.id, got {call_kwargs.get('artifact_id')}"
    )
