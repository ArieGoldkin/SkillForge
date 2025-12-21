"""Broadcaster factory for dynamic backend selection.

Issue #444: Factory pattern to support both in-memory and Redis broadcasters
with graceful fallback for production deployments.

Architecture:
    ┌──────────────────┐
    │ get_broadcaster()│
    │                  │
    │  [auto mode]     │
    │      │           │
    │      ├──→ Try Redis first
    │      │    ├─→ Success: Return RedisEventBroadcaster
    │      │    └─→ Failed: Log warning, fallback to in-memory
    │      │
    │  [redis mode]    │
    │      └──→ Require Redis (raise on failure)
    │
    │  [memory mode]   │
    │      └──→ Return EventBroadcaster
    └──────────────────┘

Usage:
    ```python
    from app.shared.services.messaging.broadcaster_factory import (
        get_broadcaster,
        BroadcasterBackend,
    )

    # Auto mode (recommended for production)
    broadcaster = await get_broadcaster(BroadcasterBackend.AUTO)

    # Explicit backend selection
    broadcaster = await get_broadcaster(BroadcasterBackend.REDIS)

    # In-memory only (development)
    broadcaster = await get_broadcaster(BroadcasterBackend.MEMORY)
    ```

"""

from __future__ import annotations

import asyncio
from enum import Enum
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.core.types import ChannelName, EventData

logger = get_logger(__name__)


class BroadcasterBackend(str, Enum):
    """Broadcaster backend type."""

    MEMORY = "memory"
    REDIS = "redis"
    AUTO = "auto"  # Try Redis first, fallback to in-memory


@runtime_checkable
class BroadcasterProtocol(Protocol):
    """Protocol for broadcaster interface compatibility.

    Both EventBroadcaster and RedisEventBroadcaster must implement this interface.
    """

    async def publish(self, channel: ChannelName, message: EventData) -> None:
        """Publish message to channel."""
        ...

    async def subscribe(self, channel: ChannelName) -> AsyncIterator[EventData]:
        """Subscribe to channel and yield messages."""
        ...

    def get_subscriber_count(self, channel: ChannelName) -> int:
        """Get number of active subscribers for a channel."""
        ...

    async def clear_buffer(self, channel: ChannelName) -> None:
        """Clear the event buffer for a channel."""
        ...


# Singleton instance
_broadcaster: BroadcasterProtocol | None = None
_broadcaster_backend: BroadcasterBackend | None = None
_broadcaster_lock = asyncio.Lock()


async def get_broadcaster(
    backend: BroadcasterBackend = BroadcasterBackend.AUTO,
) -> BroadcasterProtocol:
    """Get or create singleton broadcaster instance.

    Thread-safe lazy initialization with configurable backend.

    Args:
        backend: Broadcaster backend type (auto, redis, memory)

    Returns:
        Broadcaster instance (EventBroadcaster or RedisEventBroadcaster)

    Raises:
        ConnectionError: If redis backend is explicitly requested but unavailable
        ValueError: If backend type is invalid

    Examples:
        ```python
        # Production: Auto-fallback from Redis to in-memory
        broadcaster = await get_broadcaster(BroadcasterBackend.AUTO)

        # Development: Force in-memory
        broadcaster = await get_broadcaster(BroadcasterBackend.MEMORY)

        # Production: Require Redis (fail if unavailable)
        broadcaster = await get_broadcaster(BroadcasterBackend.REDIS)
        ```

    """
    global _broadcaster, _broadcaster_backend  # noqa: PLW0603 - Singleton pattern

    # If already initialized with the same backend, return existing instance
    if _broadcaster is not None and _broadcaster_backend == backend:
        logger.debug(
            "broadcaster_factory_reuse",
            backend=backend.value,
        )
        return _broadcaster

    async with _broadcaster_lock:
        # Double-check after acquiring lock
        if _broadcaster is not None and _broadcaster_backend == backend:
            return _broadcaster

        # Backend changed - log the switch
        if _broadcaster_backend is not None and _broadcaster_backend != backend:
            logger.info(
                "broadcaster_factory_backend_switch",
                from_backend=_broadcaster_backend.value,
                to_backend=backend.value,
            )

        logger.info(
            "broadcaster_factory_initialize",
            backend=backend.value,
        )

        # Initialize based on backend type
        if backend == BroadcasterBackend.MEMORY:
            _broadcaster = _create_memory_broadcaster()
            _broadcaster_backend = BroadcasterBackend.MEMORY

        elif backend == BroadcasterBackend.REDIS:
            _broadcaster = await _create_redis_broadcaster(required=True)
            _broadcaster_backend = BroadcasterBackend.REDIS

        elif backend == BroadcasterBackend.AUTO:
            # Try Redis first, fallback to in-memory
            try:
                _broadcaster = await _create_redis_broadcaster(required=False)
                _broadcaster_backend = BroadcasterBackend.REDIS
                logger.info(
                    "broadcaster_factory_auto_selected_redis",
                    backend="redis",
                )
            except Exception as e:  # noqa: BLE001 - Fallback to memory on any error
                logger.warning(
                    "broadcaster_factory_redis_unavailable_fallback",
                    error=str(e),
                    fallback="memory",
                )
                _broadcaster = _create_memory_broadcaster()
                _broadcaster_backend = BroadcasterBackend.MEMORY

        else:
            msg = f"Invalid broadcaster backend: {backend}"
            raise ValueError(msg)

        logger.info(
            "broadcaster_factory_initialized",
            backend=_broadcaster_backend.value,
            broadcaster_type=type(_broadcaster).__name__,
        )

        return _broadcaster


