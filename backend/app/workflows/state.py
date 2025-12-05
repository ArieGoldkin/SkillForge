"""State definitions for LangGraph workflows.

This module defines TypedDict state structures for the analysis workflow.
State is managed by LangGraph's StateGraph and automatically checkpointed.
"""

import operator
from typing import Annotated, TypedDict

from app.core.types import AnalysisID, EmbeddingVector


class AnalysisState(TypedDict, total=False):
    """State structure for the analysis workflow.

    All fields are optional (total=False) to allow incremental population
    as the workflow progresses through stages.

    Attributes:
        analysis_id: Unique identifier for this analysis
        url: URL being analyzed
        content_type: Type of content (article, video, repo)
        skill_level: User's experience level (beginner, intermediate, expert)
        raw_content: Extracted text content
        extraction_metadata: Metadata from extraction (title, word_count, etc.)
        content_embedding: Vector embedding of the content
        supervisor_decision: Supervisor's agent selection decision
        agent_findings: List of findings from executed agents (uses reducer for parallel merge)
        aggregated_insights: Synthesized insights from all agents (Issue #71)
        artifact_id: UUID of generated artifact (Issue #72)
        evaluation_results: Agent quality evaluation results (NEW)
        metrics: Performance and quality metrics (NEW)

    Note:
        agent_findings uses operator.add reducer to allow parallel agent nodes
        to append their findings. Each agent node returns {"agent_findings": [result]},
        and LangGraph automatically concatenates them.

    """

    analysis_id: AnalysisID
    url: str
    content_type: str
    skill_level: str  # "beginner" | "intermediate" | "expert"
    raw_content: str
    extraction_metadata: dict[str, object]
    content_embedding: EmbeddingVector
    supervisor_decision: dict[str, object]
    agent_findings: Annotated[list[dict[str, object]], operator.add]
    aggregated_insights: dict[str, object]  # Issue #71: Synthesized insights
    artifact_id: str | None  # Issue #72: Generated artifact ID
    evaluation_results: dict[str, object]  # NEW: Agent quality scores
    metrics: dict[str, object]  # NEW: Performance metrics
