"""Unit tests for metrics emitter wrapper.

Tests verify that the metrics client can be injected, metrics can be emitted
through the client or fallback to logging, and the Protocol is correctly typed.
"""

from typing import Any
from unittest.mock import Mock

import pytest

from app.domains.analysis.workflows.tasks.metrics import (
    MetricsClient,
    emit_metric,
    set_metrics_client,
)


@pytest.mark.unit
class MockMetricsClient:
    """Test implementation of MetricsClient protocol."""

    def __init__(self):
        """Initialize with empty call history."""
        self.gauge_calls: list[tuple[str, float | int, dict[str, Any]]] = []

    def gauge(self, name: str, value: float | int, tags: dict[str, Any] | None = None) -> None:
        """Record gauge calls for verification."""
        self.gauge_calls.append((name, value, tags or {}))


class TestSetMetricsClient:
    """Tests for set_metrics_client function."""

    def test_set_metrics_client_with_mock(self):
        """Set metrics client to a mock implementation."""
        client = MockMetricsClient()
        set_metrics_client(client)

        # Verify we can emit through the client
        emit_metric("test.metric", 42, {"env": "test"})

        assert len(client.gauge_calls) == 1
        assert client.gauge_calls[0] == ("test.metric", 42, {"env": "test"})

    def test_set_metrics_client_to_none(self):
        """Set metrics client to None to reset to logging fallback."""
        # First set a client
        client = MockMetricsClient()
        set_metrics_client(client)

        # Then clear it
        set_metrics_client(None)

        # Verify emit_metric falls back to logging (tested in TestEmitMetric)
        # This test ensures line 25 (_metrics_client = client) is covered when client is None


class TestEmitMetric:
    """Tests for emit_metric function."""

    def test_emit_metric_with_client(self):
        """Emit metric using configured client."""
        client = MockMetricsClient()
        set_metrics_client(client)

        emit_metric("pipeline.duration", 123.45, {"stage": "extract"})

        assert len(client.gauge_calls) == 1
        name, value, tags = client.gauge_calls[0]
        assert name == "pipeline.duration"
        assert value == 123.45
        assert tags == {"stage": "extract"}

    def test_emit_metric_with_client_no_tags(self):
        """Emit metric without tags defaults to empty dict."""
        client = MockMetricsClient()
        set_metrics_client(client)

        emit_metric("simple.counter", 1)

        assert len(client.gauge_calls) == 1
        name, value, tags = client.gauge_calls[0]
        assert name == "simple.counter"
        assert value == 1
        assert tags == {}  # Verifies line 33: tags or {}

    def test_emit_metric_fallback_to_logging(self, caplog):
        """Emit metric falls back to logging when no client is set."""
        set_metrics_client(None)

        with caplog.at_level("INFO"):
            emit_metric("fallback.metric", 999, {"source": "test"})

        # Verify logging was called (covers lines 30-32)
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "INFO"
        assert "metric_emit_fallback" in record.message

    def test_emit_metric_fallback_without_tags(self, caplog):
        """Emit metric fallback without tags."""
        set_metrics_client(None)

        with caplog.at_level("INFO"):
            emit_metric("no_tags.metric", 42)

        # Verify logging handles None tags (covers line 31)
        assert len(caplog.records) == 1


class TestMetricsClientProtocol:
    """Tests for MetricsClient Protocol typing."""

    def test_mock_implements_protocol(self):
        """MockMetricsClient correctly implements MetricsClient protocol."""
        client: MetricsClient = MockMetricsClient()

        # Should not raise type errors
        client.gauge("test", 1, {})
        client.gauge("test", 1.5, {"key": "value"})
        client.gauge("test", 1, None)

    def test_protocol_with_mock_library(self):
        """unittest.mock.Mock can be used as MetricsClient."""
        mock_client = Mock(spec=MetricsClient)
        set_metrics_client(mock_client)

        emit_metric("test.metric", 100, {"tag": "value"})

        mock_client.gauge.assert_called_once_with("test.metric", 100, {"tag": "value"})


@pytest.fixture(autouse=True)
def reset_metrics_client():
    """Reset metrics client to None after each test to avoid side effects."""
    yield
    set_metrics_client(None)
