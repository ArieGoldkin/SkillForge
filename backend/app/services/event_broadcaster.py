"""Event broadcaster service for pub/sub messaging.

Provides in-memory pub/sub functionality for SSE events using asyncio.Queue.
Channels are keyed by string identifiers (e.g., "workflow:{analysis_id}").
"""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import suppress

from app.core.logging import get_logger

logger = get_logger(__name__)


class EventBroadcaster:
    """In-memory pub/sub broadcaster for SSE events.

    Manages channels and subscribers using asyncio.Queue. Each channel can have
    multiple subscribers, and messages published to a channel are delivered to
    all active subscribers.

    Attributes:
        _channels: Dictionary mapping channel names to lists of queues

    Example:
        ```python
        broadcaster = EventBroadcaster()

        # Subscribe to channel
        async for event in broadcaster.subscribe("workflow:123"):
            print(event)

        # Publish to channel (from another coroutine)
        await broadcaster.publish("workflow:123", {"type": "progress"})
        ```

    """

    def __init__(self) -> None:
        """Initialize event broadcaster with empty channels."""
        self._channels: dict[str, list[asyncio.Queue[dict[str, object]]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, channel: str, message: dict[str, object]) -> None:
        """Publish message to all subscribers of a channel.

        Args:
            channel: Channel name (e.g., "workflow:{analysis_id}")
            message: Message dictionary to broadcast

        """
        async with self._lock:
            queues = self._channels.get(channel, [])

        if not queues:
            logger.debug("publish_no_subscribers", channel=channel)
            return

        # Broadcast to all subscribers
        for queue in queues:
            try:
                await queue.put(message)
            except (asyncio.CancelledError, RuntimeError) as e:
                logger.warning(
                    "publish_failed",
                    channel=channel,
                    error=str(e),
                    exc_info=True,
                )

        logger.debug(
            "publish_success",
            channel=channel,
            subscribers=len(queues),
        )

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, object]]:
        """Subscribe to a channel and yield messages.

        Creates a new queue for this subscriber and yields messages as they
        are published. Automatically cleans up the queue when the subscription
        ends (client disconnect, generator exit, etc.).

        Args:
            channel: Channel name to subscribe to

        Yields:
            Message dictionaries published to the channel

        """
        queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

        # Add queue to channel subscribers
        async with self._lock:
            self._channels[channel].append(queue)

        logger.debug("subscribe_created", channel=channel)

        try:
            while True:
                message = await queue.get()
                yield message
        except asyncio.CancelledError:
            logger.debug("subscribe_cancelled", channel=channel)
            raise
        finally:
            # Cleanup: remove queue from subscribers
            async with self._lock:
                if channel in self._channels:
                    with suppress(ValueError):
                        self._channels[channel].remove(queue)

                    # Clean up empty channels
                    if not self._channels[channel]:
                        del self._channels[channel]

            logger.debug("subscribe_cleaned", channel=channel)

    def get_subscriber_count(self, channel: str) -> int:
        """Get number of active subscribers for a channel.

        Args:
            channel: Channel name

        Returns:
            Number of active subscribers

        """
        return len(self._channels.get(channel, []))


# Global broadcaster instance
broadcaster = EventBroadcaster()
