"""Syllabus generation task with LLM prompt engineering.

Phase 2: Extracted from node for better organization.
Issue #414: Migrated to PromptManager with Jinja2 templates.
"""

from app.core.logging import get_logger
from app.domains.tutor.workflows.config import PROMPT_SYLLABUS_GENERATION
from app.shared.services.prompts.prompt_manager import get_prompt_manager

logger = get_logger(__name__)


async def generate_syllabus_prompt(
    analysis_summary: dict[str, object] | None,
    user_level: str,
) -> str:
    """Generate syllabus generation prompt.

    Args:
        analysis_summary: Optional analysis summary for context
        user_level: User's skill level

    Returns:
        Formatted prompt string

    """
    import json

    prompt_manager = get_prompt_manager()
    return await prompt_manager.get_prompt(
        PROMPT_SYLLABUS_GENERATION,
        variables={
            "analysis_summary": json.dumps(analysis_summary)
            if analysis_summary
            else "No analysis context",
            "user_level": user_level,
        },
    )
