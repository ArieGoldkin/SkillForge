"""State definitions for LangGraph workflows.

This module defines TypedDict state structures for the analysis workflow.
State is managed by LangGraph's StateGraph and automatically checkpointed.
"""

from typing import TypedDict

from app.core.types import AnalysisID, EmbeddingVector


class AnalysisState(TypedDict, total=False):
    """State structure for the analysis workflow.

    All fields are optional (total=False) to allow incremental population
    as the workflow progresses through stages.

    Attributes:
        analysis_id: Unique identifier for this analysis
        url: URL being analyzed
        content_type: Type of content (article, video, repo)
        raw_content: Extracted text content
        extraction_metadata: Metadata from extraction (title, word_count, etc.)
        content_embedding: Vector embedding of the content
        supervisor_decision: Supervisor's agent selection decision
        agent_findings: List of findings from executed agents
        evaluation_results: Agent quality evaluation results (NEW)
        metrics: Performance and quality metrics (NEW)
    """

    analysis_id: AnalysisID
    url: str
    content_type: str
    raw_content: str
    extraction_metadata: dict[str, object]
    content_embedding: EmbeddingVector
    supervisor_decision: dict[str, object]
    agent_findings: list[dict[str, object]]
    evaluation_results: dict[str, object]  # NEW: Agent quality scores
    metrics: dict[str, object]  # NEW: Performance metrics
