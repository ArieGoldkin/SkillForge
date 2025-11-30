"""Generate syllabus node for tutor workflow.

This node creates a personalized curriculum based on analysis context.
"""

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import get_current_run_tree

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.core.model_factory import get_chat_model
from app.db.session import get_session_factory
from app.workflows.tutor.config import SYLLABUS_GENERATION_PROMPT
from app.workflows.tutor.nodes.sse_helpers import emit_tutor_event as _emit_tutor_event
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)


@robust_traceable(
    name="generate_syllabus",
    run_type="chain",
    tags=["tutor", "workflow", "node"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "tutor",
        "component": "tutor_node",
    },
)
async def generate_syllabus(state: TutorState) -> dict[str, object]:
    """Generate syllabus from analysis context.

    Creates a personalized curriculum with 2-4 sections, each containing
    2-3 lessons based on the analysis content.

    Args:
        state: Current tutor state

    Returns:
        Dictionary with syllabus field (to avoid LangGraph concurrent update errors)

    """
    session_id = state["session_id"]
    analysis_id = state.get("analysis_id")
    user_level = state.get("user_level", "intermediate")

    # Thread grouping and runtime metadata
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            # Group all tutor messages in one thread
            run_tree.metadata["thread_id"] = str(session_id)
            run_tree.metadata["session_id"] = str(session_id)
            run_tree.metadata["conversation_id"] = str(session_id)
            # Phase-specific metadata
            run_tree.metadata["tutor_phase"] = "syllabus_generation"
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

    # Emit SSE event: syllabus generation started
    await _emit_tutor_event(
        session_id,
        "progress",
        "syllabus_generation",
        "running",
    )

    logger.info(
        "tutor_syllabus_generation_started",
        session_id=session_id,
        analysis_id=analysis_id,
        user_level=user_level,
    )

    try:
        # Get analysis summary if analysis_id provided
        analysis_summary = None
        if analysis_id:
            session_factory = get_session_factory()
            async with session_factory() as db_session:
                from uuid import UUID

                from app.services.tutor.analysis_service import get_analysis_summary

                analysis_summary = await get_analysis_summary(db_session, UUID(analysis_id))

        # Build prompt
        prompt = SYLLABUS_GENERATION_PROMPT.format(
            analysis_summary=json.dumps(analysis_summary)
            if analysis_summary
            else "No analysis context",
            user_level=user_level,
        )

        # Get LLM model
        model = get_chat_model()

        # Generate syllabus with structured output
        messages = [
            SystemMessage(
                content=(
                    "You are an expert curriculum designer. "
                    "Generate structured, personalized learning curricula."
                )
            ),
            HumanMessage(content=prompt),
        ]

        response = await model.ainvoke(messages)
        from app.workflows.tutor.nodes.response_helpers import extract_string_content

        syllabus_text = extract_string_content(response)

        # Parse JSON response
        try:
            # Try to extract JSON from markdown code blocks if present
            if isinstance(syllabus_text, str) and "```json" in syllabus_text:
                json_start = syllabus_text.find("```json") + 8
                json_end = syllabus_text.find("```", json_start)
                if json_end > json_start:
                    syllabus_text = syllabus_text[json_start:json_end].strip()
            elif isinstance(syllabus_text, str) and "```" in syllabus_text:
                json_start = syllabus_text.find("```") + 3
                json_end = syllabus_text.find("```", json_start)
                if json_end > json_start:
                    syllabus_text = syllabus_text[json_start:json_end].strip()

            if not isinstance(syllabus_text, str):
                raise ValueError("Syllabus text must be a string")
            syllabus = json.loads(syllabus_text)
        except json.JSONDecodeError as e:
            logger.error(
                "tutor_syllabus_parse_error",
                session_id=session_id,
                error=str(e),
                response_preview=syllabus_text[:200],
            )
            # Fallback: create basic syllabus structure
            syllabus = {
                "title": "Learning Curriculum",
                "description": "Personalized learning path",
                "sections": [
                    {
                        "title": "Introduction",
                        "description": "Getting started",
                        "lessons": [
                            {
                                "title": "Overview",
                                "concept": "Core concepts",
                                "explanation": "Let's start learning...",
                            }
                        ],
                    }
                ],
            }

        # Update session state in database
        session_factory = get_session_factory()
        async with session_factory() as db_session:
            from uuid import UUID

            from app.db.repositories.tutor_session_repository import TutorSessionRepository

            repo = TutorSessionRepository(session=db_session)
            await repo.update_session_state(
                UUID(session_id),
                syllabus=syllabus,
                current_phase="lesson_delivery",
            )

        # Emit SSE event: syllabus generation complete
        await _emit_tutor_event(
            session_id,
            "progress",
            "syllabus_generation",
            "complete",
            sections_count=len(syllabus.get("sections", [])),
        )

        logger.info(
            "tutor_syllabus_generation_complete",
            session_id=session_id,
            sections_count=len(syllabus.get("sections", [])),
        )

        # Return only updated fields
        return {
            "syllabus": syllabus,
            "current_phase": "lesson_delivery",
        }

    except Exception as e:
        # Emit SSE event: syllabus generation failed
        await _emit_tutor_event(
            session_id,
            "error",
            "syllabus_generation",
            "failed",
            error=str(e),
        )

        logger.error(
            "tutor_syllabus_generation_failed",
            session_id=session_id,
            error=str(e),
            exc_info=True,
        )
        raise
