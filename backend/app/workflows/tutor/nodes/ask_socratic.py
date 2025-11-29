"""Ask Socratic question node for tutor workflow.

This node generates contextual Socratic questions based on user level.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.workflows.tutor.config import SOCRATIC_QUESTION_PROMPT
from app.workflows.tutor.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)


@traceable(
    name="ask_socratic",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
)
async def ask_socratic(state: TutorState) -> dict[str, object]:
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
            if current_section < len(sections):
                section = sections[current_section]
                if isinstance(section, dict):
                    lessons = section.get("lessons", [])
                    if current_lesson < len(lessons):
                        lesson = lessons[current_lesson]
                        if isinstance(lesson, dict):
                            concept = lesson.get("concept", concept)

        # Build prompt
        prompt = SOCRATIC_QUESTION_PROMPT.format(
            concept=concept,
            user_response=last_user_message or "No response yet",
            user_level=user_level,
        )

        # Get LLM model
        model = get_chat_model()

        # Generate Socratic question
        messages = [
            SystemMessage(
                content=(
                    "You are a Socratic tutor. "
                    "Ask thoughtful questions that guide learning through discovery."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = await model.ainvoke(messages)
        question = response.content if hasattr(response, "content") else str(response)

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
        updated_history = conversation_history + [
            {
                "role": "assistant",
                "content": question,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {
                    "phase": "socratic_questioning",
                    "section": current_section,
                    "lesson": current_lesson,
                },
            }
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
