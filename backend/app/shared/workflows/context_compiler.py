"""Workflow-specific context compiler factory.

Provides preset configurations for different workflow types (tutor, analysis).
Each workflow has specific system prompts and compaction settings.

Reference: Sprint 11 - Context Engineering (#247)
Issue #414: Migrated TUTOR_SYSTEM_PROMPT and ANALYSIS_SYSTEM_PROMPT to Jinja2 templates.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.domains.analysis.services.context.compiler import ContextCompiler
from app.shared.services.prompts.prompt_manager import get_prompt_manager

if TYPE_CHECKING:
    from app.domains.analysis.services.context.compaction import CompactionConfig


async def create_workflow_compiler(
    workflow_type: str,
    config: CompactionConfig | None = None,
) -> ContextCompiler:
    """Create context compiler for specific workflow type.

    Issue #414: Now uses PromptManager with Jinja2 templates.

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
    prompt_manager = get_prompt_manager()

    if workflow_type == "tutor":
        system_prompt = await prompt_manager.get_prompt(name="system-tutor")
        return ContextCompiler(
            system_prompt=system_prompt,
            agent_identity="You are a patient, encouraging tutor focused on student growth.",
            config=config,
        )

    if workflow_type == "analysis":
        system_prompt = await prompt_manager.get_prompt(name="system-analysis")
        return ContextCompiler(
            system_prompt=system_prompt,
            agent_identity="You are a precise technical analyst focused on actionable insights.",
            config=config,
        )

    error_msg = f"Unknown workflow type: {workflow_type}. Must be 'tutor' or 'analysis'."
    raise ValueError(error_msg)
