"""Metadata calculation for aggregated insights.

This module provides functions for calculating and formatting metadata
for aggregated insights.
"""

import time
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class AggregationMetadataParams:
    """Parameters for aggregation metadata calculation.

    Groups parameters to reduce function complexity.
    """

    validated_findings: list[dict[str, object]]
    agent_types: list[str]
    confidence_scores: dict[str, float]
    conflicts: list[dict[str, str]]
    aggregated_insights_dict: dict[str, object]
    start_time: float


def extract_metadata_for_logging(
    aggregated_insights_dict: dict[str, object],
) -> int:
    """Extract conflicts_resolved count from metadata for logging.

    Args:
        aggregated_insights_dict: Dictionary with aggregated insights

    Returns:
        Number of conflicts resolved (0 if not found or invalid)

    """
    metadata_for_logging = aggregated_insights_dict.get("metadata", {})
    if isinstance(metadata_for_logging, dict):
        conflicts_resolved_for_log = metadata_for_logging.get("conflicts_resolved", 0)
        if isinstance(conflicts_resolved_for_log, int):
            return conflicts_resolved_for_log
    return 0


def extract_sse_metadata(
    aggregated_insights_dict: dict[str, object],
) -> tuple[int, int]:
    """Extract metadata for SSE event emission.

    Args:
        aggregated_insights_dict: Dictionary with aggregated insights

    Returns:
        Tuple of (conflicts_resolved_count, key_findings_count)

    """
    metadata_dict = aggregated_insights_dict.get("metadata", {})
    if not isinstance(metadata_dict, dict):
        metadata_dict = {}
    conflicts_resolved_count = metadata_dict.get("conflicts_resolved", 0)
    if not isinstance(conflicts_resolved_count, int):
        conflicts_resolved_count = 0

    key_findings_list = aggregated_insights_dict.get("key_findings", [])
    if not isinstance(key_findings_list, list):
        key_findings_list = []

    return conflicts_resolved_count, len(key_findings_list)


def calculate_aggregation_metadata(  # noqa: PLR0913
    validated_findings: list[dict[str, object]],
    agent_types: list[str],
    confidence_scores: dict[str, float],
    conflicts: list[dict[str, str]],
    aggregated_insights_dict: dict[str, object],
    start_time: float,
) -> dict[str, object]:
    """Calculate metadata for aggregated insights.

    Note: This function accepts 6 parameters. Parameters could be grouped into
    AggregationMetadataParams dataclass in the future to reduce complexity.

    Args:
        validated_findings: List of validated agent findings
        agent_types: List of agent type names
        confidence_scores: Dictionary of agent confidence scores
        conflicts: List of detected conflicts
        aggregated_insights_dict: Dictionary with aggregated insights
        start_time: Start time of aggregation (for processing time calculation)

    Returns:
        Dictionary with metadata fields added

    """
    processing_time_ms = int((time.time() - start_time) * 1000)

    conflicts_resolved_raw = aggregated_insights_dict.get("conflicts_resolved", [])
    conflicts_resolved_list = (
        conflicts_resolved_raw if isinstance(conflicts_resolved_raw, list) else []
    )

    confidence_values = list(confidence_scores.values())

    metadata = {
        "total_agents": len(validated_findings),
        "agents_executed": agent_types,
        "confidence_avg": (
            sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        ),
        "confidence_min": min(confidence_values) if confidence_values else 0.0,
        "confidence_max": max(confidence_values) if confidence_values else 0.0,
        "processing_time_ms": processing_time_ms,
        "conflicts_detected": len(conflicts),
        "conflicts_resolved": len(conflicts_resolved_list),
    }

    aggregated_insights_dict["metadata"] = metadata
    return aggregated_insights_dict
