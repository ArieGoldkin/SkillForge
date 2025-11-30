"""Assess readiness node for tutor workflow.

This node evaluates user understanding using LLM-based assessment.
"""

import json
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.core.model_factory import get_chat_model
from app.db.repositories.tutor_session_repository import TutorSessionRepository
from app.db.session import get_session_factory
from app.workflows.tutor.config import READINESS_ASSESSMENT_PROMPT
from app.workflows.tutor.nodes.response_helpers import extract_string_content
from app.workflows.tutor.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.workflows.tutor.schemas.assessment import ReadinessAssessment
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)


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
async def assess_readiness(state: TutorState) -> dict[str, object]:
    """Assess user readiness using LLM-based evaluation.

    Evaluates understanding based on user response and updates
    understanding_scores. Returns user_ready boolean.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with user_ready, understanding_scores, and attempts fields

    """
    session_id = state["session_id"]
    syllabus = state.get("syllabus")
    current_section = state.get("current_section", 0)
    current_lesson = state.get("current_lesson", 0)
    last_user_message = state.get("last_user_message", "")
    understanding_scores = state.get("understanding_scores", {})
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
            run_tree.metadata["tutor_phase"] = "readiness_assessment"
    except Exception:
        # LangSmith not available or not in trace context - continue
        pass

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
                            concept = lesson.get("concept", concept)

        # Build prompt
        prompt = READINESS_ASSESSMENT_PROMPT.format(
            concept=concept,
            user_response=last_user_message or "No response yet",
            understanding_scores=json.dumps(understanding_scores),
        )

        # Get LLM model with structured output
        model = get_chat_model()

        # Create parser for ReadinessAssessment
        parser = JsonOutputParser(pydantic_object=ReadinessAssessment)

        # Generate assessment with structured output
        messages = [
            SystemMessage(
                content=(
                    "You are an expert educational assessor. "
                    "Evaluate understanding accurately and provide actionable feedback."
                )
            ),
            HumanMessage(content=f"{prompt}\n\n{parser.get_format_instructions()}"),
        ]

        response = await model.ainvoke(messages)
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
                raise ValueError("Response text must be a string")
            assessment_dict = json.loads(response_text)
            assessment = ReadinessAssessment(**assessment_dict)
        except (json.JSONDecodeError, Exception) as e:
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
            updated_history = conversation_history + [
                {
                    "role": "user",
                    "content": state["last_user_message"],
                    "created_at": datetime.now(UTC).isoformat(),
                    "metadata": {"phase": "readiness_assessment"},
                }
            ]
        else:
            updated_history = conversation_history

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
