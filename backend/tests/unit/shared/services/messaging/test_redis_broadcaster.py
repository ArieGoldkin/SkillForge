"""Unit tests for Redis event broadcaster.

Tests verify Redis-backed pub/sub with event buffering for multi-instance
SSE delivery. Mocks Redis client to avoid external dependencies.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from redis.asyncio.client import PubSub

from app.shared.services.messaging.redis_broadcaster import (
    REDIS_BUFFER_MAX_SIZE,
    REDIS_BUFFER_TTL_SECONDS,
    RedisEventBroadcaster,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Create mock Redis client with common methods."""
    client = AsyncMock()

    # Mock successful ping
    client.ping = AsyncMock(return_value=True)

    # Mock pipeline context manager
    mock_pipe = AsyncMock()
    mock_pipe.rpush = Mock(return_value=mock_pipe)
    mock_pipe.ltrim = Mock(return_value=mock_pipe)
    mock_pipe.expire = Mock(return_value=mock_pipe)
    mock_pipe.publish = Mock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[1, True, True, 0])

    client.pipeline = Mock(return_value=mock_pipe)
    mock_pipe.__aenter__ = AsyncMock(return_value=mock_pipe)
    mock_pipe.__aexit__ = AsyncMock(return_value=None)

    # Mock lrange (buffer replay)
    client.lrange = AsyncMock(return_value=[])

    # Mock delete (buffer clear)
    client.delete = AsyncMock(return_value=1)

    # Mock pubsub_numsub (subscriber count)
    client.pubsub_numsub = AsyncMock(return_value=[(b"channel", 0)])

    # Mock close
    client.close = AsyncMock()

    # Mock pubsub() - returns a PubSub-like object (not async)
    mock_pubsub = AsyncMock(spec=PubSub)
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.unsubscribe = AsyncMock()
    mock_pubsub.close = AsyncMock()

    # Mock get_message for the new timeout-resilient implementation
    mock_pubsub.get_message = AsyncMock(return_value=None)
    client.pubsub = Mock(return_value=mock_pubsub)
    client._mock_pubsub = mock_pubsub  # Store for test access

    return client


@pytest.fixture
def broadcaster(mock_redis_client: AsyncMock) -> RedisEventBroadcaster:
    """Create RedisEventBroadcaster with mocked Redis client."""
    return RedisEventBroadcaster(mock_redis_client)


