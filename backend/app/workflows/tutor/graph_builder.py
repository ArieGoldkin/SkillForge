"""StateGraph workflow builder for tutor agent.

This module constructs the LangGraph StateGraph workflow for the tutor agent
with nodes for syllabus generation, lesson delivery, Socratic questioning,
and readiness assessment.
"""

import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.core.logging import get_logger
from app.workflows.tutor.nodes import (
    ask_socratic,
    assess_readiness,
    conduct_review,  # Phase 3
    deliver_lesson,
    final_challenge,  # Phase 3
    generate_syllabus,
    guide_reflection,  # Phase 3
    rephrase_explain,  # Phase 2
)
from app.workflows.tutor.state import TutorState

# Try to import PostgresSaver, fallback to MemorySaver if not available
try:
    from langgraph.checkpoint.postgres import (
        PostgresSaver,  # type: ignore[import-not-found,import-untyped]
    )
except ImportError:
    PostgresSaver = None  # type: ignore[assignment, misc]

logger = get_logger(__name__)


def _get_checkpointer():
    """Get checkpointer instance (PostgresSaver or MemorySaver)."""
    # Setup checkpointer (PostgreSQL for production, MemorySaver for dev)
    # Use MemorySaver in tests to avoid database connection hangs
    if (
        settings.DATABASE_URL
        and PostgresSaver is not None
        and not os.environ.get("PYTEST_CURRENT_TEST")
    ):
        try:
            checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
            logger.info("tutor_checkpointer_initialized", type="PostgresSaver")
            return checkpointer
        except (ValueError, ConnectionError) as e:
            logger.warning(
                "tutor_checkpointer_fallback",
                error=str(e),
                fallback="MemorySaver",
            )
            return MemorySaver()
    else:
        logger.info("tutor_checkpointer_initialized", type="MemorySaver")
        return MemorySaver()


def _route_after_assessment(state: TutorState) -> str:
    """Route after readiness assessment.

    Phase 3: Routes to rephrase_explain if not ready (and attempts < 3),
    or checks if last lesson in section to route to section_review,
    or routes to next_lesson if more lessons remain.

    Args:
        state: Current tutor state

    Returns:
        Next node name: "rephrase_explain", "section_review", "next_lesson", or "end"

    """
    user_ready = state.get("user_ready", False)
    attempts = state.get("attempts_current_lesson", 0)
    max_attempts = 3
    syllabus = state.get("syllabus")
    current_section = state.get("current_section", 0)
    current_lesson = state.get("current_lesson", 0)

    if user_ready:
        # User is ready, check if last lesson in section
        if syllabus and isinstance(syllabus, dict):
            sections = syllabus.get("sections", [])
            if isinstance(sections, list) and current_section < len(sections):
                section = sections[current_section]
                if isinstance(section, dict):
                    lessons = section.get("lessons", [])
                    if isinstance(lessons, list) and current_lesson >= len(lessons) - 1:
                        # Last lesson in section, move to section review
                        return "section_review"
                    else:
                        # More lessons in section - Phase 3: will add next_lesson node
                        return "end"  # Phase 3: For now end, will add next_lesson node
        return "end"  # No more sections/lessons
    elif attempts >= max_attempts:
        # Max attempts reached, move on anyway
        logger.warning(
            "tutor_max_attempts_reached",
            session_id=state.get("session_id"),
            attempts=attempts,
        )
        # Check if last lesson - if so, go to section review
        if syllabus and isinstance(syllabus, dict):
            sections = syllabus.get("sections", [])
            if isinstance(sections, list) and current_section < len(sections):
                section = sections[current_section]
                if isinstance(section, dict):
                    lessons = section.get("lessons", [])
                    if isinstance(lessons, list) and current_lesson >= len(lessons) - 1:
                        return "section_review"
        return "end"
    else:
        # Not ready, but attempts < 3 - try rephrasing
        return "rephrase_explain"


def _route_after_review(state: TutorState) -> str:
    """Route after section review.

    Phase 3: Checks if last section to route to final_challenge,
    or routes to next section.

    Args:
        state: Current tutor state

    Returns:
        Next node name: "final_challenge" or "end"

    """
    syllabus = state.get("syllabus")
    current_section = state.get("current_section", 0)

    if syllabus and isinstance(syllabus, dict):
        sections = syllabus.get("sections", [])
        if isinstance(sections, list) and current_section >= len(sections) - 1:
            # Last section, move to final challenge
            return "final_challenge"
        else:
            # More sections - Phase 3: will add next_section logic
            return "end"  # Phase 3: For now end, will add next_section node

    return "end"


def build_tutor_graph():
    """Build and compile tutor StateGraph workflow.

    Returns:
        Compiled StateGraph ready for execution

    """
    graph = StateGraph(TutorState)

    # Add nodes (Phase 1: Core 4 + Phase 2: rephrase + Phase 3: completion)
    graph.add_node("generate_syllabus", generate_syllabus)
    graph.add_node("deliver_lesson", deliver_lesson)
    graph.add_node("ask_socratic", ask_socratic)
    graph.add_node("assess_readiness", assess_readiness)
    graph.add_node("rephrase_explain", rephrase_explain)  # Phase 2
    graph.add_node("conduct_review", conduct_review)  # Phase 3
    graph.add_node("final_challenge", final_challenge)  # Phase 3
    graph.add_node("guide_reflection", guide_reflection)  # Phase 3

    # Set entry point
    graph.set_entry_point("generate_syllabus")

    # Add edges
    graph.add_edge("generate_syllabus", "deliver_lesson")
    graph.add_edge("deliver_lesson", "ask_socratic")
    # After asking Socratic question, workflow ends to wait for user response
    graph.add_edge("ask_socratic", END)

    # When user sends message, workflow continues: ask_socratic -> assess_readiness
    # (This is handled by API manually calling assess_readiness)

    # After assessment, route based on readiness
    graph.add_conditional_edges(
        "assess_readiness",
        _route_after_assessment,
        {
            "rephrase_explain": "rephrase_explain",  # Phase 2: Try rephrasing
            "section_review": "conduct_review",  # Phase 3: Last lesson in section
            "end": END,  # Phase 3: End (will add next_lesson node in future)
        },
    )

    # After rephrasing, ask Socratic question again
    graph.add_edge("rephrase_explain", "ask_socratic")

    # After section review, route to final challenge or next section
    graph.add_conditional_edges(
        "conduct_review",
        _route_after_review,
        {
            "final_challenge": "final_challenge",  # Phase 3: Last section
            "end": END,  # Phase 3: More sections (will add next_section node in future)
        },
    )

    # After final challenge, guide reflection
    graph.add_edge("final_challenge", "guide_reflection")

    # After reflection, session is complete
    graph.add_edge("guide_reflection", END)

    # Compile with checkpointer
    checkpointer = _get_checkpointer()
    compiled_graph = graph.compile(checkpointer=checkpointer)

    logger.info("tutor_graph_compiled", workflow_type="StateGraph")

    return compiled_graph


# Global workflow instance
tutor_workflow = build_tutor_graph()
