"""Conduct section review node for tutor workflow.

This node conducts a section quiz with feedback to evaluate understanding.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import traceable

from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.db.repositories.tutor_message_repository import TutorMessageRepository
from app.db.session import get_session_factory
from app.workflows.tutor.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)

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


@traceable(
    name="conduct_review",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
)
async def conduct_review(state: TutorState) -> dict[str, object]:
    """Conduct section review quiz with feedback.

    Creates a quiz covering section concepts and evaluates user responses.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with review results and next phase

    """
    session_id = state["session_id"]
    syllabus = state.get("syllabus")
    current_section = state.get("current_section", 0)
    user_level = state.get("user_level", "intermediate")
    understanding_scores = state.get("understanding_scores", {})

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
            raise ValueError("Syllabus not found or invalid")

        sections = syllabus.get("sections", [])
        if current_section >= len(sections):
            raise ValueError(f"Section {current_section} not found")

        section = sections[current_section]
        if not isinstance(section, dict):
            raise ValueError(f"Section {current_section} is invalid")

        section_title = section.get("title", "Unknown Section")
        lessons = section.get("lessons", [])
        concepts = [lesson.get("concept", "") for lesson in lessons if isinstance(lesson, dict)]

        # Build prompt
        prompt = SECTION_REVIEW_PROMPT.format(
            section_title=section_title,
            concepts=", ".join(concepts),
            user_level=user_level,
            understanding_scores=str(understanding_scores),
        )

        # Get LLM model
        model = get_chat_model()

        # Generate review quiz
        messages = [
            SystemMessage(
                content="You are an expert educator. Create effective quizzes that assess understanding and provide learning feedback."
            ),
            HumanMessage(content=prompt),
        ]

        response = await model.ainvoke(messages)
        review_content = response.content if hasattr(response, "content") else str(response)

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
        updated_history = conversation_history + [
            {
                "role": "assistant",
                "content": review_content,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {"phase": "section_review", "section": current_section},
            }
        ]

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
