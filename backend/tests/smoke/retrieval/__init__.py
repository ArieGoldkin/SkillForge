"""Retrieval smoke tests for Issue #223.

This module provides smoke tests for the retrieval system, covering:
- Semantic search (vector similarity)
- Keyword search (full-text)
- Hybrid search (RRF fusion)
- Coarse-to-fine retrieval (two-stage)

Run with: pytest tests/smoke/retrieval/ -v

Quick start:
    # Run all retrieval tests
    pytest tests/smoke/retrieval/ -v -m "smoke and retrieval"

    # Run specific mode
    pytest tests/smoke/retrieval/ -v -m "semantic"
    pytest tests/smoke/retrieval/ -v -m "hybrid"
    pytest tests/smoke/retrieval/ -v -m "keyword"

    # Use CLI runner
    python -m tests.smoke.retrieval.run_smoke_tests --mode semantic -v
"""

from tests.smoke.retrieval.fixtures import FixtureLoader
from tests.smoke.retrieval.metrics import (
    AggregateMetrics,
    MetricsCalculator,
    RetrievalMetrics,
    aggregate_metrics,
)

__all__ = [
    "AggregateMetrics",
    "FixtureLoader",
    "MetricsCalculator",
    "RetrievalMetrics",
    "aggregate_metrics",
]
