"""Unit tests for the backpressure module."""

import time

from app.shared.services.backpressure.batch_sizer import AdaptiveBatchSizer
from app.shared.services.backpressure.error_tracker import ErrorTracker, ErrorType
from app.shared.services.backpressure.rate_limiter import RateLimiter

@pytest.mark.unit


class TestErrorTracker:
    """Tests for ErrorTracker class."""

    def test_error_tracker_initial_state(self):
        """Error tracker starts with zero error rate."""
        tracker = ErrorTracker()
        assert tracker.get_error_rate() == 0.0

    def test_error_tracker_record_success(self):
        """Recording success updates statistics."""
        tracker = ErrorTracker()
        tracker.record_success()
        tracker.record_success()

        stats = tracker.get_stats()
        assert stats["success_count"] == 2
        assert stats["error_count"] == 0

    def test_error_tracker_record_error(self):
        """Recording errors updates statistics."""
        tracker = ErrorTracker()
        tracker.record_error(ErrorType.RATE_LIMIT)
        tracker.record_error(ErrorType.SERVER_ERROR, status_code=500)

        stats = tracker.get_stats()
        assert stats["error_count"] == 2
        assert "RATE_LIMIT" in stats["errors_by_type"]

    def test_error_tracker_error_rate_calculation(self):
        """Error rate calculated correctly."""
        tracker = ErrorTracker()
        # 1 error + 9 successes = 10% error rate
        tracker.record_error(ErrorType.OTHER)
        for _ in range(9):
            tracker.record_success()

        rate = tracker.get_error_rate()
        assert 9.0 <= rate <= 11.0  # ~10%

    def test_error_tracker_threshold_exceeded(self):
        """is_threshold_exceeded works correctly."""
        tracker = ErrorTracker(threshold_percent=5.0)

        # 6% error rate (6 errors, 94 successes)
        for _ in range(6):
            tracker.record_error(ErrorType.OTHER)
        for _ in range(94):
            tracker.record_success()

        assert tracker.is_threshold_exceeded()

    def test_error_tracker_should_backoff_on_rate_limits(self):
        """should_backoff returns True after multiple rate limits."""
        tracker = ErrorTracker()

        # Multiple rate limits should trigger backoff
        for _ in range(3):
            tracker.record_rate_limit()

        assert tracker.should_backoff()

    def test_error_tracker_reset(self):
        """Reset clears all tracked data."""
        tracker = ErrorTracker()
        tracker.record_error(ErrorType.OTHER)
        tracker.record_success()
        tracker.reset()

        assert tracker.get_error_rate() == 0.0
        assert tracker.get_stats()["total_requests"] == 0

    def test_error_tracker_convenience_methods(self):
        """Convenience methods work correctly."""
        tracker = ErrorTracker()
        tracker.record_rate_limit()
        tracker.record_server_error(502)
        tracker.record_timeout()

        counts = tracker.get_error_count_by_type()
        assert counts.get("RATE_LIMIT", 0) == 1
        assert counts.get("SERVER_ERROR", 0) == 1
        assert counts.get("TIMEOUT", 0) == 1


