"""SSE event emission helpers for aggregation.

This module provides helper functions for emitting SSE events during
aggregation processing.
"""

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.services.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


async def emit_aggregation_started(
    analysis_id: AnalysisID,
    findings_count: int,
) -> None:
    """Emit SSE event for aggregation started.

    Args:
        analysis_id: UUID of the analysis
        findings_count: Number of findings to aggregate

    """
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="aggregation",
        status="running",
        findings_count=findings_count,
    )


async def emit_aggregation_detecting_conflicts(
    analysis_id: AnalysisID,
    findings_count: int,
) -> None:
    """Emit SSE event for conflict detection phase.

    Args:
        analysis_id: UUID of the analysis
        findings_count: Number of validated findings

    """
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="aggregation",
        status="detecting_conflicts",
        findings_count=findings_count,
    )


async def emit_aggregation_synthesizing(
    analysis_id: AnalysisID,
    findings_count: int,
    conflicts_detected: int,
) -> None:
    """Emit SSE event for synthesis phase.

    Args:
        analysis_id: UUID of the analysis
        findings_count: Number of validated findings
        conflicts_detected: Number of conflicts detected

    """
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="aggregation",
        status="synthesizing",
        findings_count=findings_count,
        conflicts_detected=conflicts_detected,
    )


async def emit_aggregation_complete(
    analysis_id: AnalysisID,
    findings_count: int,
    conflicts_resolved: int,
    key_findings_count: int,
) -> None:
    """Emit SSE event for aggregation complete.

    Args:
        analysis_id: UUID of the analysis
        findings_count: Number of validated findings
        conflicts_resolved: Number of conflicts resolved
        key_findings_count: Number of key findings

    """
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="aggregation",
        status="complete",
        findings_count=findings_count,
        conflicts_resolved=conflicts_resolved,
        key_findings_count=key_findings_count,
    )


async def emit_aggregation_failed(
    analysis_id: AnalysisID,
    error: str,
) -> None:
    """Emit SSE event for aggregation failed.

    Args:
        analysis_id: UUID of the analysis
        error: Error message

    """
    await emit_streaming_event(
        "error",
        analysis_id=analysis_id,
        stage="aggregation",
        status="failed",
        error=error,
        error_code="AGGREGATION_FAILED",
    )
