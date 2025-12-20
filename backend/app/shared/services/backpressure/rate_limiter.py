"""Token bucket rate limiter for API request throttling.

Implements a token bucket algorithm that allows burst capacity
while enforcing average rate limits over time.
"""

from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

# Constants
MIN_WAIT_LOG_THRESHOLD = 0.01  # Minimum wait time in seconds to log


@dataclass
class RateLimiter:
    """Token bucket rate limiter.

    Provides smooth rate limiting with burst capacity support.
    Thread-safe for concurrent access.

    Attributes:
        tokens_per_minute: Maximum sustained rate.
        burst_capacity: Maximum tokens available for bursts.
        name: Identifier for logging.

    """

    tokens_per_minute: int = 10000
    burst_capacity: int = 2000
    name: str = "default"

    _tokens: float = field(init=False, repr=False)
    _last_refill: float = field(init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        """Initialize token bucket."""
        self._tokens = float(self.burst_capacity)
        self._last_refill = time.monotonic()

    @property
    def refill_rate(self) -> float:
        """Tokens added per second."""
        return self.tokens_per_minute / 60.0

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * self.refill_rate
        self._tokens = min(self._tokens + tokens_to_add, float(self.burst_capacity))
        self._last_refill = now

    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            True if tokens were acquired, False otherwise.

        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                self._tokens -= tokens
                return True

            logger.debug(
                "rate_limit_would_block",
                limiter=self.name,
                requested=tokens,
                available=self._tokens,
            )
            return False

    def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, blocking if necessary.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            Time waited in seconds.

        """
        start = time.monotonic()

        with self._lock:
            self._refill()

            while self._tokens < tokens:
                # Calculate wait time
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.refill_rate

                # Release lock while waiting
                self._lock.release()
                try:
                    time.sleep(wait_time)
                finally:
                    self._lock.acquire()

                self._refill()

            self._tokens -= tokens

        waited = time.monotonic() - start
        if waited > MIN_WAIT_LOG_THRESHOLD:
            logger.debug(
                "rate_limit_waited",
                limiter=self.name,
                tokens=tokens,
                waited_ms=waited * 1000,
            )
        return waited

    async def acquire_async(self, tokens: int = 1) -> float:
        """Async version of acquire.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            Time waited in seconds.

        """
        start = time.monotonic()

        with self._lock:
            self._refill()

            while self._tokens < tokens:
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.refill_rate

                self._lock.release()
                try:
                    await asyncio.sleep(wait_time)
                finally:
                    self._lock.acquire()

                self._refill()

            self._tokens -= tokens

        waited = time.monotonic() - start
        if waited > MIN_WAIT_LOG_THRESHOLD:
            logger.debug(
                "rate_limit_waited_async",
                limiter=self.name,
                tokens=tokens,
                waited_ms=waited * 1000,
            )
        return waited

    def get_available_tokens(self) -> float:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return self._tokens

    def get_wait_time(self, tokens: int = 1) -> float:
        """Estimate wait time to acquire tokens.

        Args:
            tokens: Number of tokens needed.

        Returns:
            Estimated wait time in seconds, 0 if no wait needed.

        """
        with self._lock:
            self._refill()

            if self._tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self._tokens
            return tokens_needed / self.refill_rate

    def reset(self) -> None:
        """Reset the rate limiter to full capacity."""
        with self._lock:
            self._tokens = float(self.burst_capacity)
            self._last_refill = time.monotonic()
            logger.debug("rate_limiter_reset", limiter=self.name)
