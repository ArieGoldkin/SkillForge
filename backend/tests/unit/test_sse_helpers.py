"""Tests for SSE helper functions."""

import pytest

from app.services.sse_helpers import emit_streaming_event


@pytest.mark.asyncio
async def test_emit_streaming_event():
    """Test emitting a streaming event."""
    analysis_id = "123e4567-e89b-12d3-a456-426614174000"
    channel = f"workflow:{analysis_id}"

    # Subscribe to channel to capture event
    from app.services.event_broadcaster import broadcaster

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

    from app.services.event_broadcaster import broadcaster

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
