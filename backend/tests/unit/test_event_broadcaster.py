"""Tests for event broadcaster service."""

import asyncio
import contextlib

import pytest

from app.shared.services.messaging.broadcaster import EventBroadcaster, MAX_BUFFER_SIZE

@pytest.mark.unit


@pytest.mark.asyncio
async def test_publish_subscribe_single_message():
    """Test publishing and subscribing to a single message."""
    broadcaster = EventBroadcaster()
    channel = "test:channel"

    async def subscriber():
        """Subscribe and wait for first message."""
        async for message in broadcaster.subscribe(channel):
            return message

    async def publisher():
        """Wait for subscriber to be ready, then publish."""
        await asyncio.sleep(0.1)  # Wait for subscriber to register
        await broadcaster.publish(channel, {"type": "test", "data": "hello"})

    # Run both concurrently
    subscriber_task = asyncio.create_task(subscriber())
    publisher_task = asyncio.create_task(publisher())

    message = await subscriber_task
    await publisher_task

    assert message["type"] == "test"
    assert message["data"] == "hello"


@pytest.mark.asyncio
async def test_publish_multiple_subscribers():
    """Test publishing to multiple subscribers."""
    broadcaster = EventBroadcaster()
    channel = "test:multi"

    messages1 = []
    messages2 = []

    async def subscriber1():
        async for message in broadcaster.subscribe(channel):
            messages1.append(message)
            if len(messages1) >= 2:
                break

    async def subscriber2():
        async for message in broadcaster.subscribe(channel):
            messages2.append(message)
            if len(messages2) >= 2:
                break

    async def publisher():
        await asyncio.sleep(0.1)  # Wait for subscribers
        await broadcaster.publish(channel, {"type": "test", "num": 1})
        await asyncio.sleep(0.1)
        await broadcaster.publish(channel, {"type": "test", "num": 2})

    # Run all concurrently
    sub1_task = asyncio.create_task(subscriber1())
    sub2_task = asyncio.create_task(subscriber2())
    pub_task = asyncio.create_task(publisher())

    await asyncio.gather(sub1_task, sub2_task, pub_task)

    assert len(messages1) == 2
    assert len(messages2) == 2
    assert messages1[0]["num"] == 1
    assert messages1[1]["num"] == 2
    assert messages2[0]["num"] == 1
    assert messages2[1]["num"] == 2


@pytest.mark.asyncio
async def test_subscribe_cleanup_on_cancel():
    """Test that subscriber cleanup works on cancellation."""
    broadcaster = EventBroadcaster()
    channel = "test:cleanup"

    # Start subscriber
    subscriber_task = asyncio.create_task(broadcaster.subscribe(channel).__anext__())

    # Wait a bit for subscription to register
    await asyncio.sleep(0.1)

    # Verify subscriber is registered
    assert broadcaster.get_subscriber_count(channel) == 1

    # Cancel subscriber
    subscriber_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await subscriber_task

    # Wait for cleanup
    await asyncio.sleep(0.1)

    # Verify subscriber is removed
    assert broadcaster.get_subscriber_count(channel) == 0


@pytest.mark.asyncio
async def test_publish_no_subscribers():
    """Test publishing to channel with no subscribers."""
    broadcaster = EventBroadcaster()
    channel = "test:empty"

    # Publish to empty channel (should not raise error)
    await broadcaster.publish(channel, {"type": "test"})

    # Verify no subscribers
    assert broadcaster.get_subscriber_count(channel) == 0


@pytest.mark.asyncio
async def test_get_subscriber_count():
    """Test getting subscriber count for a channel."""
    broadcaster = EventBroadcaster()
    channel = "test:count"

    # No subscribers initially
    assert broadcaster.get_subscriber_count(channel) == 0

    # Add subscriber
    async def subscriber():
        async for _ in broadcaster.subscribe(channel):
            pass

    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)  # Wait for subscription

    assert broadcaster.get_subscriber_count(channel) == 1

    # Cancel subscriber
    sub_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await sub_task

    await asyncio.sleep(0.1)  # Wait for cleanup
    assert broadcaster.get_subscriber_count(channel) == 0


@pytest.mark.asyncio
async def test_multiple_channels():
    """Test that different channels are isolated."""
    broadcaster = EventBroadcaster()
    channel1 = "test:channel1"
    channel2 = "test:channel2"

    messages1 = []
    messages2 = []

    async def subscriber1():
        async for message in broadcaster.subscribe(channel1):
            messages1.append(message)
            if len(messages1) >= 1:
                break

    async def subscriber2():
        async for message in broadcaster.subscribe(channel2):
            messages2.append(message)
            if len(messages2) >= 1:
                break

    async def publisher():
        await asyncio.sleep(0.1)
        await broadcaster.publish(channel1, {"type": "channel1"})
        await broadcaster.publish(channel2, {"type": "channel2"})

    sub1_task = asyncio.create_task(subscriber1())
    sub2_task = asyncio.create_task(subscriber2())
    pub_task = asyncio.create_task(publisher())

    await asyncio.gather(sub1_task, sub2_task, pub_task)

    assert len(messages1) == 1
    assert len(messages2) == 1
    assert messages1[0]["type"] == "channel1"
    assert messages2[0]["type"] == "channel2"


# ============================================================================
# Event Buffering Tests (Issue #SSE-RACE)
# ============================================================================


