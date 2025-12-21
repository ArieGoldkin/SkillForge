"""Adaptive batch sizer for dynamic throughput optimization.

Adjusts batch sizes based on error rates and API feedback
to maximize throughput while avoiding rate limits.
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.shared.services.backpressure.error_tracker import ErrorTracker

logger = structlog.get_logger(__name__)


@dataclass
class AdaptiveBatchSizer:
    """Dynamically adjusts batch sizes based on error feedback.

    Uses error tracker feedback to:
    - Decrease batch size on 429/5xx errors
    - Gradually increase batch size during healthy periods

    Attributes:
        initial_size: Starting batch size.
        min_size: Minimum allowed batch size.
        max_size: Maximum allowed batch size.
        decrease_factor_429: Multiplier on 429 error (e.g., 0.5 = halve).
        decrease_factor_5xx: Multiplier on 5xx error (e.g., 0.75 = reduce by 25%).
        increase_factor: Multiplier when healthy (e.g., 1.1 = increase by 10%).
        cooldown_seconds: Time between size adjustments.
        healthy_window_seconds: Time with low errors before increasing.
        name: Identifier for logging.

    """

    initial_size: int = 20
    min_size: int = 1
    max_size: int = 100
    decrease_factor_429: float = 0.5
    decrease_factor_5xx: float = 0.75
    increase_factor: float = 1.1
    cooldown_seconds: float = 30.0
    healthy_window_seconds: float = 300.0  # 5 minutes
    name: str = "default"

    _current_size: int = field(init=False, repr=False)
    _last_decrease_time: float = field(init=False, repr=False)
    _last_increase_time: float = field(init=False, repr=False)
    _healthy_since: float | None = field(init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        """Initialize batch sizer state."""
        self._current_size = self.initial_size
        self._last_decrease_time = 0.0
        self._last_increase_time = 0.0
        self._healthy_since = time.monotonic()

    @property
    def current_size(self) -> int:
        """Get current batch size."""
        with self._lock:
            return self._current_size

    def decrease_for_rate_limit(self) -> int:
        """Decrease batch size due to rate limit (429).

        Returns:
            New batch size.

        """
        return self._decrease(self.decrease_factor_429, reason="rate_limit")

    def decrease_for_server_error(self) -> int:
        """Decrease batch size due to server error (5xx).

        Returns:
            New batch size.

        """
        return self._decrease(self.decrease_factor_5xx, reason="server_error")

    def _decrease(self, factor: float, reason: str) -> int:
        """Decrease batch size by the given factor.

        Args:
            factor: Multiplier to apply (0.0-1.0).
            reason: Reason for decrease (for logging).

        Returns:
            New batch size.

        """
        now = time.monotonic()

        with self._lock:
            # Check cooldown
            if now - self._last_decrease_time < self.cooldown_seconds:
                logger.debug(
                    "batch_decrease_cooldown",
                    sizer=self.name,
                    current_size=self._current_size,
                    seconds_remaining=self.cooldown_seconds - (now - self._last_decrease_time),
                )
                return self._current_size

            old_size = self._current_size
            new_size = max(self.min_size, int(self._current_size * factor))
            self._current_size = new_size
            self._last_decrease_time = now
            self._healthy_since = None  # Reset healthy tracking

        logger.info(
            "batch_size_decreased",
            sizer=self.name,
            reason=reason,
            old_size=old_size,
            new_size=new_size,
            factor=factor,
        )

        return new_size

    def try_increase(self, error_tracker: ErrorTracker | None = None) -> int:
        """Try to increase batch size if conditions are healthy.

        Only increases if:
        - Error rate is below threshold
        - Sufficient time has passed since last increase
        - Has been healthy for healthy_window_seconds

        Args:
            error_tracker: Optional tracker to check error rate.

        Returns:
            New batch size (may be unchanged).

        """
        now = time.monotonic()

        with self._lock:
            # Check if already at max
            if self._current_size >= self.max_size:
                return self._current_size

            # Check cooldown
            if now - self._last_increase_time < self.cooldown_seconds:
                return self._current_size

            # Check error tracker
            if error_tracker and error_tracker.should_backoff():
                self._healthy_since = None
                return self._current_size

            # Initialize healthy tracking if needed
            if self._healthy_since is None:
                self._healthy_since = now
                return self._current_size

            # Check if healthy long enough
            healthy_duration = now - self._healthy_since
            if healthy_duration < self.healthy_window_seconds:
                return self._current_size

            # Apply increase with jitter (prevent synchronized increases)
            jitter = random.uniform(0.95, 1.05)
            old_size = self._current_size
            new_size = min(
                self.max_size,
                int(self._current_size * self.increase_factor * jitter),
            )

            # Only update if actually increasing
            if new_size > self._current_size:
                self._current_size = new_size
                self._last_increase_time = now

                logger.info(
                    "batch_size_increased",
                    sizer=self.name,
                    old_size=old_size,
                    new_size=new_size,
                    healthy_duration_seconds=healthy_duration,
                )

        return self._current_size

    def get_next_batch_size(self, items_remaining: int) -> int:
        """Get the batch size for the next batch.

        Args:
            items_remaining: Number of items left to process.

        Returns:
            Recommended batch size.

        """
        with self._lock:
            return min(self._current_size, items_remaining)

    def reset(self) -> None:
        """Reset to initial batch size."""
        with self._lock:
            old_size = self._current_size
            self._current_size = self.initial_size
            self._last_decrease_time = 0.0
            self._last_increase_time = 0.0
            self._healthy_since = time.monotonic()

        logger.info(
            "batch_sizer_reset",
            sizer=self.name,
            old_size=old_size,
            new_size=self.initial_size,
        )

    def get_stats(self) -> dict:
        """Get batch sizer statistics."""
        now = time.monotonic()
        with self._lock:
            healthy_duration = (now - self._healthy_since) if self._healthy_since else None

            return {
                "name": self.name,
                "current_size": self._current_size,
                "initial_size": self.initial_size,
                "min_size": self.min_size,
                "max_size": self.max_size,
                "at_minimum": self._current_size == self.min_size,
                "at_maximum": self._current_size == self.max_size,
                "healthy_duration_seconds": healthy_duration,
                "seconds_since_last_decrease": now - self._last_decrease_time,
                "seconds_since_last_increase": now - self._last_increase_time,
            }
