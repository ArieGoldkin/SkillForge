"""Final challenge node for tutor workflow.

This node presents an integrative problem combining multiple concepts.
Issue #414: Migrated to PromptManager with Jinja2 templates.
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable, update_current_trace
from app.domains.tutor.repositories.message_repository import TutorMessageRepository
from app.domains.tutor.workflows.config import TUTOR_COMPACTION_CONFIG
from app.domains.tutor.workflows.nodes.response_helpers import extract_string_content
from app.domains.tutor.workflows.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.domains.tutor.workflows.state import TutorState
from app.domains.tutor.workflows.state_accessors import get_syllabus
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.context_compiler import create_workflow_compiler

logger = get_logger(__name__)

# Module-level compiler (lazy init)
_tutor_compiler = None

# Prompt name for PromptManager
PROMPT_NAME = "tutor-final-challenge"


def _get_tutor_compiler():
    """Get or create tutor compiler instance (lazy initialization)."""
    global _tutor_compiler  # noqa: PLW0603
    if _tutor_compiler is None:
        _tutor_compiler = create_workflow_compiler("tutor", config=TUTOR_COMPACTION_CONFIG)
    return _tutor_compiler


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
    syllabus = get_syllabus(state)
    user_level = state.get("user_level", "intermediate")
    understanding_scores = state.get("understanding_scores", {})

    # Thread grouping and runtime metadata
    # Thread grouping and runtime metadata for Langfuse
    update_current_trace(
        metadata={
            "thread_id": str(session_id),
            "conversation_id": str(session_id),
            "tutor_phase": "final_challenge",
        },
        session_id=str(session_id),
        user_id="anonymous",
    )

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

        # Build prompt using PromptManager
        prompt_manager = get_prompt_manager()
        prompt = await prompt_manager.get_prompt(
            PROMPT_NAME,
            variables={
                "syllabus_summary": syllabus_summary,
                "user_level": user_level,
                "understanding_scores": str(understanding_scores),
            },
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
