"""Telemetry helpers for chunking/embedding pipeline."""

from __future__ import annotations

from app.core.logging import get_logger

logger = get_logger(__name__)


def log_chunking_metrics(  # noqa: PLR0913
    *,
    coarse: int,
    fine: int,
    summaries: int,
    dedup_kept: int,
    dedup_dropped: int,
    truncation_rate: float | None = None,
    chunking_latency_ms: float | None = None,
    overlap_pct: float | None = None,
    short_window: int | None = None,
    long_window: int | None = None,
    doc_len_threshold: int | None = None,
) -> None:
    """Log chunking pipeline metrics for observability."""
    logger.info(
        "chunking_metrics",
        coarse=coarse,
        fine=fine,
        summaries=summaries,
        dedup_kept=dedup_kept,
        dedup_dropped=dedup_dropped,
        truncation_rate=truncation_rate,
        chunking_latency_ms=chunking_latency_ms,
        overlap_pct=overlap_pct,
        short_window=short_window,
        long_window=long_window,
        doc_len_threshold=doc_len_threshold,
    )
