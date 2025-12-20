"""Assess readiness node for tutor workflow.

This node evaluates user understanding using LLM-based assessment.
"""

import json
from datetime import UTC, datetime

from langchain_core.output_parsers import JsonOutputParser

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable, update_current_trace
from app.db.session import get_session_factory
from app.domains.tutor.repositories.session_repository import TutorSessionRepository
from app.domains.tutor.schemas.assessment import ReadinessAssessment
from app.domains.tutor.workflows.config import READINESS_ASSESSMENT_PROMPT, TUTOR_COMPACTION_CONFIG
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


@robust_traceable(
    name="assess_readiness",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def assess_readiness(state: TutorState) -> dict[str, object]:  # noqa: PLR0912, PLR0915 - Complex assessment logic
    """Assess user readiness using LLM-based evaluation.

    Evaluates understanding based on user response and updates
    understanding_scores. Returns user_ready boolean.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with user_ready, understanding_scores, and attempts fields

    """
    session_id = state["session_id"]
    syllabus = get_syllabus(state)
    current_section = state.get("current_section", 0)
    current_lesson = state.get("current_lesson", 0)
    last_user_message = state.get("last_user_message", "")
    understanding_scores = state.get("understanding_scores", {})
    attempts = state.get("attempts_current_lesson", 0)

    # Thread grouping and runtime metadata
    update_current_trace(
        metadata={
            "thread_id": str(session_id),
            "session_id": str(session_id),
            "conversation_id": str(session_id),
            "tutor_phase": "readiness_assessment",
        },
        session_id=str(session_id),
        user_id="anonymous",
    )

    # Emit SSE event: readiness assessment started
    await _emit_tutor_event(
        session_id,
        "progress",
        "readiness_assessment",
        "running",
    )

    logger.info(
        "tutor_readiness_assessment_started",
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
                            concept = str(lesson.get("concept", concept))

        # Build prompt
        prompt = READINESS_ASSESSMENT_PROMPT.format(
            concept=concept,
            user_response=last_user_message or "No response yet",
            understanding_scores=json.dumps(understanding_scores),
        )

        # Get LLM model and compiler
        model = get_chat_model()
        compiler = _get_tutor_compiler()

        # Create parser for ReadinessAssessment
        parser = JsonOutputParser(pydantic_object=ReadinessAssessment)

        # Get conversation history for context compaction (Issue #270)
        conversation_history = state.get("conversation_history", [])

        # Compile context with history compaction (include format instructions in current_input)
        messages = await compiler.compile_for_invocation(
            session_history=conversation_history,
            current_input=f"{prompt}\n\n{parser.get_format_instructions()}",
            injected_memory=None,  # Future RAG integration point
        )

        config = create_runnable_config()
        response = await model.ainvoke(messages, config=config)
        response_text = extract_string_content(response)

        # Parse JSON response
        try:
            # Try to extract JSON from markdown code blocks if present
            if isinstance(response_text, str) and "```json" in response_text:
                json_start = response_text.find("```json") + 8
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    response_text = response_text[json_start:json_end].strip()
            elif isinstance(response_text, str) and "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    response_text = response_text[json_start:json_end].strip()

            if not isinstance(response_text, str):
                msg = "Response text must be a string"
                raise TypeError(msg)
            assessment_dict = json.loads(response_text)
            assessment = ReadinessAssessment(**assessment_dict)
        except (json.JSONDecodeError, Exception) as e:  # noqa: BLE001 - Catch JSON parsing errors and other exceptions for fallback
            logger.warning(
                "tutor_readiness_assessment_parse_error",
                session_id=session_id,
                error=str(e),
                response_preview=response_text[:200],
            )
            # Fallback: conservative assessment
            assessment = ReadinessAssessment(
                user_ready=False,
                confidence_score=0.5,
                reasoning="Unable to parse assessment, defaulting to not ready",
                suggested_action="rephrase",
            )

        # Update understanding scores
        concept_key = f"section_{current_section}_lesson_{current_lesson}"
        updated_scores = understanding_scores.copy()
        updated_scores[concept_key] = assessment.confidence_score

        # Increment attempts
        new_attempts = attempts + 1

        # Update session state in database
        session_factory = get_session_factory()
        async with session_factory() as db_session:
            from uuid import UUID

            repo = TutorSessionRepository(session=db_session)
            await repo.update_session_state(
                UUID(session_id),
                understanding_scores=updated_scores,
            )

        # Emit SSE event: readiness assessment complete
        await _emit_tutor_event(
            session_id,
            "progress",
            "readiness_assessment",
            "complete",
            user_ready=assessment.user_ready,
            confidence_score=assessment.confidence_score,
            attempts=new_attempts,
        )

        logger.info(
            "tutor_readiness_assessment_complete",
            session_id=session_id,
            user_ready=assessment.user_ready,
            confidence_score=assessment.confidence_score,
            attempts=new_attempts,
        )

        # Update conversation history if user message exists
        conversation_history = state.get("conversation_history", [])
        if state.get("last_user_message"):
            new_message: TutorMessage = {
                "role": "user",
                "content": state["last_user_message"],  # type: ignore[typeddict-item]
                "created_at": datetime.now(UTC).isoformat(),
                "metadata": {"phase": "readiness_assessment"},
            }
            updated_history: list[TutorMessage] = [*conversation_history, new_message]  # type: ignore[list-item]
        else:
            updated_history = list(conversation_history)  # type: ignore[arg-type]

        # Return only updated fields
        return {
            "user_ready": assessment.user_ready,
            "understanding_scores": updated_scores,
            "attempts_current_lesson": new_attempts,
            "current_phase": "readiness_assessment",
            "conversation_history": updated_history,
        }

    except Exception as e:
        # Emit SSE event: readiness assessment failed
        await _emit_tutor_event(
            session_id,
            "error",
            "readiness_assessment",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_readiness_assessment_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
