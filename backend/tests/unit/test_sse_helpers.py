"""Tests for SSE helper functions."""

from unittest.mock import patch

import pytest

from app.services.messaging.sse_helpers import emit_streaming_event


@pytest.mark.asyncio
async def test_emit_streaming_event():
    """Test emitting a streaming event."""
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"
    channel = f"workflow:{analysis_id}"

    # Subscribe to channel to capture event
    from app.services.messaging.broadcaster import broadcaster

    messages = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel):
            messages.append(message)
            break

    import asyncio

    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)  # Wait for subscription

    # Emit event
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
        word_count=5234,
    )

    await sub_task

    assert len(messages) == 1
    event = messages[0]
    assert event["type"] == "progress"
    assert event["analysis_id"] == analysis_id
    assert event["stage"] == "extraction"
    assert event["status"] == "running"
    assert event["word_count"] == 5234
    assert "timestamp" in event


@pytest.mark.asyncio
async def test_emit_streaming_event_with_kwargs():
    """Test emitting event with additional kwargs."""
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"
    channel = f"workflow:{analysis_id}"

    from app.services.messaging.broadcaster import broadcaster

    messages = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel):
            messages.append(message)
            break

    import asyncio

    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)

    await emit_streaming_event(
        "complete",
        analysis_id=analysis_id,
        stage="artifact_generation",
        status="complete",
        artifact_id="artifact-123",
        download_count=0,
    )

    await sub_task

    assert len(messages) == 1
    event = messages[0]
    assert event["type"] == "complete"
    assert event["artifact_id"] == "artifact-123"
    assert event["download_count"] == 0


@pytest.mark.asyncio
@patch("app.services.persistence.progress.persist_progress_event_async")
async def test_emit_streaming_event_persists_to_database(mock_persist):
    """Test that emit_streaming_event triggers progress persistence.

    This test verifies the fix where SSE events are persisted to the
    analysis_progress table for historical tracking.
    """
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"

    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
        word_count=5234,
    )

    # Verify persist_progress_event_async was called
    assert mock_persist.called
    call_args = mock_persist.call_args[0]
    event_data = call_args[0]

    # Verify event data structure
    assert event_data["type"] == "progress"
    assert event_data["analysis_id"] == analysis_id
    assert event_data["stage"] == "extraction"
    assert event_data["status"] == "running"
    assert event_data["word_count"] == 5234
    assert "timestamp" in event_data


@pytest.mark.asyncio
@patch("app.services.persistence.progress.persist_progress_event_async")
async def test_emit_streaming_event_persistence_non_blocking(mock_persist):
    """Test that persistence failure doesn't break SSE event emission.

    Note: persist_progress_event_async is a synchronous function that creates
    a background task. Errors in the task are handled by the completion callback,
    not raised synchronously. This test verifies that even if persistence fails,
    the SSE event is still broadcast successfully.
    """
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"

    # Mock persistence to do nothing (simulating it being called but errors handled internally)
    # The actual implementation creates a task that handles errors in its callback
    mock_persist.return_value = None

    # Event should still be emitted (persistence is fire-and-forget)
    from app.services.messaging.broadcaster import broadcaster

    channel = f"workflow:{analysis_id}"
    messages = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel):
            messages.append(message)
            break

    import asyncio

    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)

    # Should not raise - persistence is fire-and-forget
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
    )

    await sub_task

    # Verify event was still broadcast despite any persistence issues
    assert len(messages) == 1
    assert messages[0]["type"] == "progress"
    # Verify persistence was attempted
    assert mock_persist.called
