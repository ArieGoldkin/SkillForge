"""Deliver lesson node for tutor workflow.

This node teaches a concept with explanation, analogy, example, and exercise.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.tracing import robust_traceable
from app.workflows.tutor.config import LESSON_DELIVERY_PROMPT
from app.workflows.tutor.nodes.response_helpers import extract_string_content
from app.workflows.tutor.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)


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
async def deliver_lesson(state: TutorState) -> dict[str, object]:
    """Deliver lesson content for current section/lesson.

    Teaches the concept with explanation, analogy, example, and exercise.
    Streams content via SSE as it's generated.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with last_assistant_response field

    """
    session_id = state["session_id"]
    syllabus = state.get("syllabus")
    current_section = state.get("current_section", 0)
    current_lesson = state.get("current_lesson", 0)
    user_level = state.get("user_level", "intermediate")
    understanding_scores = state.get("understanding_scores", {})

    # Thread grouping and runtime metadata
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            # Group all tutor messages in one thread
            run_tree.metadata["thread_id"] = str(session_id)
            run_tree.metadata["session_id"] = str(session_id)
            run_tree.metadata["conversation_id"] = str(session_id)
            # Phase-specific metadata
            run_tree.metadata["tutor_phase"] = "lesson_delivery"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

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
            raise ValueError("Syllabus not found or invalid")

        sections = syllabus.get("sections", [])
        if not isinstance(sections, list) or current_section >= len(sections):
            raise ValueError(f"Section {current_section} not found in syllabus")

        section = sections[current_section]
        if not isinstance(section, dict):
            raise ValueError(f"Section {current_section} is invalid")

        lessons = section.get("lessons", [])
        if not isinstance(lessons, list) or current_lesson >= len(lessons):
            raise ValueError(f"Lesson {current_lesson} not found in section {current_section}")

        lesson = lessons[current_lesson]
        if not isinstance(lesson, dict):
            raise ValueError(f"Lesson {current_lesson} is invalid")

        concept = lesson.get("concept", "Unknown concept")
        section_title = section.get("title", "Unknown section")
        lesson_title = lesson.get("title", "Unknown lesson")

        # Build prompt
        prompt = LESSON_DELIVERY_PROMPT.format(
            concept=concept,
            section_title=section_title,
            lesson_title=lesson_title,
            user_level=user_level,
            understanding_scores=json.dumps(understanding_scores),
        )

        # Get LLM model
        model = get_chat_model()

        # Generate lesson content
        messages = [
            SystemMessage(
                content=(
                    "You are an expert tutor. "
                    "Deliver clear, engaging lessons adapted to the user's level."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = await model.ainvoke(messages)
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

        from app.db.repositories.tutor_message_repository import TutorMessageRepository
        from app.db.session import get_session_factory

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
        updated_history = conversation_history + [
            {
                "role": "assistant",
                "content": lesson_content,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {
                    "phase": "lesson_delivery",
                    "section": current_section,
                    "lesson": current_lesson,
                },
            }
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
