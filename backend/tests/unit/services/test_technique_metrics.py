"""Unit tests for technique metrics tracking module."""

import time

import pytest

from app.shared.services.metrics.technique_metrics import (
    MetricsCollector,
    TechniqueMetrics,
)


@pytest.mark.unit
class TestTechniqueMetrics:
    """Tests for TechniqueMetrics dataclass."""

    def test_technique_metrics_creation(self):
        """TechniqueMetrics can be created with required fields."""
        metrics = TechniqueMetrics(
            analysis_id="analysis-123",
            technique="prompt-caching",
            variant="control",
        )

        assert metrics.analysis_id == "analysis-123"
        assert metrics.technique == "prompt-caching"
        assert metrics.variant == "control"
        assert metrics.latency_ms == 0
        assert metrics.token_count_input == 0
        assert metrics.token_count_output == 0
        assert metrics.cache_hit is False
        assert metrics.cache_level is None
        assert metrics.quality_score is None
        assert metrics.estimated_cost_usd == 0
        assert metrics.started_at > 0
        assert metrics.completed_at is None

    def test_technique_metrics_with_all_fields(self):
        """TechniqueMetrics can be created with all fields populated."""
        start_time = time.time()
        metrics = TechniqueMetrics(
            analysis_id="analysis-456",
            technique="semantic-cache",
            variant="treatment",
            latency_ms=1250.5,
            token_count_input=1500,
            token_count_output=800,
            cache_hit=True,
            cache_level="l2_redis",
            quality_score=0.85,
            estimated_cost_usd=0.042,
            started_at=start_time,
            completed_at=start_time + 1.25,
        )

        assert metrics.analysis_id == "analysis-456"
        assert metrics.technique == "semantic-cache"
        assert metrics.variant == "treatment"
        assert metrics.latency_ms == 1250.5
        assert metrics.token_count_input == 1500
        assert metrics.token_count_output == 800
        assert metrics.cache_hit is True
        assert metrics.cache_level == "l2_redis"
        assert metrics.quality_score == 0.85
        assert metrics.estimated_cost_usd == 0.042
        assert metrics.started_at == start_time
        assert metrics.completed_at == start_time + 1.25

    def test_technique_metrics_cache_levels(self):
        """TechniqueMetrics supports all cache level types."""
        # L1 exact match cache
        metrics_l1 = TechniqueMetrics(
            analysis_id="a1",
            technique="test",
            variant="control",
            cache_hit=True,
            cache_level="l1_exact",
        )
        assert metrics_l1.cache_level == "l1_exact"

        # L2 Redis cache
        metrics_l2 = TechniqueMetrics(
            analysis_id="a2",
            technique="test",
            variant="control",
            cache_hit=True,
            cache_level="l2_redis",
        )
        assert metrics_l2.cache_level == "l2_redis"

        # L3 prompt cache
        metrics_l3 = TechniqueMetrics(
            analysis_id="a3",
            technique="test",
            variant="control",
            cache_hit=True,
            cache_level="l3_prompt",
        )
        assert metrics_l3.cache_level == "l3_prompt"

        # No cache
        metrics_none = TechniqueMetrics(
            analysis_id="a4",
            technique="test",
            variant="control",
            cache_hit=False,
            cache_level=None,
        )
        assert metrics_none.cache_level is None


