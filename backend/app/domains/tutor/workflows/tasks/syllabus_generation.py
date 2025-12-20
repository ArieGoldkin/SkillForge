"""Syllabus generation task with LLM prompt engineering.

Phase 2: Extracted from node for better organization.
"""

from app.core.logging import get_logger
from app.domains.tutor.workflows.config import SYLLABUS_GENERATION_PROMPT

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

    return SYLLABUS_GENERATION_PROMPT.format(
        analysis_summary=json.dumps(analysis_summary)
        if analysis_summary
        else "No analysis context",
        user_level=user_level,
    )
