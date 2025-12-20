"""Type definitions for analysis workflow state.

This module defines TypedDict structures for the AnalysisState fields,
providing type safety for LangGraph state management.
"""

from typing import TypedDict


class ExtractionMetadata(TypedDict, total=False):
    """Metadata from content extraction.

    Attributes:
        title: Document/page title
        word_count: Total word count
        author: Author name if available
        source_type: Type of source (article, video, repo)
        language: Content language
        publish_date: Publication date if available
        description: Meta description
        keywords: Extracted keywords

    """

    title: str
    word_count: int
    author: str | None
    source_type: str
    language: str
    publish_date: str | None
    description: str
    keywords: list[str]


class SupervisorDecision(TypedDict, total=False):
    """Supervisor agent's decision on which agents to run.

    Attributes:
        selected_agents: List of agent names to execute
        reasoning: Explanation for agent selection
        confidence: Confidence score (0.0-1.0)
        context_used: Context factors used in decision
        priority_order: Execution priority order

    """

    selected_agents: list[str]
    reasoning: str
    confidence: float
    context_used: list[str]
    priority_order: list[str]


class AggregatedInsights(TypedDict, total=False):
    """Synthesized insights from all agents.

    Attributes:
        executive_summary: High-level summary
        key_findings: List of key findings
        synthesis: Detailed synthesis text
        core_concepts: List of core concepts with descriptions
        recommendations: Actionable recommendations
        tldr: Short summary
        ai_assistant_prompt: Prompt for AI assistant
        diagrams: Mermaid diagram definitions
        glossary: Term definitions

    """

    executive_summary: str
    key_findings: list[str]
    synthesis: str
    core_concepts: list[dict[str, str]]
    recommendations: list[str]
    tldr: str
    ai_assistant_prompt: str
    diagrams: list[str]
    glossary: dict[str, str]


class QualityScores(TypedDict, total=False):
    """Quality gate scores from LLM-as-judge evaluation.

    Attributes:
        relevance: Relevance score (0.0-1.0)
        depth: Depth of analysis score (0.0-1.0)
        coherence: Coherence score (0.0-1.0)
        avg_score: Average of all scores
        passed: Whether quality gate passed
        retry_count: Number of synthesis retries
        error: Error message if evaluation failed

    """

    relevance: float
    depth: float
    coherence: float
    avg_score: float
    passed: bool
    retry_count: int
    error: str | None


class EvaluationResults(TypedDict, total=False):
    """Agent quality evaluation results.

    Attributes:
        agent_scores: Per-agent quality scores
        overall_score: Overall quality score
        feedback: Evaluation feedback text
        improvements: Suggested improvements

    """

    agent_scores: dict[str, float]
    overall_score: float
    feedback: str
    improvements: list[str]


class ChunkCounts(TypedDict, total=False):
    """Hierarchical chunking result counts.

    Attributes:
        coarse: Number of coarse chunks
        fine: Number of fine chunks
        summaries: Number of summary chunks

    """

    coarse: int
    fine: int
    summaries: int


class DedupStats(TypedDict, total=False):
    """Deduplication statistics.

    Attributes:
        kept: Number of chunks kept
        dropped: Number of duplicate chunks dropped

    """

    kept: int
    dropped: int

