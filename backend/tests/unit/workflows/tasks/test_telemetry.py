"""Unit tests for telemetry helpers."""

from unittest.mock import patch
import pytest

from app.domains.analysis.workflows.tasks.telemetry import log_chunking_metrics

@pytest.mark.unit


class TestLogChunkingMetrics:
    """Tests for log_chunking_metrics function."""

    @patch("app.domains.analysis.workflows.tasks.telemetry.logger")
    def test_logs_required_metrics(self, mock_logger):
        """Test that required metrics are logged."""
        log_chunking_metrics(
            coarse=10,
            fine=50,
            summaries=5,
            dedup_kept=45,
            dedup_dropped=5,
        )

        mock_logger.info.assert_called_once()
        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["coarse"] == 10
        assert call_kwargs["fine"] == 50
        assert call_kwargs["summaries"] == 5
        assert call_kwargs["dedup_kept"] == 45
        assert call_kwargs["dedup_dropped"] == 5

    @patch("app.domains.analysis.workflows.tasks.telemetry.logger")
    def test_logs_optional_metrics(self, mock_logger):
        """Test that optional metrics are logged when provided."""
        log_chunking_metrics(
            coarse=10,
            fine=50,
            summaries=5,
            dedup_kept=45,
            dedup_dropped=5,
            truncation_rate=0.05,
            chunking_latency_ms=150.5,
            overlap_pct=0.15,
        )

        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["truncation_rate"] == 0.05
        assert call_kwargs["chunking_latency_ms"] == 150.5
        assert call_kwargs["overlap_pct"] == 0.15

    @patch("app.domains.analysis.workflows.tasks.telemetry.logger")
    def test_logs_window_parameters(self, mock_logger):
        """Test that window parameters are logged."""
        log_chunking_metrics(
            coarse=10,
            fine=50,
            summaries=5,
            dedup_kept=45,
            dedup_dropped=5,
            short_window=100,
            long_window=500,
            doc_len_threshold=1000,
        )

        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["short_window"] == 100
        assert call_kwargs["long_window"] == 500
        assert call_kwargs["doc_len_threshold"] == 1000

    @patch("app.domains.analysis.workflows.tasks.telemetry.logger")
    def test_logs_event_name(self, mock_logger):
        """Test that event name is chunking_metrics."""
        log_chunking_metrics(
            coarse=1,
            fine=1,
            summaries=1,
            dedup_kept=1,
            dedup_dropped=0,
        )

        call_args = mock_logger.info.call_args[0]
        assert call_args[0] == "chunking_metrics"

    @patch("app.domains.analysis.workflows.tasks.telemetry.logger")
    def test_handles_none_optional_values(self, mock_logger):
        """Test that None values are handled for optional params."""
        log_chunking_metrics(
            coarse=5,
            fine=25,
            summaries=2,
            dedup_kept=23,
            dedup_dropped=2,
            truncation_rate=None,
            chunking_latency_ms=None,
        )

        call_kwargs = mock_logger.info.call_args[1]
        assert call_kwargs["truncation_rate"] is None
        assert call_kwargs["chunking_latency_ms"] is None
