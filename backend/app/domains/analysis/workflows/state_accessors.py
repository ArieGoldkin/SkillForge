"""Type-safe accessor functions for AnalysisState.

This module provides getter functions that encapsulate type: ignore comments
in one place, allowing all consuming code to be fully type-safe.

The root cause: TypedDict.get() returns Unknown type in ty/mypy because
the type checker can't preserve field-specific types through the .get() call.

Usage:
    from app.domains.analysis.workflows.state_accessors import (
        get_agent_findings,
        get_aggregated_insights,
    )

    findings = get_agent_findings(state)  # Returns list[AgentFinding]
"""

from app.core.types import AnalysisID
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.state_types import (
    AggregatedInsights,
    ChunkCounts,
    DedupStats,
    EvaluationResults,
    ExtractionMetadata,
    QualityScores,
    SupervisorDecision,
)
from app.shared.types import AgentFinding, WorkflowMetrics


def get_analysis_id(state: AnalysisState) -> AnalysisID:
    """Get analysis_id - required field, direct access."""
    return state["analysis_id"]


def get_agent_findings(state: AnalysisState) -> list[AgentFinding]:
    """Get agent findings from state with proper typing."""
    return state.get("agent_findings", [])  # type: ignore[return-value]


def get_aggregated_insights(state: AnalysisState) -> AggregatedInsights:
    """Get aggregated insights from state with proper typing."""
    return state.get("aggregated_insights", {})  # type: ignore[return-value]


def get_extraction_metadata(state: AnalysisState) -> ExtractionMetadata:
    """Get extraction metadata from state with proper typing."""
    return state.get("extraction_metadata", {})  # type: ignore[return-value]


def get_supervisor_decision(state: AnalysisState) -> SupervisorDecision:
    """Get supervisor decision from state with proper typing."""
    return state.get("supervisor_decision", {})  # type: ignore[return-value]


def get_quality_scores(state: AnalysisState) -> QualityScores:
    """Get quality scores from state with proper typing."""
    return state.get("quality_scores", {})  # type: ignore[return-value]


def get_evaluation_results(state: AnalysisState) -> EvaluationResults:
    """Get evaluation results from state with proper typing."""
    return state.get("evaluation_results", {})  # type: ignore[return-value]


def get_metrics(state: AnalysisState) -> WorkflowMetrics:
    """Get workflow metrics from state with proper typing."""
    return state.get("metrics", {})  # type: ignore[return-value]


def get_chunk_counts(state: AnalysisState) -> ChunkCounts:
    """Get chunk counts from state with proper typing."""
    return state.get("chunk_counts", {})  # type: ignore[return-value]


def get_dedup_stats(state: AnalysisState) -> DedupStats:
    """Get deduplication stats from state with proper typing."""
    return state.get("dedup_stats", {})  # type: ignore[return-value]
