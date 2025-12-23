"""Shared workflow type definitions.

This module defines TypedDict structures used across LangGraph workflows
for type-safe state management.
"""

from typing import TypedDict


class AgentFinding(TypedDict, total=False):
    """Standard structure for agent analysis findings.

    Used by all analysis agents to return structured findings
    that can be merged via LangGraph's reducer pattern.

    Each agent returns findings in a nested structure where:
    - agent_type identifies which agent produced the finding
    - findings contains agent-specific structured data
    - Optional metadata fields provide additional context

    Attributes:
        agent_type: Type/category of agent (e.g., 'tech_comparator', 'security_auditor')
        findings: Agent-specific findings dictionary with structured data
        confidence_score: Optional confidence score (0.0-1.0)
        processing_time_ms: Optional processing time in milliseconds

    Example:
        {
            "agent_type": "tech_comparator",
            "findings": {
                "technologies": ["Python", "FastAPI", "PostgreSQL"],
                "comparisons": ["FastAPI vs Flask", "PostgreSQL vs MySQL"],
            },
            "processing_time_ms": 1200,
        }

    """

    agent_type: str  # Required: identifies the agent
    findings: dict[str, object]  # Required: agent-specific structured data
    confidence_score: float | None  # Optional: confidence score (0.0-1.0)
    processing_time_ms: int | None  # Optional: processing time in milliseconds


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
