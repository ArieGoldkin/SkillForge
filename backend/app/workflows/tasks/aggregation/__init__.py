"""Aggregation processing modules.

This package contains modules for validating, synthesizing, and processing
agent findings into aggregated insights.
"""

from app.workflows.tasks.aggregation.events import (
    emit_aggregation_complete,
    emit_aggregation_detecting_conflicts,
    emit_aggregation_failed,
    emit_aggregation_started,
    emit_aggregation_synthesizing,
)
from app.workflows.tasks.aggregation.metadata import (
    calculate_aggregation_metadata,
    extract_metadata_for_logging,
    extract_sse_metadata,
)
from app.workflows.tasks.aggregation.quick_reference import extract_quick_reference
from app.workflows.tasks.aggregation.synthesis import synthesize_with_llm
from app.workflows.tasks.aggregation.validation import validate_and_parse_findings

__all__ = [
    "calculate_aggregation_metadata",
    "emit_aggregation_complete",
    "emit_aggregation_detecting_conflicts",
    "emit_aggregation_failed",
    "emit_aggregation_started",
    "emit_aggregation_synthesizing",
    "extract_metadata_for_logging",
    "extract_quick_reference",
    "extract_sse_metadata",
    "synthesize_with_llm",
    "validate_and_parse_findings",
]
