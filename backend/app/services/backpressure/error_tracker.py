"""Sliding window error tracker for adaptive backpressure.

Tracks error rates over a configurable time window to enable
dynamic adjustments to batch sizes and retry strategies.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import NamedTuple

import structlog

logger = structlog.get_logger(__name__)

# Constants
RATE_LIMIT_BACKOFF_THRESHOLD = 3  # Number of rate limits to trigger backoff


class ErrorType(Enum):
    """Types of errors to track separately."""

    RATE_LIMIT = auto()  # 429 errors
    SERVER_ERROR = auto()  # 5xx errors
    TIMEOUT = auto()  # Request timeouts
    OTHER = auto()  # Other errors


class ErrorEvent(NamedTuple):
    """An error event with timestamp and type."""

    timestamp: float
    error_type: ErrorType
    status_code: int | None = None


@dataclass
class ErrorTracker:
    """Tracks error rates using a sliding time window.

    Provides error rate calculations for making adaptive decisions
    about batch sizes and retry strategies.

    Attributes:
        window_seconds: Time window for error rate calculation.
        threshold_percent: Error rate threshold for triggering backoff.
        name: Identifier for logging.

    """

    window_seconds: int = 60
    threshold_percent: float = 5.0
    name: str = "default"

    _errors: deque = field(default_factory=deque, repr=False)
    _successes: deque = field(default_factory=deque, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _cleanup_old_entries(self, current_time: float) -> None:
        """Remove entries outside the time window."""
        cutoff = current_time - self.window_seconds

        while self._errors and self._errors[0].timestamp < cutoff:
            self._errors.popleft()

        while self._successes and self._successes[0] < cutoff:
            self._successes.popleft()

    def record_success(self) -> None:
        """Record a successful request."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_old_entries(now)
            self._successes.append(now)

    def record_error(
        self,
        error_type: ErrorType,
        status_code: int | None = None,
    ) -> None:
        """Record an error.

        Args:
            error_type: Category of the error.
            status_code: HTTP status code if applicable.

        """
        now = time.monotonic()
        event = ErrorEvent(
            timestamp=now,
            error_type=error_type,
            status_code=status_code,
        )

        with self._lock:
            self._cleanup_old_entries(now)
            self._errors.append(event)

        logger.debug(
            "error_recorded",
            tracker=self.name,
            error_type=error_type.name,
            status_code=status_code,
        )

    def record_rate_limit(self) -> None:
        """Record a 429 rate limit error."""
        self.record_error(ErrorType.RATE_LIMIT, status_code=429)

    def record_server_error(self, status_code: int = 500) -> None:
        """Record a server error (5xx)."""
        self.record_error(ErrorType.SERVER_ERROR, status_code=status_code)

    def record_timeout(self) -> None:
        """Record a timeout error."""
        self.record_error(ErrorType.TIMEOUT)

    def get_error_rate(self) -> float:
        """Get the current error rate as a percentage.

        Returns:
            Error rate from 0.0 to 100.0.

        """
        now = time.monotonic()
        with self._lock:
            self._cleanup_old_entries(now)

            total = len(self._errors) + len(self._successes)
            if total == 0:
                return 0.0

            return (len(self._errors) / total) * 100.0

    def get_error_count_by_type(self) -> dict[str, int]:
        """Get error counts grouped by type."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_old_entries(now)

            counts: dict[str, int] = {}
            for error in self._errors:
                type_name = error.error_type.name
                counts[type_name] = counts.get(type_name, 0) + 1

            return counts

    def get_rate_limit_count(self) -> int:
        """Get the number of rate limit errors in the window."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_old_entries(now)
            return sum(1 for e in self._errors if e.error_type == ErrorType.RATE_LIMIT)

    def get_server_error_count(self) -> int:
        """Get the number of server errors in the window."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_old_entries(now)
            return sum(1 for e in self._errors if e.error_type == ErrorType.SERVER_ERROR)

    def is_threshold_exceeded(self) -> bool:
        """Check if error rate exceeds the threshold.

        Returns:
            True if error rate is above threshold_percent.

        """
        return self.get_error_rate() > self.threshold_percent

    def should_backoff(self) -> bool:
        """Determine if backoff is recommended.

        Returns True if:
        - Error rate exceeds threshold, OR
        - Recent rate limit errors detected
        """
        if self.is_threshold_exceeded():
            return True

        # Also backoff if we've hit multiple rate limits recently
        return self.get_rate_limit_count() >= RATE_LIMIT_BACKOFF_THRESHOLD

    def get_stats(self) -> dict:
        """Get comprehensive error statistics."""
        now = time.monotonic()
        with self._lock:
            self._cleanup_old_entries(now)

            error_count = len(self._errors)
            success_count = len(self._successes)
            total = error_count + success_count
            error_rate = (error_count / total * 100) if total > 0 else 0.0

            # Inline errors_by_type calculation to avoid nested lock
            errors_by_type: dict[str, int] = {}
            rate_limit_count = 0
            for error in self._errors:
                type_name = error.error_type.name
                errors_by_type[type_name] = errors_by_type.get(type_name, 0) + 1
                if error.error_type == ErrorType.RATE_LIMIT:
                    rate_limit_count += 1

            # Inline threshold/backoff checks to avoid nested locks
            threshold_exceeded = error_rate > self.threshold_percent
            should_backoff = threshold_exceeded or rate_limit_count >= RATE_LIMIT_BACKOFF_THRESHOLD

            return {
                "window_seconds": self.window_seconds,
                "threshold_percent": self.threshold_percent,
                "total_requests": total,
                "success_count": success_count,
                "error_count": error_count,
                "error_rate_percent": error_rate,
                "errors_by_type": errors_by_type,
                "threshold_exceeded": threshold_exceeded,
                "should_backoff": should_backoff,
            }

    def reset(self) -> None:
        """Clear all tracked errors and successes."""
        with self._lock:
            self._errors.clear()
            self._successes.clear()
            logger.debug("error_tracker_reset", tracker=self.name)
