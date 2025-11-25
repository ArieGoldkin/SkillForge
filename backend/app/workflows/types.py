"""Type definitions for workflow state and data structures."""

from typing import TypedDict

from app.core.types import EmbeddingVector


class AnalysisState(TypedDict, total=False):
    """State schema for the analysis workflow.

    Fields marked with total=False are optional and may be populated
    as the workflow progresses through different stages.

    Attributes:
        analysis_id: Unique identifier for the analysis
        url: Source URL being analyzed
        content_type: Detected content type (article, video, repo)
        raw_content: Extracted text content
        extraction_metadata: Metadata from extraction service
        content_embedding: Vector embedding of the content
        supervisor_decision: Supervisor routing decision (future)
        agent_findings: Findings from sub-agents (future)
        aggregated_insights: Aggregated analysis insights (future)
        final_markdown: Generated markdown artifact (future)

    """

    analysis_id: str
    url: str
    content_type: str
    raw_content: str
    extraction_metadata: dict
    content_embedding: EmbeddingVector
    supervisor_decision: dict  # For future use
    agent_findings: list[dict]  # For future use
    aggregated_insights: dict  # For future use
    final_markdown: str  # For future use
