"""Unit tests for WorkflowOrchestrator."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.services.workflow import WorkflowOrchestrator


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.fixture
def test_url():
    """Create a test URL."""
    return "https://example.com/article"


@patch("app.shared.services.persistence.progress.persist_progress_event_async")
@patch("app.shared.services.messaging.sse_helpers.get_broadcaster", new_callable=AsyncMock)
@patch("app.core.tracing.get_current_trace_id")
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.workflow.orchestrator.logger")
async def test_orchestrator_run_success(
    mock_logger,
    mock_workflow,
    mock_get_trace_id,
    mock_get_broadcaster,
    mock_persist_progress,
    mock_analysis_id,
    test_url,
):
    """Test successful workflow execution."""
    import uuid

    from app.db.models.artifact import Artifact

    # Mock broadcaster factory (async function)
    # Note: return_value is set in the patch decorator, but we need to access the mock
    # to configure the broadcaster's publish method
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()
    # The mock_get_broadcaster is already configured in the decorator to return mock_broadcaster
    # But we need to ensure it's set up correctly - let's reconfigure it
    mock_get_broadcaster.return_value = mock_broadcaster

    # Mock trace_id retrieval (Issue #385)
    mock_get_trace_id.return_value = "test-trace-id-123"

    # Mock workflow to complete successfully with data to persist
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

    # Mock analysis for status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_analysis.id = mock_analysis_id

    # Mock artifact for validation and completion event
    artifact_id = uuid.uuid4()
    mock_artifact = MagicMock(spec=Artifact)
    mock_artifact.id = artifact_id

    # Mock database session for _persist_analysis_data (first call - Issue #168)
    mock_db_session_persist = AsyncMock()
    mock_result_persist = MagicMock()
    mock_result_persist.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_persist.execute.return_value = mock_result_persist
    mock_db_session_persist.__aenter__ = AsyncMock(return_value=mock_db_session_persist)
    mock_db_session_persist.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for artifact validation (second call)
    mock_db_session_artifact_validation = AsyncMock()
    mock_db_session_artifact_validation.__aenter__ = AsyncMock(
        return_value=mock_db_session_artifact_validation
    )
    mock_db_session_artifact_validation.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for status update in _update_analysis_status (third call)
    mock_db_session_status = AsyncMock()
    mock_result_status = MagicMock()
    mock_result_status.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_status.execute.return_value = mock_result_status
    mock_db_session_status.__aenter__ = AsyncMock(return_value=mock_db_session_status)
    mock_db_session_status.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for artifact query in completion event (fourth call)
    mock_db_session_artifact_event = AsyncMock()
    mock_result_artifact_event = MagicMock()
    # The repository.get_artifact_by_analysis_id needs to return the artifact
    # This is handled by the mock_repository_instance, but we need the session to work
    mock_db_session_artifact_event.__aenter__ = AsyncMock(
        return_value=mock_db_session_artifact_event
    )
    mock_db_session_artifact_event.__aexit__ = AsyncMock(return_value=False)

    # Mock repository instance - return artifact
    mock_repository_instance = AsyncMock()
    mock_repository_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    # Track session calls to return different sessions
    # Order: persist data, artifact validation, status update, artifact for event
    session_calls = [
        mock_db_session_persist,
        mock_db_session_artifact_validation,
        mock_db_session_status,
        mock_db_session_artifact_event,
    ]

    def session_factory():
        return session_calls.pop(0) if session_calls else mock_db_session_artifact_event

    # Patch AsyncSessionLocal at the import location in orchestrator
    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repository_instance,
        ),
    ):
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(mock_analysis_id, test_url)

    # Verify workflow was called
    mock_workflow.ainvoke.assert_called_once()
    call_args = mock_workflow.ainvoke.call_args
    assert call_args[0][0]["url"] == test_url
    assert call_args[0][0]["analysis_id"] == str(mock_analysis_id)

    # Verify status was updated to complete
    assert mock_analysis.status == "complete"
    mock_db_session_status.commit.assert_called_once()

    # Verify complete event was emitted with artifact_id and trace_id
    # First check if get_broadcaster was called (it should be)
    assert mock_get_broadcaster.called, "get_broadcaster should have been called"
    
    # Check if there were any errors logged (event emission might have failed silently)
    error_logs = [
        call for call in mock_logger.error.call_args_list
        if "workflow_complete_event_failed" in str(call)
    ]
    if error_logs:
        # Event emission failed - this is a problem with the mock setup
        error_call = error_logs[0]
        print(f"Event emission failed with error: {error_call}")
        raise AssertionError(f"Event emission failed: {error_call}")
    
    # Verify broadcaster.publish was called
    mock_broadcaster.publish.assert_called()
    publish_calls = mock_broadcaster.publish.call_args_list
    complete_calls = [
        call for call in publish_calls if len(call[0]) > 1 and isinstance(call[0][1], dict) and call[0][1].get("type") == "complete"
    ]
    assert len(complete_calls) >= 1, f"Complete event should be emitted, got {len(complete_calls)} calls. All publish calls: {publish_calls}"
    complete_call = complete_calls[0]
    event_data = complete_call[0][1]
    assert "artifact_id" in event_data
    assert event_data["artifact_id"] == str(artifact_id)
    assert "trace_id" in event_data  # Issue #385


@patch("app.shared.services.persistence.progress.persist_progress_event_async")
@patch("app.shared.services.messaging.sse_helpers.get_broadcaster", new_callable=AsyncMock)
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.workflow.orchestrator.logger")
async def test_orchestrator_run_workflow_error(
    mock_logger,
    mock_workflow,
    mock_get_broadcaster,
    mock_persist_progress,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution with workflow error."""
    # Mock broadcaster factory (async function)
    # Create broadcaster mock before setting return_value
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()
    # Configure the async mock to return the broadcaster when awaited
    # For AsyncMock, return_value works for awaited calls
    mock_get_broadcaster.return_value = mock_broadcaster
    # Also ensure the mock is callable and returns the broadcaster
    mock_get_broadcaster.side_effect = None  # Clear any side_effect

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

    # Patch AsyncSessionLocal at the import location in orchestrator
    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal",
            return_value=mock_db_session,
        ),
        patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            return_value=mock_db_session,
        ),
    ):
        # The exception handler updates status and emits error event, then re-raises
        # This is correct behavior - exceptions should propagate after handling
        orchestrator = WorkflowOrchestrator()
        with pytest.raises(RuntimeError, match="Workflow failed"):
            await orchestrator.run(mock_analysis_id, test_url)

    # Verify status was updated to failed (happens before re-raising)
    assert mock_analysis.status == "failed"
    mock_db_session.commit.assert_called_once()

    # Verify error event was emitted
    mock_broadcaster.publish.assert_called()
    publish_calls = mock_broadcaster.publish.call_args_list
    error_calls = [
        call for call in publish_calls if len(call[0]) > 1 and call[0][1].get("type") == "error"
    ]
    assert len(error_calls) == 1


