"""Unit tests for WorkflowEventEmitter."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.services.events.workflow_events import WorkflowEventEmitter


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.mark.asyncio
async def test_event_emitter_emit_error(mock_analysis_id):
    """Test error event emission."""
    # Mock broadcaster factory (async function)
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()

    with (
        patch(
            "app.shared.services.messaging.sse_helpers.get_broadcaster",
            new_callable=AsyncMock,
            return_value=mock_broadcaster,
        ),
        patch(
            "app.shared.services.persistence.progress.persist_progress_event_async",
            new_callable=MagicMock,
        ),
    ):
        emitter = WorkflowEventEmitter()
        error = ValueError("Test error")
        await emitter.emit_error(mock_analysis_id, error)

        # Verify broadcaster.publish was called
        mock_broadcaster.publish.assert_called_once()
        call_args = mock_broadcaster.publish.call_args
        channel = call_args[0][0]
        event_data = call_args[0][1]

        assert channel == f"workflow:{mock_analysis_id}"
        assert event_data["type"] == "error"
        assert event_data["analysis_id"] == str(mock_analysis_id)
        assert event_data["stage"] == "workflow"
        assert event_data["status"] == "failed"
        assert event_data["error"] == str(error)


@pytest.mark.asyncio
async def test_event_emitter_emit_completion_with_artifact(mock_analysis_id):
    """Test completion event emission with artifact_id."""
    artifact_id = str(uuid.uuid4())
    trace_id = "test-trace-id"

    # Mock broadcaster factory (async function)
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()

    with (
        patch(
            "app.shared.services.messaging.sse_helpers.get_broadcaster",
            new_callable=AsyncMock,
            return_value=mock_broadcaster,
        ),
        patch(
            "app.shared.services.persistence.progress.persist_progress_event_async",
            new_callable=MagicMock,
        ),
    ):
        emitter = WorkflowEventEmitter()
        await emitter.emit_completion(mock_analysis_id, artifact_id, trace_id)

        # Verify broadcaster.publish was called
        mock_broadcaster.publish.assert_called_once()
        call_args = mock_broadcaster.publish.call_args
        channel = call_args[0][0]
        event_data = call_args[0][1]

        assert channel == f"workflow:{mock_analysis_id}"
        assert event_data["type"] == "complete"
        assert event_data["analysis_id"] == str(mock_analysis_id)
        assert event_data["artifact_id"] == artifact_id
        assert event_data["trace_id"] == trace_id


@pytest.mark.asyncio
async def test_event_emitter_emit_completion_without_artifact(mock_analysis_id):
    """Test completion event emission without artifact_id."""
    trace_id = "test-trace-id"

    # Mock broadcaster factory (async function)
    mock_broadcaster = AsyncMock()
    mock_broadcaster.publish = AsyncMock()

    with (
        patch(
            "app.shared.services.messaging.sse_helpers.get_broadcaster",
            new_callable=AsyncMock,
            return_value=mock_broadcaster,
        ),
        patch(
            "app.shared.services.persistence.progress.persist_progress_event_async",
            new_callable=MagicMock,
        ),
    ):
        emitter = WorkflowEventEmitter()
        await emitter.emit_completion(mock_analysis_id, None, trace_id)

        # Verify broadcaster.publish was called
        mock_broadcaster.publish.assert_called_once()
        call_args = mock_broadcaster.publish.call_args
        channel = call_args[0][0]
        event_data = call_args[0][1]

        assert channel == f"workflow:{mock_analysis_id}"
        assert event_data["type"] == "complete"
        assert event_data["analysis_id"] == str(mock_analysis_id)
        assert "artifact_id" not in event_data
        assert event_data["trace_id"] == trace_id

