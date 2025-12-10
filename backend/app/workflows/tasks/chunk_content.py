"""Task to chunk content into coarse/fine (and optional summary) payloads.

Includes optional PII screening before chunking (Issue #220).
"""

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
from app.services.pii import PIIDetector, PIIResult
from app.workflows.tasks.metrics import emit_metric

logger = get_logger(__name__)


class PIIRejectError(Exception):
    """Raised when content is rejected due to PII detection.

    Attributes:
        pii_types: List of PII types that triggered rejection.
        pii_density: Ratio of PII characters to total content.

    """

    def __init__(self, pii_types: list[str], pii_density: float) -> None:
        self.pii_types = pii_types
        self.pii_density = pii_density
        super().__init__(
            f"Content rejected: PII detected (types={pii_types}, density={pii_density:.2%})"
        )


class PIIMetadata(TypedDict, total=False):
    """PII detection metadata for a chunked payload.

    Attributes:
        pii_flag: Whether PII was detected in the content.
        pii_types: List of PII types detected (e.g., ["email", "phone_us"]).
        pii_count: Total number of PII matches found.

    SECURITY: Contains only type flags, NEVER actual PII values.
    """

    pii_flag: bool
    pii_types: list[str]
    pii_count: int


class ChunkedPayload(TypedDict, total=False):
    """Payload containing chunked content at multiple granularities."""

    coarse: list[ChunkText]
    fine: list[ChunkText]
    summaries: list[SummaryChunk]
    dedup_stats: DedupStats
    pii_metadata: PIIMetadata  # Issue #220: PII detection flags (no raw values)


def _screen_for_pii(text: str) -> tuple[PIIResult | None, PIIMetadata | None]:
    """Screen content for PII before chunking.

    Args:
        text: Raw content to screen.

    Returns:
        Tuple of (PIIResult, PIIMetadata) if screening is enabled, else (None, None).

    Raises:
        PIIRejectError: If PII is detected and action is REJECT.

    """
    pii_enabled = getattr(settings, "PII_SCREENING_ENABLED", False)
    if not pii_enabled:
        return None, None

    detector = PIIDetector()
    result = detector.scan(text)

    if not result.has_pii:
        return result, PIIMetadata(pii_flag=False, pii_types=[], pii_count=0)

    # Build metadata from result
    pii_metadata = PIIMetadata(
        pii_flag=True,
        pii_types=[t.value for t in result.types],
        pii_count=result.match_count,
    )

    # Check if we should reject based on action setting
    pii_action = getattr(settings, "PII_ACTION", "flag")
    if pii_action == "reject":
        # Calculate density based on match count and content length
        # Note: PIIResult stores match count, not character spans
        # This is a simplified density calculation
        estimated_pii_chars = result.match_count * 15  # avg PII token length
        density = estimated_pii_chars / len(text) if text else 0.0

        reject_threshold = getattr(settings, "PII_REJECT_THRESHOLD", 0.3)
        if density > reject_threshold:
            logger.warning(
                "pii_content_rejected",
                pii_types=pii_metadata["pii_types"],
                pii_count=result.match_count,
                estimated_density=density,
                threshold=reject_threshold,
            )
            raise PIIRejectError(
                pii_types=pii_metadata["pii_types"],
                pii_density=density,
            )

    # Log detection (types only, never values)
    logger.info(
        "pii_screening_complete",
        pii_flag=True,
        pii_types=pii_metadata["pii_types"],
        pii_count=result.match_count,
        action="flag",
    )

    return result, pii_metadata


async def chunk_content(text: str) -> ChunkedPayload:
    """Chunk content into coarse/fine (and summaries) with dedup stats.

    Includes optional PII screening before chunking (Issue #220).

    Args:
        text: Raw content to chunk.

    Returns:
        ChunkedPayload with coarse/fine chunks, summaries, and PII metadata.

    Raises:
        PIIRejectError: If PII screening is enabled with REJECT action and
            PII density exceeds the configured threshold.

    """
    import time

    start = time.perf_counter()

    # ===== PII SCREENING (Issue #220) =====
    # Screen BEFORE chunking for:
    # 1. Single pass through entire document
    # 2. Full context for better detection
    # 3. Early rejection if PII density too high
    _, pii_metadata = _screen_for_pii(text)

    # ===== CHUNKING CONFIGURATION =====
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

    # Include PII metadata in log if available
    pii_log_data = {}
    if pii_metadata:
        pii_log_data = {
            "pii_flag": pii_metadata.get("pii_flag", False),
            "pii_types": pii_metadata.get("pii_types", []),
            "pii_count": pii_metadata.get("pii_count", 0),
        }

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
        **pii_log_data,
    )

    # Metrics (fallback to logs if no metrics client)
    emit_metric("chunk.count.coarse", len(coarse))
    emit_metric("chunk.count.fine", len(fine))
    emit_metric("chunk.count.summary", len(summaries))
    emit_metric("chunk.dedup.kept", dedup_stats.kept)
    emit_metric("chunk.dedup.dropped", dedup_stats.dropped)
    emit_metric("chunk.latency_ms", duration_ms)

    # PII metrics (Issue #220)
    if pii_metadata:
        emit_metric("pii.detected", 1 if pii_metadata.get("pii_flag") else 0)
        emit_metric("pii.match_count", pii_metadata.get("pii_count", 0))

    # Build result payload
    result = ChunkedPayload(
        coarse=coarse,
        fine=fine,
        summaries=summaries,
        dedup_stats=dedup_stats,
    )

    # Add PII metadata if screening was performed
    if pii_metadata is not None:
        result["pii_metadata"] = pii_metadata

    return result