@patch("app.shared.services.persistence.progress.persist_progress_event_async")
@patch("app.shared.services.messaging.sse_helpers.get_broadcaster", new_callable=AsyncMock)
@patch("app.domains.analysis.services.persistence.status_updater.logger")
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.workflow.orchestrator.logger")
async def test_orchestrator_run_status_update_fails(
    mock_orchestrator_logger,
    mock_workflow,
    mock_status_updater_logger,
    mock_get_broadcaster,
    mock_persist_progress,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution when status update fails."""
    import uuid

    from app.db.models.artifact import Artifact

    # Mock broadcaster factory
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()
    mock_get_broadcaster.return_value = mock_broadcaster

    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

    # Mock artifact for validation
    artifact_id = uuid.uuid4()
    mock_artifact = MagicMock(spec=Artifact)
    mock_artifact.id = artifact_id

    # Mock database session for persistence (first call - succeeds)
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_analysis.id = mock_analysis_id

    mock_db_session_persist = AsyncMock()
    mock_result_persist = MagicMock()
    mock_result_persist.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_persist.execute.return_value = mock_result_persist
    mock_db_session_persist.__aenter__ = AsyncMock(return_value=mock_db_session_persist)
    mock_db_session_persist.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for artifact validation (second call - succeeds)
    mock_db_session_artifact_validation = AsyncMock()
    mock_db_session_artifact_validation.__aenter__ = AsyncMock(
        return_value=mock_db_session_artifact_validation
    )
    mock_db_session_artifact_validation.__aexit__ = AsyncMock(return_value=False)

    # Mock database session to fail on status update (third call - fails)
    mock_db_session_status = AsyncMock()
    mock_db_session_status.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session_status.__aenter__ = AsyncMock(return_value=mock_db_session_status)
    mock_db_session_status.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for artifact query in completion event (fourth call - succeeds)
    mock_db_session_artifact_event = AsyncMock()
    mock_db_session_artifact_event.__aenter__ = AsyncMock(
        return_value=mock_db_session_artifact_event
    )
    mock_db_session_artifact_event.__aexit__ = AsyncMock(return_value=False)

    # Mock repository instance - return artifact
    mock_repository_instance = AsyncMock()
    mock_repository_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    # Track session calls to return different sessions
    # Order: persist, artifact validation, status update (fails), artifact for event
    session_calls = [
        mock_db_session_persist,
        mock_db_session_artifact_validation,
        mock_db_session_status,
        mock_db_session_artifact_event,
    ]

    def session_factory():
        return session_calls.pop(0) if session_calls else mock_db_session_artifact_event

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repository_instance,
        ),
    ):
        # Should not raise - status update failure is logged but doesn't fail workflow
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify error was logged but workflow continued
    # The error is logged by StatusUpdater, not the orchestrator logger
    error_logs = [
        call
        for call in mock_status_updater_logger.error.call_args_list
        if "workflow_task_status_update_failed" in str(call)
    ]
    assert len(error_logs) == 1, "Status update failure should be logged"


@patch("app.shared.services.persistence.progress.persist_progress_event_async")
@patch("app.shared.services.messaging.sse_helpers.get_broadcaster", new_callable=AsyncMock)
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.workflow.orchestrator.logger")
async def test_orchestrator_run_analysis_not_found(
    mock_logger,
    mock_workflow,
    mock_get_broadcaster,
    mock_persist_progress,
    mock_analysis_id,
    test_url,
):
    """Test workflow execution when analysis record not found for status update."""
    # Mock broadcaster factory (async function)
    # Create broadcaster mock before setting return_value
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()
    # Configure the async mock to return the broadcaster when awaited
    # For AsyncMock, return_value works for awaited calls
    mock_get_broadcaster.return_value = mock_broadcaster
    # Also ensure the mock is callable and returns the broadcaster
    mock_get_broadcaster.side_effect = None  # Clear any side_effect

    # Mock workflow to complete successfully with required fields
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

    # Mock database session to return None (analysis not found)
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal",
            return_value=mock_db_session,
        ),
        patch(
            "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
            return_value=mock_db_session,
        ),
        patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            return_value=mock_db_session,
        ),
    ):
        # Should not raise - missing analysis is handled gracefully
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify commit was not called (no analysis to update)
    mock_db_session.commit.assert_not_called()


@patch("app.shared.services.persistence.progress.persist_progress_event_async")
@patch("app.shared.services.messaging.sse_helpers.get_broadcaster", new_callable=AsyncMock)
@patch("app.core.tracing.get_current_trace_id")
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.workflow.orchestrator.logger")
async def test_orchestrator_run_emits_complete_event_with_artifact_id(
    mock_logger,
    mock_workflow,
    mock_get_trace_id,
    mock_get_broadcaster,
    mock_persist_progress,
    mock_analysis_id,
    test_url,
):
    """Test workflow emits proper complete event with artifact_id per SSE_SCHEMA.md."""
    import uuid

    from app.db.models.artifact import Artifact

    # Mock broadcaster factory (async function)
    # Create broadcaster mock before setting return_value
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()
    # Configure the async mock to return the broadcaster when awaited
    # For AsyncMock, return_value works for awaited calls
    mock_get_broadcaster.return_value = mock_broadcaster
    # Also ensure the mock is callable and returns the broadcaster
    mock_get_broadcaster.side_effect = None  # Clear any side_effect

    # Mock trace_id retrieval (Issue #385)
    mock_get_trace_id.return_value = "test-trace-id-456"

    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

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
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
        ) as mock_repo_class,
    ):
        # Make the class constructor return our mock instance
        mock_repo_class.return_value = mock_repository_instance
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(mock_analysis_id, test_url)

    # Verify workflow was called
    mock_workflow.ainvoke.assert_called_once()

    # Verify complete event was emitted with correct format
    mock_broadcaster.publish.assert_called()
    publish_calls = mock_broadcaster.publish.call_args_list
    complete_calls = [
        call for call in publish_calls if len(call[0]) > 1 and call[0][1].get("type") == "complete"
    ]

    if not complete_calls:
        # Debug: print all calls
        print(f"All calls: {[(c[0], c[1] if len(c) > 1 else {}) for c in publish_calls]}")
        msg = f"No complete event found. All calls: {[(c[0], c[1] if len(c) > 1 else {}) for c in publish_calls]}"
        raise AssertionError(msg)

    assert len(complete_calls) == 1, (
        f"Complete event should be emitted exactly once, got {len(complete_calls)} calls"
    )

    complete_call = complete_calls[0]
    event_data = complete_call[0][1]  # event_data is the second arg to publish()

    # Verify event type
    assert event_data["type"] == "complete", (
        f"Event type should be 'complete', got {event_data.get('type')}"
    )
    # Verify stage
    assert event_data["stage"] == "artifact_generation", (
        f"Stage should be 'artifact_generation', got {event_data.get('stage')}"
    )
    # Verify status
    assert event_data["status"] == "complete", (
        f"Status should be 'complete', got {event_data.get('status')}"
    )
    # Verify artifact_id is included
    assert "artifact_id" in event_data, f"artifact_id should be in event data, got {event_data}"
    assert event_data["artifact_id"] == str(artifact_id), (
        f"artifact_id should match artifact.id, got {event_data.get('artifact_id')}"
    )
    # Verify trace_id is included (Issue #385)
    assert "trace_id" in event_data, f"trace_id should be in event data, got {event_data}"


@pytest.mark.asyncio
@patch("app.shared.services.persistence.progress.persist_progress_event_async")
@patch("app.shared.services.messaging.sse_helpers.get_broadcaster", new_callable=AsyncMock)
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.workflow.orchestrator.logger")
@patch("app.domains.analysis.services.persistence.status_updater.StatusUpdater.update")
@patch("app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error")
async def test_orchestrator_run_fails_without_artifact(
    mock_emit_error,
    mock_update_status,
    mock_logger,
    mock_workflow,
    mock_get_broadcaster,
    mock_persist_progress,
    mock_analysis_id,
    test_url,
):
    """Test that workflow fails when artifact is missing (artifact validation fix).

    This test verifies the fix where analysis is not marked complete if
    artifact generation failed or was skipped.
    """
    # Mock broadcaster factory (async function)
    # Create broadcaster mock before setting return_value
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()
    # Configure the async mock to return the broadcaster when awaited
    # For AsyncMock, return_value works for awaited calls
    mock_get_broadcaster.return_value = mock_broadcaster
    # Also ensure the mock is callable and returns the broadcaster
    mock_get_broadcaster.side_effect = None  # Clear any side_effect

    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

    # Mock analysis for status update
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_analysis.id = mock_analysis_id

    # Mock database session for persistence
    mock_db_session_persist = AsyncMock()
    mock_result_persist = MagicMock()
    mock_result_persist.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_persist.execute.return_value = mock_result_persist
    mock_db_session_persist.__aenter__ = AsyncMock(return_value=mock_db_session_persist)
    mock_db_session_persist.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for analysis status update
    mock_db_session_analysis = AsyncMock()
    mock_result_analysis = MagicMock()
    mock_result_analysis.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_analysis.execute.return_value = mock_result_analysis
    mock_db_session_analysis.__aenter__ = AsyncMock(return_value=mock_db_session_analysis)
    mock_db_session_analysis.__aexit__ = AsyncMock(return_value=False)

    # Mock database session for artifact query (returns None - no artifact)
    mock_db_session_artifact = AsyncMock()
    mock_db_session_artifact.__aenter__ = AsyncMock(return_value=mock_db_session_artifact)
    mock_db_session_artifact.__aexit__ = AsyncMock(return_value=False)

    # Mock repository - return None (artifact not found)
    mock_repository = AsyncMock()
    mock_repository.get_artifact_by_analysis_id = AsyncMock(return_value=None)

    # Track session calls to return different sessions
    session_calls = [mock_db_session_persist, mock_db_session_analysis, mock_db_session_artifact]

    def session_factory():
        return session_calls.pop(0) if session_calls else mock_db_session_artifact

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repository,
        ),
    ):
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify status was updated to ARTIFACT_FAILED (not complete) due to missing artifact
    mock_update_status.assert_called()
    # Check that status was set to "artifact_failed" (not "complete")
    status_calls = list(mock_update_status.call_args_list)
    # Last call should be "artifact_failed" (after artifact validation fails)
    assert len(status_calls) >= 1
    # Verify the last call was with artifact_failed status
    last_call = status_calls[-1]
    assert last_call[0][1] == "artifact_failed"
    # Verify error was emitted
    mock_emit_error.assert_called_once()

    # Verify error was logged
    error_logs = [
        call
        for call in mock_logger.error.call_args_list
        if "workflow_complete_without_artifact" in str(call)
    ]
    assert len(error_logs) == 1

    # Verify complete event was NOT emitted (workflow failed)
    publish_calls = mock_broadcaster.publish.call_args_list
    complete_calls = [
        call for call in publish_calls if len(call[0]) > 1 and call[0][1].get("type") == "complete"
    ]
    assert len(complete_calls) == 0, "Complete event should not be emitted when artifact is missing"


# ============================================================================
# Tests for Langfuse Graph Visualization (Issue #384)
# ============================================================================


@pytest.mark.asyncio
@patch("app.shared.services.persistence.progress.persist_progress_event_async")
@patch("app.shared.services.messaging.sse_helpers.get_broadcaster", new_callable=AsyncMock)
@patch("app.domains.analysis.services.workflow.orchestrator.analysis_workflow")
@patch("app.domains.analysis.services.workflow.orchestrator.logger")
async def test_langfuse_callback_passed_to_workflow(
    mock_logger,
    mock_workflow,
    mock_get_broadcaster,
    mock_persist_progress,
    mock_analysis_id,
    test_url,
):
    """Test that Langfuse callback handler is passed to workflow invocation (Issue #384).

    This test verifies that when Langfuse is enabled, the callback handler
    is included in the config passed to graph.ainvoke(), enabling graph
    visualization in the Langfuse UI.
    """
    import uuid

    from app.db.models.artifact import Artifact

    # Mock broadcaster factory (async function)
    # Create broadcaster mock before setting return_value
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()
    # Configure the async mock to return the broadcaster when awaited
    # For AsyncMock, return_value works for awaited calls
    mock_get_broadcaster.return_value = mock_broadcaster
    # Also ensure the mock is callable and returns the broadcaster
    mock_get_broadcaster.side_effect = None  # Clear any side_effect

    # Mock workflow to complete successfully
    mock_workflow.ainvoke = AsyncMock(
        return_value={
            "raw_content": "Test content",
            "extraction_metadata": {"title": "Test Title"},
            "content_embedding": [0.1] * 1536,
        }
    )

    # Mock analysis and artifact
    mock_analysis = MagicMock()
    mock_analysis.status = "pending"
    mock_analysis.id = mock_analysis_id

    artifact_id = uuid.uuid4()
    mock_artifact = MagicMock(spec=Artifact)
    mock_artifact.id = artifact_id

    # Mock database sessions (same pattern as other tests)
    mock_db_session_persist = AsyncMock()
    mock_result_persist = MagicMock()
    mock_result_persist.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_persist.execute.return_value = mock_result_persist
    mock_db_session_persist.__aenter__ = AsyncMock(return_value=mock_db_session_persist)
    mock_db_session_persist.__aexit__ = AsyncMock(return_value=False)

    mock_db_session_artifact_validation = AsyncMock()
    mock_db_session_artifact_validation.__aenter__ = AsyncMock(
        return_value=mock_db_session_artifact_validation
    )
    mock_db_session_artifact_validation.__aexit__ = AsyncMock(return_value=False)

    mock_db_session_status = AsyncMock()
    mock_result_status = MagicMock()
    mock_result_status.scalar_one_or_none.return_value = mock_analysis
    mock_db_session_status.execute.return_value = mock_result_status
    mock_db_session_status.__aenter__ = AsyncMock(return_value=mock_db_session_status)
    mock_db_session_status.__aexit__ = AsyncMock(return_value=False)

    mock_db_session_artifact_event = AsyncMock()
    mock_db_session_artifact_event.__aenter__ = AsyncMock(
        return_value=mock_db_session_artifact_event
    )
    mock_db_session_artifact_event.__aexit__ = AsyncMock(return_value=False)

    mock_repository_instance = AsyncMock()
    mock_repository_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    session_calls = [
        mock_db_session_persist,
        mock_db_session_artifact_validation,
        mock_db_session_status,
        mock_db_session_artifact_event,
    ]

    def session_factory():
        return session_calls.pop(0) if session_calls else mock_db_session_artifact_event

    # Mock Langfuse callback handler to be enabled
    mock_callback_handler = MagicMock()

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.data_persister.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.persistence.status_updater.AsyncSessionLocal",
            side_effect=session_factory,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repository_instance,
        ),
        patch(
            "app.core.langfuse_service.get_langfuse_callback_handler",
            return_value=mock_callback_handler,
        ),
    ):
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(mock_analysis_id, test_url)

    # Verify workflow was called with config containing callbacks
    mock_workflow.ainvoke.assert_called_once()
    call_args = mock_workflow.ainvoke.call_args

    # Extract config from kwargs (config is passed as named parameter)
    config = call_args.kwargs.get("config") or call_args[1] if len(call_args) > 1 else {}

    # Verify callbacks are present in config (Issue #384)
    assert "callbacks" in config, "Config should contain 'callbacks' key for graph visualization"
    assert config["callbacks"] == [mock_callback_handler], (
        "Callbacks should contain Langfuse handler"
    )

    # Verify debug log was called with callbacks_enabled=True
    debug_calls = [
        call
        for call in mock_logger.debug.call_args_list
        if "langfuse_callback_enabled" in str(call)
    ]
    assert len(debug_calls) == 1, "Should log that Langfuse callback is enabled"
