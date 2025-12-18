"""Conduct section review node for tutor workflow.

This node conducts a section quiz with feedback to evaluate understanding.
"""

from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.tracing import robust_traceable
from app.domains.tutor.repositories.message_repository import TutorMessageRepository
from app.domains.tutor.workflows.config import TUTOR_COMPACTION_CONFIG
from app.domains.tutor.workflows.nodes.response_helpers import extract_string_content
from app.domains.tutor.workflows.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.domains.tutor.workflows.state import TutorState
from app.domains.tutor.workflows.state_accessors import get_syllabus
from app.shared.types import TutorMessage
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


SECTION_REVIEW_PROMPT = """Create a section review quiz to assess understanding.

Section: {section_title}
Concepts Covered: {concepts}
User Level: {user_level}
Understanding Scores: {understanding_scores}

Create a quiz with 3-5 questions that:
1. Test key concepts from this section
2. Are appropriate for the user's level
3. Provide immediate feedback
4. Identify areas needing reinforcement

Return as structured quiz with questions and answer keys."""


@robust_traceable(
    name="conduct_review",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def conduct_review(state: TutorState) -> dict[str, object]:  # noqa: PLR0915 - Tutor node with complex logic
    """Conduct section review quiz with feedback.

    Creates a quiz covering section concepts and evaluates user responses.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with review results and next phase

    """
    session_id = state["session_id"]
    syllabus = get_syllabus(state)
    current_section = state.get("current_section", 0)
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
            run_tree.metadata["tutor_phase"] = "section_review"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

    # Emit SSE event: review started
    await _emit_tutor_event(
        session_id,
        "progress",
        "section_review",
        "running",
        section=current_section,
    )

    logger.info(
        "tutor_section_review_started",
        session_id=session_id,
        section=current_section,
    )

    try:
        # Get section information
        if not syllabus or not isinstance(syllabus, dict):
            msg = "Syllabus not found or invalid"
            raise ValueError(msg)

        sections = syllabus.get("sections", [])
        if not isinstance(sections, list) or current_section >= len(sections):
            msg = f"Section {current_section} not found"
            raise ValueError(msg)

        section = sections[current_section]
        if not isinstance(section, dict):
            msg = f"Section {current_section} is invalid"
            raise TypeError(msg)

        section_title = section.get("title", "Unknown Section")
        lessons = section.get("lessons", [])
        if not isinstance(lessons, list):
            lessons = []
        concepts = [
            str(lesson.get("concept", "")) for lesson in lessons if isinstance(lesson, dict)
        ]

        # Build prompt
        prompt = SECTION_REVIEW_PROMPT.format(
            section_title=section_title,
            concepts=", ".join(concepts),
            user_level=user_level,
            understanding_scores=str(understanding_scores),
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
        review_content = extract_string_content(response)

        # Stream review via SSE
        chunk_size = 50
        for i in range(0, len(review_content), chunk_size):
            chunk = review_content[i : i + chunk_size]
            await _emit_tutor_event(
                session_id,
                "chunk",
                "section_review",
                "streaming",
                content=chunk,
            )

        # Save assistant message
        from uuid import UUID

        from app.db.session import get_session_factory

        session_factory = get_session_factory()
        async with session_factory() as db_session:
            repo = TutorMessageRepository(session=db_session)
            message = await repo.save_message(
                UUID(session_id),
                role="assistant",
                content=review_content,
                message_metadata={"phase": "section_review", "section": current_section},
            )
            saved_message = message

        # Update conversation history
        conversation_history = state.get("conversation_history", [])
        new_message: TutorMessage = {
            "role": "assistant",
            "content": review_content,
            "created_at": saved_message.created_at.isoformat(),
            "metadata": {"phase": "section_review", "section": current_section},
        }
        updated_history: list[TutorMessage] = [*conversation_history, new_message]

        # Emit SSE event: review complete
        await _emit_tutor_event(
            session_id,
            "done",
            "section_review",
            "complete",
            phase="section_review",
            section=current_section,
        )

        logger.info(
            "tutor_section_review_complete",
            session_id=session_id,
            section=current_section,
        )

        # Return updated fields
        return {
            "last_assistant_response": review_content,
            "current_phase": "section_review",
            "conversation_history": updated_history,
        }

    except Exception as e:
        await _emit_tutor_event(
            session_id,
            "error",
            "section_review",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_section_review_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
