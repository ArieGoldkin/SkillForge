"""Rephrase explanation node for tutor workflow.

This node provides adaptive re-explanation with hints when user is not ready.
"""

from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.tracing import robust_traceable
from app.db.repositories.tutor_message_repository import TutorMessageRepository
from app.workflows.context_compiler import create_workflow_compiler
from app.workflows.tutor.config import TUTOR_COMPACTION_CONFIG
from app.workflows.tutor.nodes.response_helpers import extract_string_content
from app.workflows.tutor.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)

# Module-level compiler (lazy init)
_tutor_compiler = None


def _get_tutor_compiler():
    """Get or create tutor compiler instance (lazy initialization)."""
    global _tutor_compiler  # noqa: PLW0603
    if _tutor_compiler is None:
        _tutor_compiler = create_workflow_compiler("tutor", config=TUTOR_COMPACTION_CONFIG)
    return _tutor_compiler


REPHRASE_EXPLANATION_PROMPT = """Rephrase the explanation to help the user understand better.

Original Concept: {concept}
User's Response: {user_response}
User Level: {user_level}
Attempt Number: {attempts}

The user didn't fully understand. Provide:
1. A simpler explanation (use analogies if helpful)
2. A hint (don't give the answer, guide them)
3. An encouraging message

Adapt based on attempt number:
- Attempt 1: Slightly simpler, one hint
- Attempt 2: Much simpler, more hints
- Attempt 3: Very simple, direct guidance (last attempt)

Return the rephrased explanation."""


@robust_traceable(
    name="rephrase_explain",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def rephrase_explain(state: TutorState) -> dict[str, object]:  # noqa: PLR0915 - Tutor node with complex logic
    """Rephrase explanation with hints when user is not ready.

    Provides simpler re-explanation with progressive hints based on
    attempt number (max 3 attempts).

    Args:
        state: Current tutor state

    Returns:
        Dictionary with last_assistant_response and attempts fields

    """
    session_id = state["session_id"]
    syllabus = state.get("syllabus")
    current_section = state.get("current_section", 0)
    current_lesson = state.get("current_lesson", 0)
    user_level = state.get("user_level", "intermediate")
    last_user_message = state.get("last_user_message", "")
    attempts = state.get("attempts_current_lesson", 0)

    # Thread grouping and runtime metadata
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            # Group all tutor messages in one thread
            run_tree.metadata["thread_id"] = str(session_id)
            run_tree.metadata["session_id"] = str(session_id)
            run_tree.metadata["conversation_id"] = str(session_id)
            # Phase-specific metadata
            run_tree.metadata["tutor_phase"] = "rephrase_explanation"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

    # Emit SSE event: rephrase started
    await _emit_tutor_event(
        session_id,
        "progress",
        "rephrase_explanation",
        "running",
        attempts=attempts,
    )

    logger.info(
        "tutor_rephrase_started",
        session_id=session_id,
        section=current_section,
        lesson=current_lesson,
        attempts=attempts,
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
        prompt = REPHRASE_EXPLANATION_PROMPT.format(
            concept=concept,
            user_response=last_user_message or "No response",
            user_level=user_level,
            attempts=attempts,
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
        rephrased = extract_string_content(response)

        # Stream rephrased explanation via SSE
        chunk_size = 50
        for i in range(0, len(rephrased), chunk_size):
            chunk = rephrased[i : i + chunk_size]
            await _emit_tutor_event(
                session_id,
                "chunk",
                "rephrase_explanation",
                "streaming",
                content=chunk,
            )

        # Save assistant message to database
        from uuid import UUID

        from app.db.session import get_session_factory

        session_factory = get_session_factory()
        async with session_factory() as db_session:
            repo = TutorMessageRepository(session=db_session)
            message = await repo.save_message(
                UUID(session_id),
                role="assistant",
                content=rephrased,
                message_metadata={
                    "phase": "rephrase_explanation",
                    "section": current_section,
                    "lesson": current_lesson,
                    "attempts": attempts,
                },
            )
            saved_message = message

        # Emit SSE event: rephrase complete
        await _emit_tutor_event(
            session_id,
            "done",
            "rephrase_explanation",
            "complete",
            phase="rephrase_explanation",
            attempts=attempts,
        )

        logger.info(
            "tutor_rephrase_complete",
            session_id=session_id,
            attempts=attempts,
        )

        # Update conversation history in state
        conversation_history = state.get("conversation_history", [])
        updated_history = [
            *conversation_history,
            {
                "role": "assistant",
                "content": rephrased,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {
                    "phase": "rephrase_explanation",
                    "section": current_section,
                    "lesson": current_lesson,
                    "attempts": attempts,
                },
            },
        ]

        # Return only updated fields
        return {
            "last_assistant_response": rephrased,
            "current_phase": "socratic_questioning",  # Ask question again after rephrasing
            "conversation_history": updated_history,
        }

    except Exception as e:
        # Emit SSE event: rephrase failed
        await _emit_tutor_event(
            session_id,
            "error",
            "rephrase_explanation",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_rephrase_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
