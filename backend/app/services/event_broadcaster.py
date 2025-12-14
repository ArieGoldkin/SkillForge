"""Event broadcaster service for pub/sub messaging.

Provides in-memory pub/sub functionality for SSE events using asyncio.Queue.
Channels are keyed by string identifiers (e.g., "workflow:{analysis_id}").

Issue #SSE-RACE: Added event buffering to solve the race condition where
events are published before subscribers connect. Recent events are buffered
per channel and replayed to new subscribers.
"""

import asyncio
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.core.types import ChannelName, EventData

logger = get_logger(__name__)

# Buffer configuration
MAX_BUFFER_SIZE = 100  # Max events to buffer per channel
BUFFER_TTL_SECONDS = 300  # 5 minutes - events older than this are dropped


class EventBroadcaster:
    """In-memory pub/sub broadcaster for SSE events with event buffering.

    Manages channels and subscribers using asyncio.Queue. Each channel can have
    multiple subscribers, and messages published to a channel are delivered to
    all active subscribers.

    Issue #SSE-RACE: Implements event buffering to solve race condition where
    workflow starts emitting events before frontend SSE connection is established.
    Recent events are buffered per channel and replayed to new subscribers.

    Attributes:
        _channels: Dictionary mapping channel names to lists of queues
        _buffers: Dictionary mapping channel names to buffered events (deque)

    Example:
        ```python
        broadcaster = EventBroadcaster()

        # Subscribe to channel - receives buffered events first
        async for event in broadcaster.subscribe("workflow:123"):
            print(event)

        # Publish to channel (from another coroutine)
        await broadcaster.publish("workflow:123", {"type": "progress"})
        ```

    """

    def __init__(self) -> None:
        """Initialize event broadcaster with empty channels and buffers."""
        self._channels: dict[ChannelName, list[asyncio.Queue[EventData]]] = defaultdict(list)
        self._buffers: dict[ChannelName, deque[tuple[datetime, EventData]]] = defaultdict(
            lambda: deque(maxlen=MAX_BUFFER_SIZE)
        )
        self._lock = asyncio.Lock()

    async def publish(self, channel: ChannelName, message: EventData) -> None:
        """Publish message to all subscribers of a channel.

        Issue #SSE-RACE: Events are now buffered for late-joining subscribers.
        Even if no subscribers exist, events are stored in the buffer.

        Args:
            channel: Channel name (e.g., "workflow:{analysis_id}")
            message: Message dictionary to broadcast

        """
        now = datetime.now(UTC)

        async with self._lock:
            queues = self._channels.get(channel, [])

            # Always buffer the event (even if no subscribers)
            # This solves the race condition where workflow starts before SSE connects
            self._buffers[channel].append((now, message))

            # Clean up old events from buffer (older than TTL)
            cutoff = now - timedelta(seconds=BUFFER_TTL_SECONDS)
            while self._buffers[channel] and self._buffers[channel][0][0] < cutoff:
                self._buffers[channel].popleft()

        if not queues:
            logger.debug(
                "publish_buffered_no_subscribers",
                channel=channel,
                buffer_size=len(self._buffers[channel]),
            )
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
            buffer_size=len(self._buffers[channel]),
        )

    async def subscribe(self, channel: ChannelName) -> AsyncIterator[EventData]:
        """Subscribe to a channel and yield messages.

        Issue #SSE-RACE: New subscribers first receive all buffered events
        (events published before the subscriber connected), then receive
        live events as they are published.

        Creates a new queue for this subscriber and yields messages as they
        are published. Automatically cleans up the queue when the subscription
        ends (client disconnect, generator exit, etc.).

        Args:
            channel: Channel name to subscribe to

        Yields:
            Message dictionaries published to the channel

        """
        queue: asyncio.Queue[EventData] = asyncio.Queue()
        buffered_events: list[EventData] = []

        # Add queue to channel subscribers and capture buffered events
        async with self._lock:
            self._channels[channel].append(queue)

            # Capture buffered events for replay (copy to avoid mutation during iteration)
            if channel in self._buffers:
                buffered_events = [event for _, event in self._buffers[channel]]

        logger.debug(
            "subscribe_created",
            channel=channel,
            buffered_events_count=len(buffered_events),
        )

        try:
            # First, replay all buffered events to catch up the subscriber
            for event in buffered_events:
                yield event

            if buffered_events:
                logger.debug(
                    "subscribe_buffer_replayed",
                    channel=channel,
                    events_replayed=len(buffered_events),
                )

            # Then, yield live events as they arrive
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

    def get_subscriber_count(self, channel: ChannelName) -> int:
        """Get number of active subscribers for a channel.

        Args:
            channel: Channel name

        Returns:
            Number of active subscribers

        """
        return len(self._channels.get(channel, []))

    async def clear_buffer(self, channel: ChannelName) -> None:
        """Clear the event buffer for a channel.

        Call this when an analysis is complete to free memory.
        The buffer is automatically size-limited, but explicit clearing
        helps with cleanup after workflow completion.

        Args:
            channel: Channel name to clear buffer for

        """
        async with self._lock:
            if channel in self._buffers:
                cleared_count = len(self._buffers[channel])
                del self._buffers[channel]
                logger.debug(
                    "buffer_cleared",
                    channel=channel,
                    events_cleared=cleared_count,
                )


# Global broadcaster instance
broadcaster = EventBroadcaster()
