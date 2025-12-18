"""Metric collector classes for counters and histograms.

Provides thread-safe metric collection with in-memory aggregation
for percentile calculations (p50, p95, p99).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class Counter:
    """Thread-safe counter metric.

    Tracks total count with optional labels for dimensional breakdowns.
    """

    name: str
    description: str = ""
    _value: int = field(default=0, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def inc(self, value: int = 1) -> None:
        """Increment the counter by the given value."""
        with self._lock:
            self._value += value

    def get(self) -> int:
        """Get the current counter value."""
        with self._lock:
            return self._value

    def reset(self) -> int:
        """Reset and return the previous value."""
        with self._lock:
            value = self._value
            self._value = 0
            return value


@dataclass
class Histogram:
    """Thread-safe histogram for latency/size tracking.

    Uses a sliding window approach for percentile calculations
    to avoid unbounded memory growth.
    """

    name: str
    description: str = ""
    window_size: int = 1000  # Keep last N observations
    _observations: deque = field(default_factory=lambda: deque(maxlen=1000), repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _sum: float = field(default=0.0, repr=False)
    _count: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        """Initialize observations deque with correct maxlen."""
        self._observations = deque(maxlen=self.window_size)

    def observe(self, value: float) -> None:
        """Record an observation."""
        with self._lock:
            self._observations.append(value)
            self._sum += value
            self._count += 1

    def get_percentile(self, percentile: float) -> float | None:
        """Calculate the given percentile from observations.

        Args:
            percentile: Value between 0 and 100.

        Returns:
            The percentile value, or None if no observations.

        """
        with self._lock:
            if not self._observations:
                return None

            sorted_obs = sorted(self._observations)
            idx = int(len(sorted_obs) * percentile / 100)
            idx = min(idx, len(sorted_obs) - 1)
            return float(sorted_obs[idx])

    def get_stats(self) -> dict:
        """Get all statistics for this histogram."""
        with self._lock:
            if not self._observations:
                return {
                    "count": 0,
                    "sum": 0.0,
                    "avg": 0.0,
                    "p50": None,
                    "p95": None,
                    "p99": None,
                    "min": None,
                    "max": None,
                }

            sorted_obs = sorted(self._observations)
            count = len(sorted_obs)

            return {
                "count": self._count,
                "sum": self._sum,
                "avg": self._sum / self._count if self._count > 0 else 0.0,
                "p50": sorted_obs[int(count * 0.50)] if count > 0 else None,
                "p95": sorted_obs[min(int(count * 0.95), count - 1)] if count > 0 else None,
                "p99": sorted_obs[min(int(count * 0.99), count - 1)] if count > 0 else None,
                "min": sorted_obs[0] if count > 0 else None,
                "max": sorted_obs[-1] if count > 0 else None,
            }

    def reset(self) -> dict:
        """Reset and return the previous stats."""
        with self._lock:
            # Inline stats calculation to avoid nested lock acquisition
            if not self._observations:
                stats = {
                    "count": 0,
                    "sum": 0.0,
                    "avg": 0.0,
                    "p50": None,
                    "p95": None,
                    "p99": None,
                    "min": None,
                    "max": None,
                }
            else:
                sorted_obs = sorted(self._observations)
                count = len(sorted_obs)
                stats = {
                    "count": self._count,
                    "sum": self._sum,
                    "avg": self._sum / self._count if self._count > 0 else 0.0,
                    "p50": sorted_obs[int(count * 0.50)] if count > 0 else None,
                    "p95": sorted_obs[min(int(count * 0.95), count - 1)] if count > 0 else None,
                    "p99": sorted_obs[min(int(count * 0.99), count - 1)] if count > 0 else None,
                    "min": sorted_obs[0] if count > 0 else None,
                    "max": sorted_obs[-1] if count > 0 else None,
                }
            self._observations.clear()
            self._sum = 0.0
            self._count = 0
            return stats


class Timer:
    """Context manager for timing operations.

    Usage:
        with Timer(histogram):
            # code to time
            pass
    """

    def __init__(self, histogram: Histogram) -> None:
        """Initialize timer with target histogram."""
        self.histogram = histogram
        self.start_time: float | None = None
        self.duration_ms: float | None = None

    def __enter__(self) -> Timer:
        """Start the timer."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object) -> None:
        """Stop the timer and record the duration."""
        if self.start_time is not None:
            self.duration_ms = (time.perf_counter() - self.start_time) * 1000
            self.histogram.observe(self.duration_ms)


@dataclass
class LabeledCounter:
    """Counter with label support for dimensional metrics.

    Example:
        counter = LabeledCounter("api.errors", labels=["status", "provider"])
        counter.inc(status="429", provider="openai")

    """

    name: str
    labels: Sequence[str]
    description: str = ""
    _counters: dict = field(default_factory=dict, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def _get_key(self, **label_values: str) -> str:
        """Generate a key from label values."""
        return "|".join(f"{k}={label_values.get(k, '')}" for k in self.labels)

    def inc(self, value: int = 1, **label_values: str) -> None:
        """Increment counter for the given label combination."""
        # Validate all required labels are provided
        for label in self.labels:
            if label not in label_values:
                msg = f"Missing label: {label}"
                raise ValueError(msg)
        key = self._get_key(**label_values)
        with self._lock:
            if key not in self._counters:
                self._counters[key] = 0
            self._counters[key] += value

    def get(self, **label_values: str) -> int:
        """Get counter value for the given label combination."""
        key = self._get_key(**label_values)
        with self._lock:
            return int(self._counters.get(key, 0))

    def get_all(self) -> dict[str, int]:
        """Get all counter values by label combination."""
        with self._lock:
            return dict(self._counters)

    def reset(self) -> dict[str, int]:
        """Reset all counters and return previous values."""
        with self._lock:
            values = dict(self._counters)
            self._counters.clear()
            return values
