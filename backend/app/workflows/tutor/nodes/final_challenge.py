"""Final challenge node for tutor workflow.

This node presents an integrative problem combining multiple concepts.
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.tracing import robust_traceable
from app.db.repositories.tutor_message_repository import TutorMessageRepository
from app.workflows.tutor.nodes.response_helpers import extract_string_content
from app.workflows.tutor.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)

FINAL_CHALLENGE_PROMPT = """Create a final integrative challenge problem.

Syllabus: {syllabus_summary}
User Level: {user_level}
Understanding Scores: {understanding_scores}

Create a challenging problem that:
1. Combines concepts from multiple sections
2. Tests overall understanding
3. Requires synthesis and application
4. Is appropriate for the user's level

Return a problem statement with clear instructions."""


@robust_traceable(
    name="final_challenge",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def final_challenge(state: TutorState) -> dict[str, object]:
    """Present final integrative challenge.

    Creates a problem that combines concepts from all sections to test
    overall understanding.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with challenge content and phase update

    """
    session_id = state["session_id"]
    syllabus = state.get("syllabus")
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
            run_tree.metadata["tutor_phase"] = "final_challenge"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

    await _emit_tutor_event(
        session_id,
        "progress",
        "final_challenge",
        "running",
    )

    logger.info(
        "tutor_final_challenge_started",
        session_id=session_id,
    )

    try:
        # Build syllabus summary
        syllabus_summary = "All sections completed"
        if syllabus and isinstance(syllabus, dict):
            sections = syllabus.get("sections", [])
            if isinstance(sections, list):
                section_titles = [s.get("title", "") for s in sections if isinstance(s, dict)]
                syllabus_summary = f"Sections: {', '.join(section_titles)}"

        # Build prompt
        prompt = FINAL_CHALLENGE_PROMPT.format(
            syllabus_summary=syllabus_summary,
            user_level=user_level,
            understanding_scores=str(understanding_scores),
        )

        # Get LLM model
        model = get_chat_model()

        # Generate challenge
        messages = [
            SystemMessage(
                content=(
                    "You are an expert educator. "
                    "Create integrative challenges that test deep understanding."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = await model.ainvoke(messages)
        challenge = extract_string_content(response)

        # Stream challenge via SSE
        chunk_size = 50
        for i in range(0, len(challenge), chunk_size):
            chunk = challenge[i : i + chunk_size]
            await _emit_tutor_event(
                session_id,
                "chunk",
                "final_challenge",
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
                content=challenge,
                message_metadata={"phase": "final_challenge"},
            )
            saved_message = message

        # Update conversation history
        conversation_history = state.get("conversation_history", [])
        updated_history = [
            *conversation_history,
            {
                "role": "assistant",
                "content": challenge,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {"phase": "final_challenge"},
            },
        ]

        await _emit_tutor_event(
            session_id,
            "done",
            "final_challenge",
            "complete",
            phase="final_challenge",
        )

        logger.info(
            "tutor_final_challenge_complete",
            session_id=session_id,
        )

        return {
            "last_assistant_response": challenge,
            "current_phase": "reflection",
            "conversation_history": updated_history,
        }

    except Exception as e:
        await _emit_tutor_event(
            session_id,
            "error",
            "final_challenge",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_final_challenge_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