# =============================================================================
# Test: publish buffers event in Redis
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_buffers_event_in_redis(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that publish() adds event to Redis List buffer."""
    channel = "workflow:123"
    message = {"type": "progress", "stage": "extraction", "percent": 25}

    await broadcaster.publish(channel, message)

    mock_pipe = mock_redis_client.pipeline.return_value

    # 1. rpush - add to buffer
    mock_pipe.rpush.assert_called_once()
    buffer_key, buffered_json = mock_pipe.rpush.call_args[0]
    assert buffer_key == f"buffer:{channel}"

    # Verify message has timestamp
    buffered_msg = json.loads(buffered_json)
    assert buffered_msg["type"] == "progress"
    assert buffered_msg["stage"] == "extraction"
    assert buffered_msg["percent"] == 25
    assert "_buffered_at" in buffered_msg

    # 2. ltrim - maintain max size
    mock_pipe.ltrim.assert_called_once_with(
        f"buffer:{channel}",
        -REDIS_BUFFER_MAX_SIZE,
        -1,
    )

    # 3. expire - set TTL
    mock_pipe.expire.assert_called_once_with(
        f"buffer:{channel}",
        REDIS_BUFFER_TTL_SECONDS,
    )

    # 4. publish - send to Pub/Sub
    mock_pipe.publish.assert_called_once()
    pub_channel, pub_message = mock_pipe.publish.call_args[0]
    assert pub_channel == channel
    assert pub_message == buffered_json

    # Pipeline executed
    mock_pipe.execute.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_sends_to_pubsub(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that publish() sends event to Redis Pub/Sub for real-time delivery."""
    channel = "workflow:456"
    message = {"type": "complete", "status": "success"}

    mock_pipe = mock_redis_client.pipeline.return_value
    mock_pipe.execute = AsyncMock(return_value=[1, True, True, 3])

    await broadcaster.publish(channel, message)

    mock_pipe.publish.assert_called_once()
    pub_channel, pub_json = mock_pipe.publish.call_args[0]
    assert pub_channel == channel

    pub_msg = json.loads(pub_json)
    assert pub_msg["type"] == "complete"
    assert pub_msg["status"] == "success"


# =============================================================================
# Test: subscribe replays buffered events
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_replays_buffered_events(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that subscribe() replays buffered events before live events.

    This is the critical fix for SSE race condition - events published
    before subscriber connects must be replayed.
    """
    channel = "workflow:789"
    mock_pubsub = mock_redis_client._mock_pubsub

    # Mock buffered events
    buffered_events = [
        json.dumps({"type": "progress", "stage": "extraction", "_buffered_at": "2025-01-01T00:00:00Z"}),
        json.dumps({"type": "progress", "stage": "embedding", "_buffered_at": "2025-01-01T00:00:01Z"}),
        json.dumps({"type": "progress", "stage": "agents", "_buffered_at": "2025-01-01T00:00:02Z"}),
    ]
    mock_redis_client.lrange = AsyncMock(return_value=buffered_events)

    # Mock get_message to return None (no live events after buffer replay)
    mock_pubsub.get_message = AsyncMock(return_value=None)

    received = []

    async def collect_events():
        async for event in broadcaster.subscribe(channel):
            received.append(event)
            if len(received) >= 3:
                break

    task = asyncio.create_task(collect_events())
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Verify all buffered events were replayed
    assert len(received) == 3
    assert received[0]["stage"] == "extraction"
    assert received[1]["stage"] == "embedding"
    assert received[2]["stage"] == "agents"

    # Verify timestamps were removed
    assert "_buffered_at" not in received[0]
    assert "_buffered_at" not in received[1]
    assert "_buffered_at" not in received[2]

    mock_redis_client.lrange.assert_called_once_with(f"buffer:{channel}", 0, -1)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_receives_live_events(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that subscribe() receives live events from Pub/Sub after buffer replay."""
    channel = "workflow:live"
    mock_pubsub = mock_redis_client._mock_pubsub

    mock_redis_client.lrange = AsyncMock(return_value=[])

    # Mock get_message to return live events sequentially
    live_messages = [
        {"type": "message", "channel": channel, "data": json.dumps({"type": "live1", "_buffered_at": "2025-01-01T00:00:00Z"})},
        {"type": "message", "channel": channel, "data": json.dumps({"type": "live2", "_buffered_at": "2025-01-01T00:00:01Z"})},
        None,  # End of messages
    ]
    mock_pubsub.get_message = AsyncMock(side_effect=live_messages)

    received = []

    async def collect_events():
        async for event in broadcaster.subscribe(channel):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collect_events())
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert len(received) == 2
    assert received[0]["type"] == "live1"
    assert received[1]["type"] == "live2"
    assert "_buffered_at" not in received[0]
    assert "_buffered_at" not in received[1]


# =============================================================================
# Test: buffer TTL and size limits
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_buffer_ttl_respected(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that buffer TTL is set correctly on publish."""
    channel = "workflow:ttl"
    message = {"type": "test"}

    await broadcaster.publish(channel, message)

    mock_pipe = mock_redis_client.pipeline.return_value
    mock_pipe.expire.assert_called_once_with(
        f"buffer:{channel}",
        REDIS_BUFFER_TTL_SECONDS,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_buffer_max_size_limit(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that buffer is trimmed to max size on publish."""
    channel = "workflow:limit"
    message = {"type": "test"}

    await broadcaster.publish(channel, message)

    mock_pipe = mock_redis_client.pipeline.return_value
    mock_pipe.ltrim.assert_called_once_with(
        f"buffer:{channel}",
        -REDIS_BUFFER_MAX_SIZE,
        -1,
    )


# =============================================================================
# Test: clear buffer
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_buffer(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that clear_buffer() removes buffer from Redis."""
    channel = "workflow:clear"

    await broadcaster.clear_buffer(channel)

    mock_redis_client.delete.assert_called_once_with(f"buffer:{channel}")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_clear_buffer_handles_errors(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that clear_buffer() handles Redis errors gracefully."""
    channel = "workflow:error"

    mock_redis_client.delete = AsyncMock(side_effect=Exception("Redis error"))

    # Should not raise - logs warning instead
    await broadcaster.clear_buffer(channel)


# =============================================================================
# Test: connection failure handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_failure_handling() -> None:
    """Test that create() raises ConnectionError if Redis connection fails."""
    with patch("app.shared.services.messaging.redis_broadcaster.aioredis.from_url") as mock_from_url:
        mock_client = AsyncMock()
        # Use OSError (base class for connection errors) which is caught by the code
        mock_client.ping = AsyncMock(side_effect=OSError("Connection refused"))
        mock_from_url.return_value = mock_client

        with pytest.raises(ConnectionError, match="Failed to connect to Redis"):
            await RedisEventBroadcaster.create()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_failure_raises_exception(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that publish() raises exception on Redis error."""
    channel = "workflow:fail"
    message = {"type": "test"}

    mock_pipe = mock_redis_client.pipeline.return_value
    mock_pipe.execute = AsyncMock(side_effect=Exception("Redis error"))

    with pytest.raises(Exception, match="Redis error"):
        await broadcaster.publish(channel, message)


# =============================================================================
# Test: invalid JSON handling
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_json_in_buffer_skipped(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that subscribe() skips invalid JSON in buffered events."""
    channel = "workflow:badjson"
    mock_pubsub = mock_redis_client._mock_pubsub

    buffered_events = [
        json.dumps({"type": "valid1"}),
        "invalid json {{{",
        json.dumps({"type": "valid2"}),
    ]
    mock_redis_client.lrange = AsyncMock(return_value=buffered_events)

    # Mock get_message to return None (no live events after buffer replay)
    mock_pubsub.get_message = AsyncMock(return_value=None)

    received = []

    async def collect_events():
        async for event in broadcaster.subscribe(channel):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collect_events())
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert len(received) == 2
    assert received[0]["type"] == "valid1"
    assert received[1]["type"] == "valid2"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_json_in_pubsub_skipped(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that subscribe() skips invalid JSON in live Pub/Sub messages."""
    channel = "workflow:badlive"
    mock_pubsub = mock_redis_client._mock_pubsub

    mock_redis_client.lrange = AsyncMock(return_value=[])

    # Mock get_message to return live events sequentially with invalid JSON mixed in
    live_messages = [
        {"type": "message", "channel": channel, "data": json.dumps({"type": "valid1"})},
        {"type": "message", "channel": channel, "data": "invalid json"},
        {"type": "message", "channel": channel, "data": json.dumps({"type": "valid2"})},
        None,  # End of messages
    ]
    mock_pubsub.get_message = AsyncMock(side_effect=live_messages)

    received = []

    async def collect_events():
        async for event in broadcaster.subscribe(channel):
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(collect_events())
    try:
        await asyncio.wait_for(task, timeout=1.0)
    except asyncio.TimeoutError:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    assert len(received) == 2
    assert received[0]["type"] == "valid1"
    assert received[1]["type"] == "valid2"


# =============================================================================
# Test: subscriber cleanup on cancellation
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscribe_cleanup_on_cancel(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that subscribe() cleans up PubSub connection on cancellation."""
    channel = "workflow:cancel"
    mock_pubsub = mock_redis_client._mock_pubsub

    mock_redis_client.lrange = AsyncMock(return_value=[])

    # Mock get_message to raise CancelledError (simulating task cancellation)
    mock_pubsub.get_message = AsyncMock(side_effect=asyncio.CancelledError)

    async def subscribe_task():
        async for _ in broadcaster.subscribe(channel):
            pass

    task = asyncio.create_task(subscribe_task())
    await asyncio.sleep(0.1)

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    mock_pubsub.unsubscribe.assert_called_once_with(channel)
    mock_pubsub.close.assert_called_once()


# =============================================================================
# Test: get subscriber count
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_subscriber_count_async(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that get_subscriber_count_async() returns Redis NUMSUB count."""
    channel = "workflow:count"

    mock_redis_client.pubsub_numsub = AsyncMock(return_value=[(channel.encode(), 3)])

    count = await broadcaster.get_subscriber_count_async(channel)

    assert count == 3
    mock_redis_client.pubsub_numsub.assert_called_once_with(channel)


@pytest.mark.unit
def test_get_subscriber_count_sync_returns_zero(
    broadcaster: RedisEventBroadcaster,
) -> None:
    """Test that sync get_subscriber_count() returns 0 (API compatibility)."""
    channel = "workflow:sync"

    count = broadcaster.get_subscriber_count(channel)

    assert count == 0


# =============================================================================
# Test: close broadcaster
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_broadcaster(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that close() closes Redis connection."""
    await broadcaster.close()

    mock_redis_client.close.assert_called_once()
    assert broadcaster._connected is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_close_handles_errors(
    broadcaster: RedisEventBroadcaster,
    mock_redis_client: AsyncMock,
) -> None:
    """Test that close() handles errors gracefully."""
    mock_redis_client.close = AsyncMock(side_effect=Exception("Close error"))

    # Should not raise - logs warning instead
    await broadcaster.close()


# =============================================================================
# Test: singleton factory
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_singleton_factory() -> None:
    """Test that get_redis_broadcaster() returns singleton instance."""
    from app.shared.services.messaging.redis_broadcaster import (
        get_redis_broadcaster,
        reset_redis_broadcaster,
    )

    await reset_redis_broadcaster()

    with patch("app.shared.services.messaging.redis_broadcaster.RedisEventBroadcaster.create") as mock_create:
        mock_broadcaster = AsyncMock(spec=RedisEventBroadcaster)
        mock_create.return_value = mock_broadcaster

        instance1 = await get_redis_broadcaster()
        assert instance1 == mock_broadcaster
        mock_create.assert_called_once()

        instance2 = await get_redis_broadcaster()
        assert instance2 == mock_broadcaster
        mock_create.assert_called_once()

        await reset_redis_broadcaster()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_singleton() -> None:
    """Test that reset_redis_broadcaster() closes and clears singleton."""
    from app.shared.services.messaging.redis_broadcaster import (
        get_redis_broadcaster,
        reset_redis_broadcaster,
    )

    with patch("app.shared.services.messaging.redis_broadcaster.RedisEventBroadcaster.create") as mock_create:
        mock_broadcaster = AsyncMock(spec=RedisEventBroadcaster)
        mock_broadcaster.close = AsyncMock()
        mock_create.return_value = mock_broadcaster

        await get_redis_broadcaster()

        await reset_redis_broadcaster()

        mock_broadcaster.close.assert_called_once()

        mock_create.reset_mock()
        await get_redis_broadcaster()
        mock_create.assert_called_once()

        await reset_redis_broadcaster()