def _create_memory_broadcaster() -> BroadcasterProtocol:
    """Create in-memory broadcaster instance.

    Returns:
        EventBroadcaster instance

    """
    from app.shared.services.messaging.broadcaster import EventBroadcaster

    logger.debug("broadcaster_factory_create_memory")
    return EventBroadcaster()  # type: ignore[return-value]


async def _create_redis_broadcaster(*, required: bool = True) -> BroadcasterProtocol:
    """Create Redis broadcaster instance.

    Args:
        required: If True, raise exception on connection failure.
                  If False, allow exception to propagate for fallback handling.

    Returns:
        RedisEventBroadcaster instance

    Raises:
        ConnectionError: If Redis connection fails and required=True

    """
    from app.shared.services.messaging.redis_broadcaster import RedisEventBroadcaster

    try:
        logger.debug("broadcaster_factory_create_redis")
        return await RedisEventBroadcaster.create()  # type: ignore[return-value]
    except (OSError, ConnectionError, TimeoutError) as e:
        logger.exception(
            "broadcaster_factory_redis_failed",
            error=str(e),
            required=required,
        )

        if required:
            msg = f"Redis broadcaster required but unavailable: {e}"
            raise ConnectionError(msg) from e

        # Re-raise for auto-mode fallback handling
        raise


async def reset_broadcaster() -> None:
    """Reset the singleton broadcaster instance.

    Useful for testing or when switching backends at runtime.
    Closes Redis connections if applicable.

    """
    global _broadcaster, _broadcaster_backend  # noqa: PLW0603 - Singleton pattern

    async with _broadcaster_lock:
        if _broadcaster is not None:
            logger.info(
                "broadcaster_factory_reset",
                previous_backend=_broadcaster_backend.value if _broadcaster_backend else "none",
            )

            # Close Redis connection if applicable
            if hasattr(_broadcaster, "close") and callable(_broadcaster.close):
                try:
                    await _broadcaster.close()  # type: ignore[misc]
                except Exception as e:  # noqa: BLE001 - Cleanup must not fail
                    logger.warning(
                        "broadcaster_factory_reset_close_error",
                        error=str(e),
                    )

            _broadcaster = None
            _broadcaster_backend = None


def get_current_backend() -> BroadcasterBackend | None:
    """Get the currently initialized broadcaster backend.

    Returns:
        Current backend type or None if not initialized

    """
    return _broadcaster_backend


async def health_check() -> dict[str, bool | str]:
    """Check health of current broadcaster.

    Returns:
        Dictionary with health status and backend type

    Example:
        ```python
        {"healthy": true, "backend": "redis", "details": "Redis connection active"}
        ```

    """
    if _broadcaster is None:
        return {
            "healthy": False,
            "backend": "none",
            "details": "Broadcaster not initialized",
        }

    backend = _broadcaster_backend.value if _broadcaster_backend else "unknown"

    # For Redis, try to ping
    if _broadcaster_backend == BroadcasterBackend.REDIS and hasattr(_broadcaster, "_redis"):
        try:
            await _broadcaster._redis.ping()  # type: ignore[attr-defined]
            return {
                "healthy": True,
                "backend": backend,
                "details": "Redis connection active",
            }
        except Exception as e:  # noqa: BLE001 - Health check catches all errors
            return {
                "healthy": False,
                "backend": backend,
                "details": f"Redis connection failed: {e}",
            }

    # For in-memory, always healthy
    return {
        "healthy": True,
        "backend": backend,
        "details": "In-memory broadcaster active",
    }
