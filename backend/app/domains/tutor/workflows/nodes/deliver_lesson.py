"""Deliver lesson node for tutor workflow.

This node teaches a concept with explanation, analogy, example, and exercise.
"""

import json

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable, update_current_trace
from app.domains.tutor.workflows.config import PROMPT_LESSON_DELIVERY, TUTOR_COMPACTION_CONFIG
from app.domains.tutor.workflows.nodes.response_helpers import extract_string_content
from app.domains.tutor.workflows.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.domains.tutor.workflows.state import TutorState
from app.domains.tutor.workflows.state_accessors import (
    get_syllabus,
    get_understanding_scores,
)
from app.shared.workflows.context_compiler import create_workflow_compiler

logger = get_logger(__name__)

# Module-level compiler (lazy init)
_tutor_compiler = None


def _get_tutor_compiler():
    """Get or create tutor compiler instance (lazy initialization)."""
    global _tutor_compiler  # noqa: PLW0603
    if _tutor_compiler is None:
        _tutor_compiler = create_workflow_compiler("tutor", config=TUTOR_COMPACTION_CONFIG)
    return _tutor_compiler


@robust_traceable(
    name="deliver_lesson",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def deliver_lesson(state: TutorState) -> dict[str, object]:  # noqa: PLR0915 - Tutor node with complex logic
    """Deliver lesson content for current section/lesson.

    Teaches the concept with explanation, analogy, example, and exercise.
    Streams content via SSE as it's generated.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with last_assistant_response field

    """
    session_id = state["session_id"]
    syllabus = get_syllabus(state)
    current_section = state.get("current_section", 0)
    current_lesson = state.get("current_lesson", 0)
    user_level = state.get("user_level", "intermediate")
    understanding_scores = get_understanding_scores(state)

    # Thread grouping and runtime metadata
    # Thread grouping and runtime metadata for Langfuse
    update_current_trace(
        metadata={
            "thread_id": str(session_id),
            "conversation_id": str(session_id),
            "tutor_phase": "lesson_delivery",
        },
        session_id=str(session_id),
        user_id="anonymous",
    )

    # Emit SSE event: lesson delivery started
    await _emit_tutor_event(
        session_id,
        "progress",
        "lesson_delivery",
        "running",
        section=current_section,
        lesson=current_lesson,
    )

    logger.info(
        "tutor_lesson_delivery_started",
        session_id=session_id,
        section=current_section,
        lesson=current_lesson,
    )

    try:
        # Get current lesson from syllabus
        if not syllabus or not isinstance(syllabus, dict):
            msg = "Syllabus not found or invalid"
            raise ValueError(msg)

        sections = syllabus.get("sections", [])
        if not isinstance(sections, list) or current_section >= len(sections):
            msg = f"Section {current_section} not found in syllabus"
            raise ValueError(msg)

        section = sections[current_section]
        if not isinstance(section, dict):
            msg = f"Section {current_section} is invalid"
            raise TypeError(msg)

        lessons = section.get("lessons", [])
        if not isinstance(lessons, list) or current_lesson >= len(lessons):
            msg = f"Lesson {current_lesson} not found in section {current_section}"
            raise ValueError(msg)

        lesson = lessons[current_lesson]
        if not isinstance(lesson, dict):
            msg = f"Lesson {current_lesson} is invalid"
            raise TypeError(msg)

        concept = lesson.get("concept", "Unknown concept")
        section_title = section.get("title", "Unknown section")
        lesson_title = lesson.get("title", "Unknown lesson")

        # Build prompt
        prompt = PROMPT_LESSON_DELIVERY.format(
            concept=concept,
            section_title=section_title,
            lesson_title=lesson_title,
            user_level=user_level,
            understanding_scores=json.dumps(understanding_scores),
        )

        # Get LLM model and compiler
        model = get_chat_model()
        compiler = _get_tutor_compiler()

        # Get conversation history for context compaction (Issue #270)
        conversation_history = state.get("conversation_history", [])

        # Compile context with history compaction
        messages = await compiler.compile_for_invocation(
            session_history=conversation_history,
            current_input=prompt,
            injected_memory=None,  # Future RAG integration point
        )

        config = create_runnable_config()
        response = await model.ainvoke(messages, config=config)
        lesson_content = extract_string_content(response)

        # Stream lesson content via SSE (chunked)
        chunk_size = 50
        for i in range(0, len(lesson_content), chunk_size):
            chunk = lesson_content[i : i + chunk_size]
            await _emit_tutor_event(
                session_id,
                "chunk",
                "lesson_delivery",
                "streaming",
                content=chunk,
            )

        # Save assistant message to database
        from uuid import UUID

        from app.db.session import get_session_factory
        from app.domains.tutor.repositories.message_repository import TutorMessageRepository

        session_factory = get_session_factory()
        async with session_factory() as db_session:
            repo = TutorMessageRepository(session=db_session)
            message = await repo.save_message(
                UUID(session_id),
                role="assistant",
                content=lesson_content,
                message_metadata={
                    "phase": "lesson_delivery",
                    "section": current_section,
                    "lesson": current_lesson,
                },
            )
            saved_message = message

        # Emit SSE event: lesson delivery complete
        await _emit_tutor_event(
            session_id,
            "done",
            "lesson_delivery",
            "complete",
            phase="lesson_delivery",
            progress={"section": current_section, "lesson": current_lesson},
        )

        logger.info(
            "tutor_lesson_delivery_complete",
            session_id=session_id,
            section=current_section,
            lesson=current_lesson,
        )

        # Update conversation history in state
        conversation_history = state.get("conversation_history", [])
        updated_history = [
            *conversation_history,
            {
                "role": "assistant",
                "content": lesson_content,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {
                    "phase": "lesson_delivery",
                    "section": current_section,
                    "lesson": current_lesson,
                },
            },
        ]

        # Return only updated fields
        return {
            "last_assistant_response": lesson_content,
            "current_phase": "socratic_questioning",
            "conversation_history": updated_history,
        }

    except Exception as e:
        # Emit SSE event: lesson delivery failed
        await _emit_tutor_event(
            session_id,
            "error",
            "lesson_delivery",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_lesson_delivery_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