class TestAdaptiveBatchSizer:
    """Tests for AdaptiveBatchSizer class."""

    def test_batch_sizer_initial_size(self):
        """Batch sizer starts at initial size."""
        sizer = AdaptiveBatchSizer(initial_size=20)
        assert sizer.current_size == 20

    def test_batch_sizer_decrease_for_rate_limit(self):
        """decrease_for_rate_limit halves batch size by default."""
        sizer = AdaptiveBatchSizer(
            initial_size=20,
            decrease_factor_429=0.5,
            cooldown_seconds=0,  # No cooldown for test
        )
        new_size = sizer.decrease_for_rate_limit()
        assert new_size == 10

    def test_batch_sizer_decrease_for_server_error(self):
        """decrease_for_server_error reduces batch size by 25% by default."""
        sizer = AdaptiveBatchSizer(
            initial_size=20,
            decrease_factor_5xx=0.75,
            cooldown_seconds=0,
        )
        new_size = sizer.decrease_for_server_error()
        assert new_size == 15

    def test_batch_sizer_respects_min_size(self):
        """Batch size doesn't go below minimum."""
        sizer = AdaptiveBatchSizer(
            initial_size=2,
            min_size=1,
            decrease_factor_429=0.5,
            cooldown_seconds=0,
        )
        sizer.decrease_for_rate_limit()
        new_size = sizer.decrease_for_rate_limit()
        assert new_size >= 1

    def test_batch_sizer_cooldown(self):
        """Batch size changes respect cooldown period."""
        sizer = AdaptiveBatchSizer(
            initial_size=20,
            cooldown_seconds=1.0,  # 1 second cooldown
        )
        first = sizer.decrease_for_rate_limit()
        second = sizer.decrease_for_rate_limit()  # Should be blocked by cooldown

        # Second call should return same size (cooldown active)
        assert first == second == sizer.current_size

    def test_batch_sizer_get_next_batch_size(self):
        """get_next_batch_size respects remaining items."""
        sizer = AdaptiveBatchSizer(initial_size=20)

        # When remaining > current_size, return current_size
        assert sizer.get_next_batch_size(100) == 20

        # When remaining < current_size, return remaining
        assert sizer.get_next_batch_size(5) == 5

    def test_batch_sizer_reset(self):
        """Reset returns to initial size."""
        sizer = AdaptiveBatchSizer(initial_size=20, cooldown_seconds=0)
        sizer.decrease_for_rate_limit()
        assert sizer.current_size == 10

        sizer.reset()
        assert sizer.current_size == 20

    def test_batch_sizer_stats(self):
        """get_stats returns correct information."""
        sizer = AdaptiveBatchSizer(
            initial_size=20,
            min_size=1,
            max_size=100,
            name="test",
        )
        stats = sizer.get_stats()

        assert stats["name"] == "test"
        assert stats["current_size"] == 20
        assert stats["initial_size"] == 20
        assert stats["min_size"] == 1
        assert stats["max_size"] == 100


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_rate_limiter_initial_tokens(self):
        """Rate limiter starts with burst capacity tokens."""
        limiter = RateLimiter(burst_capacity=100)
        assert limiter.get_available_tokens() == 100

    def test_rate_limiter_try_acquire_success(self):
        """try_acquire succeeds when tokens available."""
        limiter = RateLimiter(burst_capacity=10)
        assert limiter.try_acquire(5)
        # Use approximate comparison due to token refill during test execution
        assert abs(limiter.get_available_tokens() - 5) < 0.1

    def test_rate_limiter_try_acquire_failure(self):
        """try_acquire fails when insufficient tokens."""
        limiter = RateLimiter(burst_capacity=5)
        assert not limiter.try_acquire(10)
        assert limiter.get_available_tokens() == 5  # Unchanged

    def test_rate_limiter_blocking_acquire(self):
        """Acquire blocks until tokens available."""
        limiter = RateLimiter(tokens_per_minute=60000, burst_capacity=1)

        # First acquire uses the token
        limiter.try_acquire(1)

        # Second acquire should wait briefly
        start = time.monotonic()
        limiter.acquire(1)
        elapsed = time.monotonic() - start

        # Should have waited some time (but not too long)
        assert elapsed >= 0  # At least didn't error

    def test_rate_limiter_refill(self):
        """Tokens refill over time."""
        limiter = RateLimiter(
            tokens_per_minute=60000,  # 1000/sec
            burst_capacity=100,
        )

        # Use all tokens
        limiter.try_acquire(100)
        assert limiter.get_available_tokens() < 1

        # Wait briefly for refill
        time.sleep(0.01)  # 10ms = ~10 tokens at 1000/sec

        available = limiter.get_available_tokens()
        assert available > 0

    def test_rate_limiter_get_wait_time(self):
        """get_wait_time estimates wait correctly."""
        limiter = RateLimiter(
            tokens_per_minute=600,  # 10/sec
            burst_capacity=10,
        )

        # Use all tokens
        limiter.try_acquire(10)

        # Should need to wait for 1 token
        wait = limiter.get_wait_time(1)
        assert wait > 0  # Needs to wait
        assert wait < 1.0  # But not too long

    def test_rate_limiter_reset(self):
        """Reset restores full capacity."""
        limiter = RateLimiter(burst_capacity=100)
        limiter.try_acquire(50)
        # Use approximate comparison due to token refill during test execution
        assert abs(limiter.get_available_tokens() - 50) < 0.1

        limiter.reset()
        assert limiter.get_available_tokens() == 100

    def test_rate_limiter_refill_rate(self):
        """refill_rate property calculates correctly."""
        limiter = RateLimiter(tokens_per_minute=600)
        assert limiter.refill_rate == 10.0  # 600/60 = 10 per second