@pytest.mark.asyncio
async def test_buffer_replay_events_published_before_subscriber():
    """Test that events published BEFORE subscriber connects are replayed.

    This is the critical fix for the SSE race condition where workflow
    starts emitting events before frontend SSE connection is established.
    """
    broadcaster = EventBroadcaster()
    channel = "test:buffer"

    # Publish events BEFORE any subscriber connects
    await broadcaster.publish(channel, {"type": "progress", "stage": "extraction", "num": 1})
    await broadcaster.publish(channel, {"type": "progress", "stage": "embedding", "num": 2})
    await broadcaster.publish(channel, {"type": "progress", "stage": "agents", "num": 3})

    # Verify no subscribers yet
    assert broadcaster.get_subscriber_count(channel) == 0

    # Now subscribe - should receive all buffered events
    received_messages = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel):
            received_messages.append(message)
            if len(received_messages) >= 3:
                break

    sub_task = asyncio.create_task(subscriber())
    await asyncio.wait_for(sub_task, timeout=2.0)

    # Verify all buffered events were replayed in order
    assert len(received_messages) == 3
    assert received_messages[0]["num"] == 1
    assert received_messages[1]["num"] == 2
    assert received_messages[2]["num"] == 3
    assert received_messages[0]["stage"] == "extraction"
    assert received_messages[1]["stage"] == "embedding"
    assert received_messages[2]["stage"] == "agents"


@pytest.mark.asyncio
async def test_buffer_replay_then_live_events():
    """Test that subscriber receives buffered events first, then live events."""
    broadcaster = EventBroadcaster()
    channel = "test:buffer_live"

    # Publish buffered events first
    await broadcaster.publish(channel, {"type": "buffered", "num": 1})
    await broadcaster.publish(channel, {"type": "buffered", "num": 2})

    received_messages = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel):
            received_messages.append(message)
            if len(received_messages) >= 4:
                break

    # Start subscriber
    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)  # Let subscriber register

    # Publish live events after subscriber is connected
    await broadcaster.publish(channel, {"type": "live", "num": 3})
    await broadcaster.publish(channel, {"type": "live", "num": 4})

    await asyncio.wait_for(sub_task, timeout=2.0)

    # Verify order: buffered events first, then live events
    assert len(received_messages) == 4
    assert received_messages[0]["type"] == "buffered"
    assert received_messages[1]["type"] == "buffered"
    assert received_messages[2]["type"] == "live"
    assert received_messages[3]["type"] == "live"


@pytest.mark.asyncio
async def test_buffer_clear():
    """Test that buffer can be explicitly cleared."""
    broadcaster = EventBroadcaster()
    channel = "test:buffer_clear"

    # Publish some events
    await broadcaster.publish(channel, {"type": "test", "num": 1})
    await broadcaster.publish(channel, {"type": "test", "num": 2})

    # Clear the buffer
    await broadcaster.clear_buffer(channel)

    # Subscribe and verify no buffered events
    received_messages = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel):
            received_messages.append(message)
            if len(received_messages) >= 1:
                break

    sub_task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.1)  # Let subscriber register

    # Publish a new event to trigger receipt
    await broadcaster.publish(channel, {"type": "new", "num": 3})

    await asyncio.wait_for(sub_task, timeout=2.0)

    # Should only have the new event, not the cleared buffered ones
    assert len(received_messages) == 1
    assert received_messages[0]["type"] == "new"
    assert received_messages[0]["num"] == 3


@pytest.mark.asyncio
async def test_buffer_per_channel_isolation():
    """Test that buffers are isolated per channel."""
    broadcaster = EventBroadcaster()
    channel1 = "test:buffer_iso1"
    channel2 = "test:buffer_iso2"

    # Publish to both channels before any subscribers
    await broadcaster.publish(channel1, {"channel": 1, "msg": "a"})
    await broadcaster.publish(channel1, {"channel": 1, "msg": "b"})
    await broadcaster.publish(channel2, {"channel": 2, "msg": "x"})

    # Subscribe to channel1 only
    received = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel1):
            received.append(message)
            if len(received) >= 2:
                break

    sub_task = asyncio.create_task(subscriber())
    await asyncio.wait_for(sub_task, timeout=2.0)

    # Should only have channel1 messages
    assert len(received) == 2
    assert all(m["channel"] == 1 for m in received)


@pytest.mark.asyncio
async def test_buffer_max_size_limit():
    """Test that buffer respects max size limit."""
    from app.shared.services.messaging.broadcaster import MAX_BUFFER_SIZE

    broadcaster = EventBroadcaster()
    channel = "test:buffer_limit"

    # Publish more events than buffer size
    for i in range(MAX_BUFFER_SIZE + 50):
        await broadcaster.publish(channel, {"num": i})

    # Subscribe and collect events
    received = []

    async def subscriber():
        async for message in broadcaster.subscribe(channel):
            received.append(message)
            if len(received) >= MAX_BUFFER_SIZE:
                break

    sub_task = asyncio.create_task(subscriber())
    await asyncio.wait_for(sub_task, timeout=5.0)

    # Should have exactly MAX_BUFFER_SIZE events (oldest were dropped)
    assert len(received) == MAX_BUFFER_SIZE
    # First received event should be event #50 (oldest 50 were dropped)
    assert received[0]["num"] == 50
