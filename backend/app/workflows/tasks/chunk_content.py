"""Task to chunk content into coarse/fine (and optional summary) payloads."""

from __future__ import annotations

from typing import TypedDict

from app.core.config import settings
from app.core.logging import get_logger
from app.services.chunking.chunker import (
    DEFAULT_LONG_WINDOW,
    DEFAULT_OVERLAP_PCT,
    DEFAULT_SHORT_WINDOW,
    ChunkText,
    chunk_document,
)
from app.services.chunking.dedup import DedupStats, deduplicate
from app.services.chunking.summaries import SummaryChunk, summarize_sections
from app.workflows.tasks.metrics import emit_metric

logger = get_logger(__name__)


class ChunkedPayload(TypedDict):
    """Payload containing chunked content at multiple granularities."""

    coarse: list[ChunkText]
    fine: list[ChunkText]
    summaries: list[SummaryChunk]
    dedup_stats: DedupStats


async def chunk_content(text: str) -> ChunkedPayload:
    """Chunk content into coarse/fine (and summaries) with dedup stats."""
    import time

    start = time.perf_counter()
    short_window = getattr(settings, "CHUNK_WINDOW_SHORT", DEFAULT_SHORT_WINDOW)
    long_window = getattr(settings, "CHUNK_WINDOW_LONG", DEFAULT_LONG_WINDOW)
    overlap_pct = getattr(settings, "CHUNK_OVERLAP_PCT", DEFAULT_OVERLAP_PCT)
    doc_len_threshold = getattr(settings, "DOC_LENGTH_THRESHOLD", 4000)
    enable_summaries = getattr(settings, "ENABLE_SUMMARIES", False)
    dedup_enabled = getattr(settings, "DEDUP_ENABLED", True)

    coarse, fine = chunk_document(
        text,
        short_window=short_window,
        long_window=long_window,
        overlap_pct=overlap_pct,
        long_threshold_tokens=doc_len_threshold,
    )

    summaries: list[SummaryChunk] = []
    if enable_summaries:
        summaries = summarize_sections(coarse)

    if dedup_enabled:
        fine, dedup_stats = deduplicate(fine)
        coarse, coarse_stats = deduplicate(coarse)
        dedup_stats = DedupStats(
            kept=dedup_stats.kept + coarse_stats.kept,
            dropped=dedup_stats.dropped + coarse_stats.dropped,
        )
    else:
        dedup_stats = DedupStats(kept=len(coarse) + len(fine), dropped=0)

    duration_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "chunk_content_complete",
        coarse=len(coarse),
        fine=len(fine),
        summaries=len(summaries),
        overlap_pct=overlap_pct,
        short_window=short_window,
        long_window=long_window,
        doc_len_threshold=doc_len_threshold,
        dedup_enabled=dedup_enabled,
        dedup_kept=dedup_stats.kept,
        dedup_dropped=dedup_stats.dropped,
        chunking_latency_ms=duration_ms,
    )

    # Metrics (fallback to logs if no metrics client)
    emit_metric("chunk.count.coarse", len(coarse))
    emit_metric("chunk.count.fine", len(fine))
    emit_metric("chunk.count.summary", len(summaries))
    emit_metric("chunk.dedup.kept", dedup_stats.kept)
    emit_metric("chunk.dedup.dropped", dedup_stats.dropped)
    emit_metric("chunk.latency_ms", duration_ms)

    return ChunkedPayload(
        coarse=coarse,
        fine=fine,
        summaries=summaries,
        dedup_stats=dedup_stats,
    )
