"""Lesson delivery task with LLM prompt engineering.

Phase 2: Extracted from node for better organization.
"""

from app.core.logging import get_logger
from app.domains.tutor.workflows.config import LESSON_DELIVERY_PROMPT

logger = get_logger(__name__)


async def generate_lesson_prompt(
    concept: str,
    section_title: str,
    lesson_title: str,
    user_level: str,
    understanding_scores: dict[str, float],
) -> str:
    """Generate lesson delivery prompt.

    Args:
        concept: Concept being taught
        section_title: Section title
        lesson_title: Lesson title
        user_level: User's skill level
        understanding_scores: Previous understanding scores

    Returns:
        Formatted prompt string

    """
    import json

    return LESSON_DELIVERY_PROMPT.format(
        concept=concept,
        section_title=section_title,
        lesson_title=lesson_title,
        user_level=user_level,
        understanding_scores=json.dumps(understanding_scores),
    )
