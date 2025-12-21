"""Workflow-specific context compiler factory.

Provides preset configurations for different workflow types (tutor, analysis).
Each workflow has specific system prompts and compaction settings.

Reference: Sprint 11 - Context Engineering (#247)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domains.analysis.services.context.compiler import ContextCompiler

if TYPE_CHECKING:
    from app.domains.analysis.services.context.compaction import CompactionConfig

# Tutor workflow system prompt
TUTOR_SYSTEM_PROMPT = """You are an expert Socratic tutor helping students learn new concepts.

Your teaching approach:
1. Ask guiding questions before giving answers
2. Adapt complexity to the student's level
3. Use analogies and concrete examples
4. Encourage critical thinking and discovery
5. Be patient and supportive

Always maintain a conversational, encouraging tone."""

# Analysis workflow system prompt
ANALYSIS_SYSTEM_PROMPT = """You are a technical content analysis expert.

Your role:
1. Analyze technical content thoroughly
2. Extract key concepts and dependencies
3. Identify learning objectives
4. Assess complexity and prerequisites
5. Provide structured, actionable insights

Maintain objectivity and technical accuracy."""


def create_workflow_compiler(
    workflow_type: str,
    config: CompactionConfig | None = None,
) -> ContextCompiler:
    """Create context compiler for specific workflow type.

    Factory function that provides preset configurations for different
    workflow types with appropriate system prompts and settings.

    Args:
        workflow_type: Type of workflow ("tutor" or "analysis")
        config: Optional compaction config, uses defaults if None

    Returns:
        Configured ContextCompiler instance

    Raises:
        ValueError: If workflow_type is not recognized

    """
    if workflow_type == "tutor":
        return ContextCompiler(
            system_prompt=TUTOR_SYSTEM_PROMPT,
            agent_identity="You are a patient, encouraging tutor focused on student growth.",
            config=config,
        )

    if workflow_type == "analysis":
        return ContextCompiler(
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            agent_identity="You are a precise technical analyst focused on actionable insights.",
            config=config,
        )

    error_msg = f"Unknown workflow type: {workflow_type}. Must be 'tutor' or 'analysis'."
    raise ValueError(error_msg)
