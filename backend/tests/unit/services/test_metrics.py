"""Unit tests for the metrics service module."""

import pytest

from app.shared.services.metrics.collectors import Counter, Histogram, LabeledCounter, Timer


@pytest.mark.unit
class TestCounter:
    """Tests for Counter class."""

    def test_counter_initial_value(self):
        """Counter starts at zero."""
        counter = Counter(name="test")
        assert counter.get() == 0

    def test_counter_increment(self):
        """Counter increments by 1 by default."""
        counter = Counter(name="test")
        counter.inc()
        assert counter.get() == 1

    def test_counter_increment_by_value(self):
        """Counter can increment by custom value."""
        counter = Counter(name="test")
        counter.inc(5)
        assert counter.get() == 5

    def test_counter_multiple_increments(self):
        """Counter accumulates multiple increments."""
        counter = Counter(name="test")
        counter.inc(3)
        counter.inc(7)
        assert counter.get() == 10

    def test_counter_reset(self):
        """Counter reset returns old value and sets to zero."""
        counter = Counter(name="test")
        counter.inc(42)
        old_value = counter.reset()
        assert old_value == 42
        assert counter.get() == 0


class TestHistogram:
    """Tests for Histogram class."""

    def test_histogram_empty(self):
        """Empty histogram returns None for percentiles."""
        histogram = Histogram(name="test")
        assert histogram.get_percentile(50) is None

    def test_histogram_observe(self):
        """Histogram records observations."""
        histogram = Histogram(name="test")
        histogram.observe(100)
        histogram.observe(200)
        assert histogram.get_percentile(50) is not None

    def test_histogram_percentiles(self):
        """Histogram calculates percentiles correctly."""
        histogram = Histogram(name="test")
        for i in range(1, 101):
            histogram.observe(i)

        # p50 should be around 50
        p50 = histogram.get_percentile(50)
        assert p50 is not None
        assert 49 <= p50 <= 51

        # p99 should be high
        p99 = histogram.get_percentile(99)
        assert p99 is not None
        assert p99 >= 95

    def test_histogram_stats(self):
        """Histogram get_stats returns correct statistics."""
        histogram = Histogram(name="test")
        histogram.observe(10)
        histogram.observe(20)
        histogram.observe(30)

        stats = histogram.get_stats()
        assert stats["count"] == 3
        assert stats["sum"] == 60.0
        assert stats["avg"] == 20.0

    def test_histogram_reset(self):
        """Histogram reset clears observations."""
        histogram = Histogram(name="test")
        histogram.observe(100)
        histogram.reset()
        assert histogram.get_percentile(50) is None


class TestTimer:
    """Tests for Timer context manager."""

    def test_timer_records_duration(self):
        """Timer records duration to histogram."""
        histogram = Histogram(name="test")
        timer = Timer(histogram)

        with timer:
            # Do nothing, just test that it records
            pass

        assert histogram.get_percentile(50) is not None

    def test_timer_duration_property(self):
        """Timer exposes duration after context exit."""
        histogram = Histogram(name="test")
        timer = Timer(histogram)

        with timer:
            pass

        # Duration should be very small (< 1000ms for empty block)
        assert timer.duration_ms is not None
        assert timer.duration_ms >= 0
        assert timer.duration_ms < 1000


class TestLabeledCounter:
    """Tests for LabeledCounter class."""

    def test_labeled_counter_single_label(self):
        """LabeledCounter tracks by single label."""
        counter = LabeledCounter(name="test", labels=["status"])
        counter.inc(status="success")
        counter.inc(status="success")
        counter.inc(status="error")

        assert counter.get(status="success") == 2
        assert counter.get(status="error") == 1

    def test_labeled_counter_multiple_labels(self):
        """LabeledCounter tracks by multiple labels."""
        counter = LabeledCounter(name="test", labels=["provider", "status"])
        counter.inc(provider="openai", status="success")
        counter.inc(provider="openai", status="error")
        counter.inc(provider="anthropic", status="success")

        assert counter.get(provider="openai", status="success") == 1
        assert counter.get(provider="openai", status="error") == 1
        assert counter.get(provider="anthropic", status="success") == 1

    def test_labeled_counter_get_all(self):
        """LabeledCounter get_all returns all combinations."""
        counter = LabeledCounter(name="test", labels=["status"])
        counter.inc(status="success")
        counter.inc(status="error")

        all_values = counter.get_all()
        assert "status=success" in all_values
        assert "status=error" in all_values

    def test_labeled_counter_missing_label_raises(self):
        """LabeledCounter raises on missing label."""
        counter = LabeledCounter(name="test", labels=["status"])
        with pytest.raises(ValueError, match="Missing label"):
            counter.inc()  # No status provided

    def test_labeled_counter_reset(self):
        """LabeledCounter reset clears all counters."""
        counter = LabeledCounter(name="test", labels=["status"])
        counter.inc(status="success")
        old_values = counter.reset()
        assert "status=success" in old_values
        assert counter.get(status="success") == 0
