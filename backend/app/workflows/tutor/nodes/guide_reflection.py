"""Guide reflection node for tutor workflow.

This node provides real-world application suggestions and marks session as completed.
"""

from app.workflows.context_compiler import create_workflow_compiler
from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.tracing import robust_traceable
from app.db.repositories.tutor_message_repository import TutorMessageRepository
from app.db.repositories.tutor_session_repository import TutorSessionRepository
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


REFLECTION_PROMPT = """Guide the user in reflecting on their learning and applying concepts.

Syllabus: {syllabus_summary}
Understanding Scores: {understanding_scores}

Provide:
1. Real-world applications of the concepts learned
2. Next steps for continued learning
3. Resources for deeper exploration
4. Encouragement and reflection questions

Help the user connect concepts to practice and plan their continued learning journey."""


@robust_traceable(
    name="guide_reflection",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def guide_reflection(state: TutorState) -> dict[str, object]:
    """Guide user reflection and mark session as completed.

    Provides real-world application suggestions and marks the session
    as completed.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with reflection content and completion status

    """
    session_id = state["session_id"]
    syllabus = state.get("syllabus")
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
            run_tree.metadata["tutor_phase"] = "reflection"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

    await _emit_tutor_event(
        session_id,
        "progress",
        "reflection",
        "running",
    )

    logger.info(
        "tutor_reflection_started",
        session_id=session_id,
    )

    try:
        # Build syllabus summary
        syllabus_summary = "All concepts covered"
        if syllabus and isinstance(syllabus, dict):
            sections = syllabus.get("sections", [])
            if isinstance(sections, list):
                section_titles = [s.get("title", "") for s in sections if isinstance(s, dict)]
                syllabus_summary = f"Completed: {', '.join(section_titles)}"

        # Build prompt
        prompt = REFLECTION_PROMPT.format(
            syllabus_summary=syllabus_summary,
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
        reflection = extract_string_content(response)

        # Stream reflection via SSE
        chunk_size = 50
        for i in range(0, len(reflection), chunk_size):
            chunk = reflection[i : i + chunk_size]
            await _emit_tutor_event(
                session_id,
                "chunk",
                "reflection",
                "streaming",
                content=chunk,
            )

        # Save assistant message and mark session as completed
        from uuid import UUID

        from app.db.session import get_session_factory

        session_factory = get_session_factory()
        async with session_factory() as db_session:
            message_repo = TutorMessageRepository(session=db_session)
            session_repo = TutorSessionRepository(session=db_session)

            message = await message_repo.save_message(
                UUID(session_id),
                role="assistant",
                content=reflection,
                message_metadata={"phase": "reflection"},
            )
            saved_message = message

            # Mark session as completed
            await session_repo.update_session_state(
                UUID(session_id),
                status="completed",
                current_phase="completed",
            )

        # Update conversation history
        conversation_history = state.get("conversation_history", [])
        updated_history = [
            *conversation_history,
            {
                "role": "assistant",
                "content": reflection,
                "created_at": saved_message.created_at.isoformat(),
                "metadata": {"phase": "reflection"},
            },
        ]

        await _emit_tutor_event(
            session_id,
            "done",
            "reflection",
            "complete",
            phase="completed",
        )

        logger.info(
            "tutor_reflection_complete",
            session_id=session_id,
        )

        return {
            "last_assistant_response": reflection,
            "current_phase": "completed",
            "conversation_history": updated_history,
        }

    except Exception as e:
        await _emit_tutor_event(
            session_id,
            "error",
            "reflection",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_reflection_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
