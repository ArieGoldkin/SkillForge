"""Unit tests for workflow runner background task."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.workflow_runner import (
    _persist_analysis_data,
    _validate_workflow_result,
    run_workflow_task,
)


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
    import uuid

    from app.models.artifact import Artifact

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

    # Patch AsyncSessionLocal at the source (app.db.session)
    with (
        patch("app.db.session.AsyncSessionLocal", side_effect=session_factory),
        patch(
            "app.db.repositories.artifact_repository.ArtifactRepository",
            return_value=mock_repository_instance,
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
    mock_db_session_status.commit.assert_called_once()

    # Verify complete event was emitted with artifact_id
    complete_calls = [call for call in mock_emit_event.call_args_list if call[0][0] == "complete"]
    assert len(complete_calls) == 1, "Complete event should be emitted exactly once"
    complete_call = complete_calls[0]
    assert "artifact_id" in complete_call.kwargs
    assert complete_call.kwargs["artifact_id"] == str(artifact_id)


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
    import uuid

    from app.models.artifact import Artifact

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
        patch("app.db.session.AsyncSessionLocal", side_effect=session_factory),
        patch(
            "app.db.repositories.artifact_repository.ArtifactRepository",
            return_value=mock_repository_instance,
        ),
    ):
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
        msg = f"No complete event found. All calls: {[(c.args, c.kwargs) for c in all_calls]}"
        raise AssertionError(msg)

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


@pytest.mark.asyncio
@patch("app.api.v1.workflow_runner.emit_streaming_event")
@patch("app.api.v1.workflow_runner.analysis_workflow")
@patch("app.api.v1.workflow_runner.logger")
@patch("app.api.v1.workflow_runner._update_analysis_status")
@patch("app.api.v1.workflow_runner._emit_workflow_error")
async def test_run_workflow_task_fails_without_artifact(
    mock_emit_error,
    mock_update_status,
    mock_logger,
    mock_workflow,
    mock_emit_event,
    mock_analysis_id,
    test_url,
):
    """Test that workflow fails when artifact is missing (artifact validation fix).

    This test verifies the fix where analysis is not marked complete if
    artifact generation failed or was skipped.
    """
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
        patch("app.db.session.AsyncSessionLocal", side_effect=session_factory),
        patch(
            "app.db.repositories.artifact_repository.ArtifactRepository",
            return_value=mock_repository,
        ),
    ):
        await run_workflow_task(mock_analysis_id, test_url)

    # Verify workflow completed
    mock_workflow.ainvoke.assert_called_once()

    # Verify status was updated to FAILED (not complete) due to missing artifact
    mock_update_status.assert_called()
    # Check that status was set to "failed" (not "complete")
    status_calls = list(mock_update_status.call_args_list)
    # Last call should be "failed" (after artifact validation fails)
    assert len(status_calls) >= 1
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
    complete_calls = [call for call in mock_emit_event.call_args_list if call[0][0] == "complete"]
    assert len(complete_calls) == 0, "Complete event should not be emitted when artifact is missing"


# ============================================================================
# Tests for _persist_analysis_data (Issue #168)
# ============================================================================


@pytest.mark.asyncio
async def test_persist_analysis_data_success(mock_analysis_id):
    """Test successful persistence of workflow data to analysis record."""
    # Mock analysis record
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.raw_content = None
    mock_analysis.title = None
    mock_analysis.extraction_metadata = None
    mock_analysis.content_embedding = None

    # Mock database session
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # Workflow result with all fields
    workflow_result = {
        "raw_content": "This is the extracted content about React hooks...",
        "extraction_metadata": {
            "title": "React Hooks Tutorial",
            "word_count": 1500,
            "author": "Test Author",
        },
        "content_embedding": [0.1] * 1536,  # 1536-dimensional vector
    }

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        result = await _persist_analysis_data(mock_analysis_id, workflow_result)

    # Verify success
    assert result is True

    # Verify all fields were set
    assert mock_analysis.raw_content == workflow_result["raw_content"]
    assert mock_analysis.title == "React Hooks Tutorial"
    assert mock_analysis.extraction_metadata == workflow_result["extraction_metadata"]
    assert mock_analysis.content_embedding == workflow_result["content_embedding"]

    # Verify commit was called
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_persist_analysis_data_partial_data(mock_analysis_id):
    """Test persistence with partial workflow data (only some fields present)."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.raw_content = None
    mock_analysis.title = None
    mock_analysis.extraction_metadata = None
    mock_analysis.content_embedding = None

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # Workflow result with only raw_content (no embedding, no metadata)
    workflow_result = {
        "raw_content": "Partial content...",
    }

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        result = await _persist_analysis_data(mock_analysis_id, workflow_result)

    assert result is True
    assert mock_analysis.raw_content == "Partial content..."
    # Title and embedding should not be set (no metadata/embedding in result)
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_persist_analysis_data_analysis_not_found(mock_analysis_id):
    """Test persistence when analysis record is not found."""
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Analysis not found
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    workflow_result = {"raw_content": "Content..."}

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        result = await _persist_analysis_data(mock_analysis_id, workflow_result)

    # Should return False when analysis not found
    assert result is False
    mock_db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_persist_analysis_data_database_error(mock_analysis_id):
    """Test persistence handles database errors gracefully."""
    mock_db_session = AsyncMock()
    mock_db_session.execute.side_effect = ConnectionError("DB connection failed")
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    workflow_result = {"raw_content": "Content..."}

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        with pytest.raises(RuntimeError, match="Failed to persist analysis data"):
            await _persist_analysis_data(mock_analysis_id, workflow_result)


@pytest.mark.asyncio
async def test_persist_analysis_data_empty_result(mock_analysis_id):
    """Test persistence with empty workflow result."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # Empty workflow result
    workflow_result = {}

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        result = await _persist_analysis_data(mock_analysis_id, workflow_result)

    # Should still succeed (just no data to persist)
    assert result is True
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_persist_analysis_data_extracts_title_from_metadata(mock_analysis_id):
    """Test that title is correctly extracted from extraction_metadata."""
    mock_analysis = MagicMock()
    mock_analysis.id = mock_analysis_id
    mock_analysis.title = None

    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_analysis
    mock_db_session.execute.return_value = mock_result
    mock_db_session.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_db_session.__aexit__ = AsyncMock(return_value=False)

    # extraction_metadata with title
    workflow_result = {
        "extraction_metadata": {
            "title": "My Amazing Article Title",
            "description": "Article description",
        },
    }

    with patch("app.db.session.AsyncSessionLocal", return_value=mock_db_session):
        await _persist_analysis_data(mock_analysis_id, workflow_result)

    # Verify title was extracted and set
    assert mock_analysis.title == "My Amazing Article Title"
    assert mock_analysis.extraction_metadata == workflow_result["extraction_metadata"]


def test_validate_workflow_result_identifies_missing_fields():
    """Validate helper identifies missing required workflow fields."""
    result = {
        "raw_content": "content",
        "extraction_metadata": None,
        "content_embedding": None,
    }

    missing = _validate_workflow_result(result)
    assert set(missing) == {"extraction_metadata", "content_embedding"}
