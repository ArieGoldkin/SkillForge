"""State definitions for LangGraph workflows.

This module defines TypedDict state structures for the analysis workflow.
State is managed by LangGraph's StateGraph and automatically checkpointed.

Handle Pattern (Issue #244): Large content is stored as refs, not inline.
Agents use load_artifact tool to retrieve content sections on-demand.
"""

import operator
from typing import Annotated, Literal, TypedDict

from app.core.types import AnalysisID, EmbeddingVector
from app.domains.analysis.workflows.state_types import (
    AggregatedInsights,
    ChunkCounts,
    DedupStats,
    EvaluationResults,
    ExtractionMetadata,
    QualityScores,
    SupervisorDecision,
)
from app.domains.analysis.workflows.tier_types import TierSummary
from app.shared.types import AgentFinding, WorkflowMetrics


class ContentRef(TypedDict, total=False):
    """Lightweight reference to content stored in database.

    This implements the Handle Pattern from Google ADK's Context Engineering.
    Instead of passing large content inline through state, we pass this
    lightweight reference (~200 bytes) and let agents load what they need.

    Attributes:
        uri: Artifact URI (analysis://{analysis_id}/content)
        summary: Always-available content summary (~500 words)
        size_bytes: Original content size for context
        content_type: MIME type (text/plain, text/markdown)
        available_sections: Loadable sections (summary, full, code_blocks, headings)

    """

    uri: str
    summary: str
    size_bytes: int
    content_type: str
    available_sections: list[str]


class AnalysisState(TypedDict, total=False):
    """State structure for the analysis workflow.

    All fields are optional (total=False) to allow incremental population
    as the workflow progresses through stages.

    Attributes:
        analysis_id: Unique identifier for this analysis
        url: URL being analyzed
        content_type: Type of content (article, video, repo)
        skill_level: User's experience level (beginner, intermediate, expert)
        raw_content: Extracted text content (DEPRECATED: use content_ref)
        content_ref: Lightweight ref to content - agents use load_artifact tool
        extraction_metadata: Metadata from extraction (title, word_count, etc.)
        content_embedding: Vector embedding of the content
        supervisor_decision: Supervisor's agent selection decision
        agent_findings: List of findings from executed agents (uses reducer for parallel merge)
        aggregated_insights: Synthesized insights from all agents (Issue #71)
        artifact_id: UUID of generated artifact (Issue #72)
        evaluation_results: Agent quality evaluation results (NEW)
        metrics: Performance and quality metrics (NEW)
        should_abort: Flag to signal workflow should stop early (Issue #441)
        abort_reason: Human-readable error message if workflow aborted (Issue #441)
        extraction_status: Status of extraction node - pending/success/failed (Issue #441)
        extraction_error_code: Error code if extraction failed (Issue #441)
        workflow_status: Final workflow status - running/completed/failed (Issue #441)
        final_error: Final error message if workflow failed (Issue #441)
        tier1_summary: Compressed findings from Tier 1 agents (Issue #588)
        tier2_summary: Compressed findings from Tier 2 agents (Issue #588)
        tier3_summary: Compressed findings from Tier 3 agents (Issue #588)

    Note:
        agent_findings uses operator.add reducer to allow parallel agent nodes
        to append their findings. Each agent node returns {"agent_findings": [result]},
        and LangGraph automatically concatenates them.

    Handle Pattern (Issue #244):
        raw_content is deprecated. Use content_ref instead.
        Agents should call load_artifact(uri, section) to get content.
        Available sections: summary, full, first_n, code_blocks, headings.

    Abort Signal (Issue #441):
        Nodes can set should_abort=True to signal early termination.
        Subsequent nodes should check should_abort and skip processing if True.
        abort_reason provides user-facing error message for debugging.

    """

    analysis_id: AnalysisID
    url: str
    content_type: str
    skill_level: str  # "beginner" | "intermediate" | "expert"
    analysis_mode: str  # "quick" | "standard" | "deep_dive" (Issue #436)
    raw_content: str  # DEPRECATED: Use content_ref for new code
    content_ref: ContentRef  # Issue #244: Handle Pattern - lightweight ref
    extraction_metadata: ExtractionMetadata  # Was dict[str, object]
    content_embedding: EmbeddingVector
    supervisor_decision: SupervisorDecision  # Was dict[str, object]
    agent_findings: Annotated[list[AgentFinding], operator.add]  # Typed findings
    aggregated_insights: AggregatedInsights  # Issue #71: Synthesized insights
    artifact_id: str | None  # Issue #72: Generated artifact ID
    evaluation_results: EvaluationResults  # Agent quality scores
    metrics: WorkflowMetrics  # Performance metrics
    # Issue #221: Hierarchical chunking results
    chunk_counts: ChunkCounts  # {"coarse": N, "fine": M, "summaries": K}
    dedup_stats: DedupStats  # {"kept": N, "dropped": M}
    # Issue #300: Proactive memory recall context
    proactive_context: str  # Formatted memory context from past analyses
    # Issue #301: Quality gate validation
    quality_scores: QualityScores  # LLM-as-judge quality scores
    quality_gate_avg_score: float  # Average quality score (0.0-1.0)
    quality_gate_passed: bool  # Whether quality gate passed
    quality_gate_retry_count: int  # Number of synthesis retries
    quality_gate_error: str  # Error message if gate evaluation failed
    # Issue #441: Workflow abort signal fields
    should_abort: bool  # True if workflow should stop early (e.g., extraction failed)
    abort_reason: str | None  # Human-readable error message explaining why workflow aborted
    extraction_status: Literal["pending", "success", "failed"]  # Track extraction node status
    extraction_error_code: (
        str | None
    )  # Error code from ExtractionErrorCode enum if extraction failed
    workflow_status: Literal["running", "completed", "failed"]  # Final workflow status
    final_error: str | None  # Final error message if workflow failed
    # Issue #544: Stage resumption skip flags (for retry/rerun from specific stages)
    skip_extraction: bool  # True to skip extraction node (data already loaded from DB)
    skip_embedding: bool  # True to skip embedding node (data already loaded from DB)
    # Issue #547 (GAP 4): Dynamic fan-in tracking
    # These fields track how many agents were ACTUALLY dispatched vs completed
    # to prevent stuck aggregation when agent counts don't match expectations
    expected_agent_count: int  # Number of agents actually dispatched by router
    dispatched_agents: list[str]  # List of agent names actually dispatched
    completed_agent_count: int  # Incremented by each agent on completion (for validation)
    # Issue #588: Sequential Tier Learning - compressed findings passed between tiers
    tier1_summary: TierSummary  # Compressed findings from Tier 1 foundational agents
    tier2_summary: TierSummary  # Compressed findings from Tier 2 technical agents
    tier3_summary: TierSummary  # Compressed findings from Tier 3 strategic agents
