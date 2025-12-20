"""Shared workflow type definitions.

This module defines TypedDict structures used across LangGraph workflows
for type-safe state management.
"""

from typing import TypedDict


class AgentFinding(TypedDict, total=False):
    """Standard structure for agent analysis findings.

    Used by all analysis agents to return structured findings
    that can be merged via LangGraph's reducer pattern.

    Attributes:
        agent_name: Name of the agent that produced this finding
        agent_type: Type/category of agent (e.g., 'tech_comparator')
        finding_type: Category of finding (e.g., 'comparison', 'security_issue')
        title: Short title for the finding
        content: Detailed content/analysis
        confidence: Confidence score (0.0-1.0)
        priority: Priority level ('high', 'medium', 'low')
        metadata: Additional key-value metadata
        recommendations: List of actionable recommendations

    """

    agent_name: str
    agent_type: str
    finding_type: str
    title: str
    content: str
    confidence: float
    priority: str  # "high" | "medium" | "low"
    metadata: dict[str, str]
    recommendations: list[str]


class WorkflowMetrics(TypedDict, total=False):
    """Performance and quality metrics for workflows.

    Tracks timing, token usage, and error counts for
    workflow execution monitoring.

    Attributes:
        start_time: Unix timestamp when workflow started
        end_time: Unix timestamp when workflow ended
        duration_ms: Total duration in milliseconds
        token_count: Total tokens used
        error_count: Number of errors encountered
        retry_count: Number of retries performed

    """

    start_time: float
    end_time: float
    duration_ms: float
    token_count: int
    error_count: int
    retry_count: int
