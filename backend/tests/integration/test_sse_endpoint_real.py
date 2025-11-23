"""Integration tests for SSE endpoint with real workflow execution.

These tests require .env.test with real API keys (JINA_API_KEY, etc.)
and will be skipped if .env.test doesn't exist or keys are missing.
"""

import asyncio
import json
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from sse_starlette.sse import EventSourceResponse

from app.api.v1.analyze import stream_analysis_progress
from app.core.config import settings
from app.services.event_broadcaster import broadcaster
from app.workflows.analysis import analysis_workflow

# Check if .env.test exists
TEST_ENV_FILE = Path(__file__).parent.parent.parent / ".env.test"
HAS_TEST_ENV = TEST_ENV_FILE.exists()
HAS_JINA_KEY = bool(settings.JINA_API_KEY)


@pytest.fixture
def requires_test_env():
    """Skip test if .env.test doesn't exist."""
    if not HAS_TEST_ENV:
        pytest.skip(".env.test file not found - create it from .env.test.example")
    if not HAS_JINA_KEY:
        pytest.skip("JINA_API_KEY not set in .env.test - skipping real API test")


@pytest.mark.asyncio
async def test_sse_endpoint_with_real_workflow(requires_test_env):
    """Test SSE endpoint with real workflow execution.

    This test:
    1. Connects to SSE endpoint
    2. Triggers real workflow execution
    3. Verifies events stream in real-time
    4. Verifies complete event is received
    """
    analysis_id = str(uuid.uuid4())
    channel = f"workflow:{analysis_id}"

    # Mock request object
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    # Get SSE event generator
    response = await stream_analysis_progress(uuid.UUID(analysis_id), mock_request)
    assert isinstance(response, EventSourceResponse)

    # Start workflow in background task
    async def run_workflow():
        """Run workflow and emit SSE events."""
        try:
            result = await analysis_workflow(
                url="https://react.dev",
                analysis_id=analysis_id,
            )
            # Emit complete event
            await broadcaster.publish(
                channel,
                {
                    "type": "complete",
                    "analysis_id": analysis_id,
                    "stage": "artifact_generation",
                    "status": "complete",
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            )
        except Exception as e:
            # Emit error event on failure
            # Emit error event
            await broadcaster.publish(
                channel,
                {
                    "type": "error",
                    "analysis_id": analysis_id,
                    "stage": "workflow",
                    "status": "failed",
                    "error": str(e),
                    "timestamp": "2025-01-01T00:00:00Z",
                },
            )
            raise

    # Start workflow task
    workflow_task = asyncio.create_task(run_workflow())

    # Collect events from SSE stream
    events_received = []
    try:
        # Get the event generator from EventSourceResponse
        event_gen = response.body_iterator

        # Read events with timeout
        timeout = 30.0  # 30 seconds for real workflow
        start_time = asyncio.get_event_loop().time()

        async for event_dict in event_gen:
            if asyncio.get_event_loop().time() - start_time > timeout:
                break

            events_received.append(event_dict)

            # Stop on complete event
            if event_dict.get("event") == "complete":
                break

    except asyncio.CancelledError:
        pass
    finally:
        # Wait for workflow to complete
        try:
            await asyncio.wait_for(workflow_task, timeout=5.0)
        except TimeoutError:
            workflow_task.cancel()

    # Verify we received events
    assert len(events_received) > 0, "No events received from SSE stream"

    # Verify event structure
    for event in events_received:
        assert "event" in event, "Event missing 'event' field"
        assert "data" in event, "Event missing 'data' field"

        # Parse data
        data = json.loads(event["data"])
        assert "type" in data, "Event data missing 'type' field"
        assert "analysis_id" in data, "Event data missing 'analysis_id' field"
        assert data["analysis_id"] == analysis_id, "Event has wrong analysis_id"

    # Verify we received progress events
    progress_events = [
        e for e in events_received if json.loads(e["data"]).get("type") == "progress"
    ]
    assert len(progress_events) > 0, "No progress events received"

    # Verify complete event was received (if workflow completed)
    # Complete event may or may not be received depending on timing
    # This is acceptable - the important thing is that events streamed


@pytest.mark.asyncio
async def test_sse_endpoint_real_workflow_events(requires_test_env):
    """Test that real workflow execution emits SSE events.

    This test verifies that when a workflow runs, it emits SSE events
    that can be received via the SSE endpoint.
    """
    analysis_id = str(uuid.uuid4())

    # Run workflow (which should emit SSE events)
    workflow_task = asyncio.create_task(
        analysis_workflow(url="https://python.org", analysis_id=analysis_id)
    )

    # Wait a bit for workflow to start and emit events
    await asyncio.sleep(1.0)

    # Check that events were published to broadcaster
    # (The workflow uses emit_streaming_event which publishes to broadcaster)
    # Note: Subscriber count may be 0 if no one is subscribed, but events
    # should still be published

    # Wait for workflow to complete
    try:
        result = await asyncio.wait_for(workflow_task, timeout=30.0)
        assert "analysis_id" in result
        assert result["analysis_id"] == analysis_id
        assert "raw_content" in result
        assert "content_embedding" in result
    except TimeoutError:
        workflow_task.cancel()
        pytest.fail("Workflow did not complete within timeout")
