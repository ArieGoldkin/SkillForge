"""Metrics emitter wrapper for chunking pipeline."""

from __future__ import annotations

from typing import Any, Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


class MetricsClient(Protocol):
    """Protocol for metrics clients."""

    def gauge(self, name: str, value: float | int, tags: dict[str, Any] | None = None) -> None:
        """Record a gauge metric."""


_metrics_client: MetricsClient | None = None


def set_metrics_client(client: MetricsClient | None) -> None:
    """Inject a metrics client; if None, falls back to logging."""
    global _metrics_client  # noqa: PLW0603
    _metrics_client = client


def emit_metric(name: str, value: float | int, tags: dict[str, Any] | None = None) -> None:
    """Emit a metric using configured client or log fallback."""
    if _metrics_client is None:
        logger.info("metric_emit_fallback", name=name, value=value, tags=tags)
        return
    _metrics_client.gauge(name, value, tags or {})
