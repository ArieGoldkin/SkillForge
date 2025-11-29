"""Tasks module for tutor workflow.

Contains LLM prompt engineering and context management logic.
"""

from app.workflows.tutor.tasks.context_management import (
    build_conversation_context,
    should_summarize,
    summarize_conversation,
)
from app.workflows.tutor.tasks.lesson_delivery import generate_lesson_prompt
from app.workflows.tutor.tasks.syllabus_generation import generate_syllabus_prompt

__all__ = [
    "generate_syllabus_prompt",
    "generate_lesson_prompt",
    "build_conversation_context",
    "should_summarize",
    "summarize_conversation",
]
