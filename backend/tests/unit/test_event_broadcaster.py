"""Tests for event broadcaster service."""

import asyncio

import pytest

from app.services.event_broadcaster import EventBroadcaster


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
    subscriber_task = asyncio.create_task(
        broadcaster.subscribe(channel).__anext__()
    )

    # Wait a bit for subscription to register
    await asyncio.sleep(0.1)

    # Verify subscriber is registered
    assert broadcaster.get_subscriber_count(channel) == 1

    # Cancel subscriber
    subscriber_task.cancel()
    try:
        await subscriber_task
    except asyncio.CancelledError:
        pass

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
    try:
        await sub_task
    except asyncio.CancelledError:
        pass

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