@pytest.mark.unit
class TestMetricsCollector:
    """Tests for MetricsCollector class."""

    def test_metrics_collector_initialization(self):
        """MetricsCollector initializes with empty list."""
        collector = MetricsCollector()
        assert collector._metrics == []

    def test_record_sets_completed_at(self):
        """record() sets completed_at timestamp."""
        collector = MetricsCollector()
        metrics = TechniqueMetrics(
            analysis_id="analysis-789",
            technique="prompt-caching",
            variant="control",
        )

        assert metrics.completed_at is None
        collector.record(metrics)
        assert metrics.completed_at is not None
        assert metrics.completed_at > metrics.started_at

    def test_record_appends_to_list(self):
        """record() appends metrics to internal list."""
        collector = MetricsCollector()
        metrics1 = TechniqueMetrics(
            analysis_id="a1",
            technique="test",
            variant="control",
        )
        metrics2 = TechniqueMetrics(
            analysis_id="a2",
            technique="test",
            variant="treatment",
        )

        collector.record(metrics1)
        assert len(collector._metrics) == 1

        collector.record(metrics2)
        assert len(collector._metrics) == 2

    def test_get_summary_empty_technique(self):
        """get_summary() returns empty dict for unknown technique."""
        collector = MetricsCollector()
        summary = collector.get_summary("unknown-technique")
        assert summary == {}

    def test_get_summary_control_vs_treatment(self):
        """get_summary() correctly separates control and treatment."""
        collector = MetricsCollector()

        # Add control metrics
        control1 = TechniqueMetrics(
            analysis_id="c1",
            technique="prompt-caching",
            variant="control",
            latency_ms=1000.0,
        )
        control2 = TechniqueMetrics(
            analysis_id="c2",
            technique="prompt-caching",
            variant="control",
            latency_ms=1200.0,
        )

        # Add treatment metrics
        treatment1 = TechniqueMetrics(
            analysis_id="t1",
            technique="prompt-caching",
            variant="treatment",
            latency_ms=800.0,
            cache_hit=True,
        )
        treatment2 = TechniqueMetrics(
            analysis_id="t2",
            technique="prompt-caching",
            variant="treatment",
            latency_ms=900.0,
            cache_hit=True,
        )
        treatment3 = TechniqueMetrics(
            analysis_id="t3",
            technique="prompt-caching",
            variant="treatment",
            latency_ms=1000.0,
            cache_hit=False,
        )

        collector.record(control1)
        collector.record(control2)
        collector.record(treatment1)
        collector.record(treatment2)
        collector.record(treatment3)

        summary = collector.get_summary("prompt-caching")

        assert summary["technique"] == "prompt-caching"
        assert summary["control_count"] == 2
        assert summary["treatment_count"] == 3
        assert summary["control_avg_latency"] == 1100.0  # (1000 + 1200) / 2
        assert summary["treatment_avg_latency"] == 900.0  # (800 + 900 + 1000) / 3
        assert summary["treatment_cache_hit_rate"] == pytest.approx(2 / 3)

    def test_get_summary_cache_hit_rate_calculation(self):
        """get_summary() correctly calculates cache hit rate."""
        collector = MetricsCollector()

        # All cache hits
        for i in range(4):
            metrics = TechniqueMetrics(
                analysis_id=f"t{i}",
                technique="semantic-cache",
                variant="treatment",
                cache_hit=True,
            )
            collector.record(metrics)

        summary = collector.get_summary("semantic-cache")
        assert summary["treatment_cache_hit_rate"] == 1.0

        # Add one cache miss
        miss = TechniqueMetrics(
            analysis_id="t4",
            technique="semantic-cache",
            variant="treatment",
            cache_hit=False,
        )
        collector.record(miss)

        summary = collector.get_summary("semantic-cache")
        assert summary["treatment_cache_hit_rate"] == 0.8  # 4 hits / 5 total

    def test_get_summary_latency_averages(self):
        """get_summary() correctly calculates latency averages."""
        collector = MetricsCollector()

        # Single control run
        control = TechniqueMetrics(
            analysis_id="c1",
            technique="test",
            variant="control",
            latency_ms=500.0,
        )
        collector.record(control)

        # Multiple treatment runs with varying latency
        latencies = [100.0, 200.0, 300.0, 400.0]
        for i, latency in enumerate(latencies):
            treatment = TechniqueMetrics(
                analysis_id=f"t{i}",
                technique="test",
                variant="treatment",
                latency_ms=latency,
            )
            collector.record(treatment)

        summary = collector.get_summary("test")
        assert summary["control_avg_latency"] == 500.0
        assert summary["treatment_avg_latency"] == 250.0  # (100+200+300+400)/4

    def test_get_summary_zero_division_safety(self):
        """get_summary() safely handles empty control or treatment groups."""
        collector = MetricsCollector()

        # Only treatment metrics
        treatment = TechniqueMetrics(
            analysis_id="t1",
            technique="test",
            variant="treatment",
            latency_ms=1000.0,
            cache_hit=True,
        )
        collector.record(treatment)

        summary = collector.get_summary("test")
        assert summary["control_count"] == 0
        assert summary["treatment_count"] == 1
        assert summary["control_avg_latency"] == 0  # No control data
        assert summary["treatment_avg_latency"] == 1000.0
        assert summary["treatment_cache_hit_rate"] == 1.0

    def test_get_summary_multiple_techniques(self):
        """get_summary() correctly filters by technique."""
        collector = MetricsCollector()

        # Add metrics for technique A
        metrics_a = TechniqueMetrics(
            analysis_id="a1",
            technique="technique-a",
            variant="control",
            latency_ms=100.0,
        )
        collector.record(metrics_a)

        # Add metrics for technique B
        metrics_b = TechniqueMetrics(
            analysis_id="b1",
            technique="technique-b",
            variant="control",
            latency_ms=200.0,
        )
        collector.record(metrics_b)

        # Summary for A should only include A's metrics
        summary_a = collector.get_summary("technique-a")
        assert summary_a["technique"] == "technique-a"
        assert summary_a["control_count"] == 1
        assert summary_a["control_avg_latency"] == 100.0

        # Summary for B should only include B's metrics
        summary_b = collector.get_summary("technique-b")
        assert summary_b["technique"] == "technique-b"
        assert summary_b["control_count"] == 1
        assert summary_b["control_avg_latency"] == 200.0

    def test_collector_isolation(self):
        """Each MetricsCollector instance has independent state."""
        collector1 = MetricsCollector()
        collector2 = MetricsCollector()

        metrics1 = TechniqueMetrics(
            analysis_id="a1",
            technique="test",
            variant="control",
        )
        collector1.record(metrics1)

        assert len(collector1._metrics) == 1
        assert len(collector2._metrics) == 0
