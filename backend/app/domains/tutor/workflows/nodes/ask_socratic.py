"""Ask Socratic question node for tutor workflow.

This node generates contextual Socratic questions based on user level.
"""

from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.tracing import robust_traceable
from app.shared.workflows.context_compiler import create_workflow_compiler
from app.domains.tutor.workflows.config import SOCRATIC_QUESTION_PROMPT, TUTOR_COMPACTION_CONFIG
from app.domains.tutor.workflows.nodes.response_helpers import extract_string_content
from app.domains.tutor.workflows.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.domains.tutor.workflows.state import TutorState

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
    name="ask_socratic",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def ask_socratic(state: TutorState) -> dict[str, object]:  # noqa: PLR0915 - Tutor node with complex logic
    """Generate Socratic question based on lesson and user response.

    Questions are adaptive:
    - Beginners: Check understanding before explanation
    - Intermediate/Advanced: Challenge thinking after explanation

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
    last_user_message = state.get("last_user_message", "")

    # Thread grouping and runtime metadata
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            # Group all tutor messages in one thread
            run_tree.metadata["thread_id"] = str(session_id)
            run_tree.metadata["session_id"] = str(session_id)
            run_tree.metadata["conversation_id"] = str(session_id)
            # Phase-specific metadata
            run_tree.metadata["tutor_phase"] = "socratic_questioning"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

    # Emit SSE event: Socratic questioning started
    await _emit_tutor_event(
        session_id,
        "progress",
        "socratic_questioning",
        "running",
    )

    logger.info(
        "tutor_socratic_questioning_started",
        session_id=session_id,
        section=current_section,
        lesson=current_lesson,
    )

    try:
        # Get current lesson concept
        concept = "the current lesson"
        if syllabus and isinstance(syllabus, dict):
            sections = syllabus.get("sections", [])
            if isinstance(sections, list) and current_section < len(sections):
                section = sections[current_section]
                if isinstance(section, dict):
                    lessons = section.get("lessons", [])
                    if isinstance(lessons, list) and current_lesson < len(lessons):
                        lesson = lessons[current_lesson]
                        if isinstance(lesson, dict):
                            concept = lesson.get("concept", concept)

        # Build prompt
        prompt = SOCRATIC_QUESTION_PROMPT.format(
            concept=concept,
            user_response=last_user_message or "No response yet",
            user_level=user_level,
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

        response = await model.ainvoke(messages)
        question = extract_string_content(response)

        # Stream question via SSE
        chunk_size = 50
        for i in range(0, len(question), chunk_size):
            chunk = question[i : i + chunk_size]
            await _emit_tutor_event(
                session_id,
                "chunk",
                "socratic_questioning",
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
                content=question,
                message_metadata={
                    "phase": "socratic_questioning",
                    "section": current_section,
                    "lesson": current_lesson,
                },
            )
            saved_message = message

        # Emit SSE event: Socratic questioning complete
        await _emit_tutor_event(
            session_id,
            "done",
            "socratic_questioning",
            "complete",
            phase="socratic_questioning",
        )

        logger.info(
            "tutor_socratic_questioning_complete",
            session_id=session_id,
        )

        # Update conversation history in state
        conversation_history = state.get("conversation_history", [])
        updated_history = [
            *conversation_history,
            {
                "role": "assistant",
                "content": question,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {
                    "phase": "socratic_questioning",
                    "section": current_section,
                    "lesson": current_lesson,
                },
            },
        ]

        # Return only updated fields
        return {
            "last_assistant_response": question,
            "current_phase": "readiness_assessment",
            "conversation_history": updated_history,
        }

    except Exception as e:
        # Emit SSE event: Socratic questioning failed
        await _emit_tutor_event(
            session_id,
            "error",
            "socratic_questioning",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_socratic_questioning_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
