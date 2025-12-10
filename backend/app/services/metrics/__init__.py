"""Metrics collection and aggregation services.

This module provides lightweight metrics collection using structlog,
avoiding external dependencies like Prometheus while still enabling
observability through log aggregation tools (CloudWatch, Loki, Datadog).
"""

from app.services.metrics.collectors import Counter, Histogram
from app.services.metrics.service import MetricsService, get_metrics_service

__all__ = [
    "Counter",
    "Histogram",
    "MetricsService",
    "get_metrics_service",
]
