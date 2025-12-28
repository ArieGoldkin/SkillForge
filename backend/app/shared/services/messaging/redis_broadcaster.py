"""Redis-backed event broadcaster for distributed pub/sub messaging.

Issue #444: Implements Redis Pub/Sub to solve the multi-instance problem where
in-memory EventBroadcaster doesn't share events across backend replicas.

Architecture:
    ┌─────────────┐        ┌─────────────┐
    │ Instance A  │        │ Instance B  │
    │             │        │             │
    │ POST /analyze        │ GET /stream │
    │     ↓       │        │     ↓       │
    │ publish()   │───────→│ subscribe() │
    │     │       │  Redis │     ↓       │
    │     │       │  Pub/Sub│ yield events│
    │     ↓       │        │             │
    │ buffer in   │───────→│ replay      │
    │ Redis List  │        │ from List   │
    └─────────────┘        └─────────────┘

Features:
    - Redis Pub/Sub for real-time event delivery across instances
    - Redis List for event buffering (late-joiner replay)
    - Configurable TTL for buffered events
    - Graceful fallback to in-memory broadcaster if Redis unavailable
    - Compatible with existing EventBroadcaster interface
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.exceptions import CacheError
from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from redis.asyncio.client import PubSub

    from app.core.types import ChannelName, EventData

logger = get_logger(__name__)

# Buffer configuration
REDIS_BUFFER_TTL_SECONDS = 300  # 5 minutes - matches in-memory broadcaster
REDIS_BUFFER_MAX_SIZE = 100  # Max events per channel - matches in-memory broadcaster


class RedisEventBroadcaster:
    """Redis-backed pub/sub broadcaster for SSE events.

    Replaces in-memory EventBroadcaster for multi-instance deployments.
    Uses Redis Pub/Sub for real-time events and Redis Lists for buffering.

    Attributes:
        _redis: Async Redis client
        _pubsub_connections: Active PubSub connections per channel
        _connected: Whether Redis connection is established

    Example:
        ```python
        from contextlib import aclosing

        broadcaster = await RedisEventBroadcaster.create()

        # Subscribe to channel - receives buffered events first
        async with aclosing(broadcaster.subscribe("workflow:123")) as events:
            async for event in events:
                print(event)

        # Publish to channel (from another coroutine)
        await broadcaster.publish("workflow:123", {"type": "progress"})
        ```

    """

    def __init__(self, redis_client: aioredis.Redis) -> None:
        """Initialize with existing Redis client.

        Use RedisEventBroadcaster.create() factory method instead.
        """
        self._redis = redis_client
        self._connected = True

    @classmethod
    async def create(cls, redis_url: str | None = None) -> RedisEventBroadcaster:
        """Create Redis broadcaster with connection validation.

        Args:
            redis_url: Redis connection URL (defaults to settings.REDIS_URL)

        Returns:
            Initialized RedisEventBroadcaster

        Raises:
            ConnectionError: If Redis connection fails

        """
        settings = get_settings()
        url = redis_url or settings.REDIS_URL

        try:
            # Create async Redis client with connection pool and keepalive
            # Issue #442: Add socket_keepalive for long-lived SSE pubsub connections
            # Without keepalive, OS/firewall drops idle connections after ~5 min
            client = aioredis.from_url(
                url,
                decode_responses=True,  # Return strings, not bytes
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_keepalive=settings.REDIS_SOCKET_KEEPALIVE,
                health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
            )

            # Verify connection
            await client.ping()

            logger.info(
                "redis_broadcaster_connected",
                redis_url=url.split("@")[-1],  # Hide credentials
            )

            return cls(client)

        except (OSError, ConnectionRefusedError, TimeoutError) as e:
            logger.exception(
                "redis_broadcaster_connection_failed",
                error=str(e),
                redis_url=url.split("@")[-1],
            )
            msg = f"Failed to connect to Redis: {e}"
            raise ConnectionError(msg) from e

    async def publish(self, channel: ChannelName, message: EventData) -> None:
        """Publish message to Redis Pub/Sub and buffer for late-joiners.

        Events are:
        1. Published to Redis Pub/Sub (real-time delivery to subscribers)
        2. Added to Redis List (buffer for late-joining subscribers)

        Args:
            channel: Channel name (e.g., "workflow:{analysis_id}")
            message: Message dictionary to broadcast

        """
        buffer_key = f"buffer:{channel}"
        now = datetime.now(UTC).isoformat()

        # Add timestamp for ordering
        buffered_message = {**message, "_buffered_at": now}
        message_json = json.dumps(buffered_message)

        try:
            # Use pipeline for atomic operations
            async with self._redis.pipeline() as pipe:
                # 1. Add to buffer list (for late-joiners)
                pipe.rpush(buffer_key, message_json)
                # 2. Trim buffer to max size (keep newest)
                pipe.ltrim(buffer_key, -REDIS_BUFFER_MAX_SIZE, -1)
                # 3. Set/refresh TTL
                pipe.expire(buffer_key, REDIS_BUFFER_TTL_SECONDS)
                # 4. Publish to Pub/Sub (real-time)
                pipe.publish(channel, message_json)

                results = await pipe.execute()

            buffer_size = results[0]  # rpush returns new length
            subscribers = results[3]  # publish returns number of subscribers

            if subscribers == 0:
                logger.debug(
                    "redis_publish_buffered_no_subscribers",
                    channel=channel,
                    buffer_size=buffer_size,
                )
            else:
                logger.debug(
                    "redis_publish_success",
                    channel=channel,
                    subscribers=subscribers,
                    buffer_size=buffer_size,
                )

        except Exception as e:
            logger.error(
                "redis_publish_failed",
                channel=channel,
                error=str(e),
                exc_info=True,
            )
            msg = f"Failed to publish to Redis channel '{channel}': {e}"
            raise CacheError(msg) from e

    async def subscribe(self, channel: ChannelName) -> AsyncIterator[EventData]:  # noqa: PLR0912
        """Subscribe to channel with buffer replay.

        Yields events in order:
        1. All buffered events (from Redis List)
        2. Live events (from Redis Pub/Sub)

        Args:
            channel: Channel name to subscribe to

        Yields:
            Message dictionaries published to the channel

        """
        buffer_key = f"buffer:{channel}"
        pubsub: PubSub | None = None

        try:
            # First, subscribe to Pub/Sub (before reading buffer to avoid race condition)
            pubsub = self._redis.pubsub()
            await pubsub.subscribe(channel)

            logger.debug(
                "redis_subscribe_created",
                channel=channel,
            )

            # Replay buffered events
            try:
                buffered = await self._redis.lrange(buffer_key, 0, -1)  # type: ignore[misc]
                buffered_count = len(buffered)

                for event_json in buffered:
                    try:
                        event = json.loads(event_json)
                        # Remove internal timestamp before yielding
                        event.pop("_buffered_at", None)
                        yield event
                    except json.JSONDecodeError:
                        logger.warning(
                            "redis_buffer_invalid_json",
                            channel=channel,
                            raw_event=event_json[:100],
                        )
                        continue

                if buffered_count > 0:
                    logger.debug(
                        "redis_subscribe_buffer_replayed",
                        channel=channel,
                        events_replayed=buffered_count,
                    )

            except Exception as e:  # noqa: BLE001 - Cache failures must not block operations
                logger.debug(
                    "cache_operation_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    operation="buffer_read",
                    channel=channel,
                )
                logger.warning(
                    "redis_buffer_read_failed",
                    channel=channel,
                    error=str(e),
                )
                # Continue with live events even if buffer read fails

            # Yield live events from Pub/Sub
            # Issue #442: Handle read timeouts gracefully - idle periods are normal during analysis
            while True:
                try:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True,
                        timeout=30.0,  # 30 second timeout, then check for cancellation
                    )
                    if message is None:
                        # Timeout - no message received, continue waiting
                        continue
                    if message["type"] == "message":
                        try:
                            event = json.loads(message["data"])
                            # Remove internal timestamp before yielding
                            event.pop("_buffered_at", None)
                            yield event
                        except json.JSONDecodeError:
                            logger.warning(
                                "redis_pubsub_invalid_json",
                                channel=channel,
                                data=str(message["data"])[:100],
                            )
                            continue
                except TimeoutError:
                    # Redis timeout - continue listening (idle periods are normal)
                    continue

        except asyncio.CancelledError:
            logger.debug("redis_subscribe_cancelled", channel=channel)
            raise

        finally:
            # Cleanup: unsubscribe and close pubsub
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel)
                    await pubsub.close()
                except Exception as e:  # noqa: BLE001 - Cache failures must not block operations
                    logger.debug(
                        "cache_operation_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                        operation="pubsub_cleanup",
                        channel=channel,
                    )
                    logger.warning(
                        "redis_pubsub_cleanup_error",
                        channel=channel,
                        error=str(e),
                    )

            logger.debug("redis_subscribe_cleaned", channel=channel)

    def get_subscriber_count(self, channel: ChannelName) -> int:  # noqa: ARG002
        """Get number of active subscribers for a channel.

        Note: This is a sync method for API compatibility with in-memory broadcaster.
        For Redis, this would require an async call, so we return 0 as a placeholder.
        Use async `get_subscriber_count_async()` for accurate counts.

        Args:
            channel: Channel name (unused - required for interface compatibility)

        Returns:
            Always returns 0 (use async version for accurate count)

        """
        return 0  # Sync API compatibility - use async version for accurate count

    async def get_subscriber_count_async(self, channel: ChannelName) -> int:
        """Get number of active subscribers for a channel (async).

        Uses Redis PUBSUB NUMSUB command.

        Args:
            channel: Channel name

        Returns:
            Number of active subscribers

        """
        try:
            result = await self._redis.pubsub_numsub(channel)
            # PUBSUB NUMSUB returns list of (channel, count) tuples
            if result:
                return int(result[0][1])
            return 0
        except Exception as e:  # noqa: BLE001 - Cache failures must not block operations
            logger.debug(
                "cache_operation_failed",
                error=str(e),
                error_type=type(e).__name__,
                operation="subscriber_count",
                channel=channel,
            )
            logger.warning(
                "redis_subscriber_count_failed",
                channel=channel,
                error=str(e),
            )
            return 0

    async def clear_buffer(self, channel: ChannelName) -> None:
        """Clear the event buffer for a channel.

        Call this when an analysis is complete to free Redis memory.

        Args:
            channel: Channel name to clear buffer for

        """
        buffer_key = f"buffer:{channel}"
        try:
            deleted = await self._redis.delete(buffer_key)
            if deleted:
                logger.debug(
                    "redis_buffer_cleared",
                    channel=channel,
                )
        except Exception as e:  # noqa: BLE001 - Cache failures must not block operations
            logger.debug(
                "cache_operation_failed",
                error=str(e),
                error_type=type(e).__name__,
                operation="buffer_clear",
                channel=channel,
            )
            logger.warning(
                "redis_buffer_clear_failed",
                channel=channel,
                error=str(e),
            )

    async def close(self) -> None:
        """Close Redis connection."""
        try:
            await self._redis.aclose()
            self._connected = False
            logger.info("redis_broadcaster_closed")
        except Exception as e:  # noqa: BLE001 - Cache failures must not block operations
            logger.debug(
                "cache_operation_failed",
                error=str(e),
                error_type=type(e).__name__,
                operation="close",
            )
            logger.warning(
                "redis_broadcaster_close_error",
                error=str(e),
            )


# Singleton instance (initialized lazily)
_redis_broadcaster: RedisEventBroadcaster | None = None
_broadcaster_lock = asyncio.Lock()


async def get_redis_broadcaster() -> RedisEventBroadcaster:
    """Get or create singleton Redis broadcaster instance.

    Thread-safe lazy initialization of the global Redis broadcaster.

    Returns:
        RedisEventBroadcaster instance

    Raises:
        ConnectionError: If Redis connection fails

    """
    global _redis_broadcaster  # noqa: PLW0603 - Singleton pattern

    if _redis_broadcaster is not None:
        return _redis_broadcaster

    async with _broadcaster_lock:
        # Double-check after acquiring lock
        if _redis_broadcaster is not None:
            return _redis_broadcaster

        _redis_broadcaster = await RedisEventBroadcaster.create()
        return _redis_broadcaster


async def reset_redis_broadcaster() -> None:
    """Reset the singleton broadcaster instance.

    Useful for testing or reconnection scenarios.
    """
    global _redis_broadcaster  # noqa: PLW0603 - Singleton pattern

    async with _broadcaster_lock:
        if _redis_broadcaster is not None:
            await _redis_broadcaster.close()
            _redis_broadcaster = None
