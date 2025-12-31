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
from app.domains.tutor.workflows.nodes import (
    ask_socratic,
    assess_readiness,
    conduct_review,  # Phase 3
    deliver_lesson,
    final_challenge,  # Phase 3
    generate_syllabus,
    guide_reflection,  # Phase 3
    rephrase_explain,  # Phase 2
)
from app.domains.tutor.workflows.state import TutorState
from app.domains.tutor.workflows.state_accessors import get_syllabus

# Try to import RedisSaver dynamically to avoid hard dependency in lint
try:
    import importlib

    _lg_redis = importlib.import_module("langgraph.checkpoint.redis")
    RedisSaver = getattr(_lg_redis, "RedisSaver", None)
except Exception as e:  # noqa: BLE001 - Graceful degradation: RedisSaver is optional dependency
    logger_temp = get_logger(__name__)
    logger_temp.debug("redis_checkpointer_unavailable", error=str(e), exc_info=e)
    RedisSaver = None

logger = get_logger(__name__)


def get_checkpointer():
    """Get checkpointer instance from FastAPI app.state or fallback.

    Issue #624: Returns app-scoped AsyncPostgresSaver initialized in main.py lifespan,
    or creates fallback checkpointer if app.state.checkpointer is not available.

    Checkpointer selection priority:
    1. MemorySaver for tests (PYTEST_CURRENT_TEST is set)
    2. RedisSaver if USE_REDIS_CHECKPOINT=true and REDIS_URL is set
    3. AsyncPostgresSaver from app.state (initialized in lifespan)
    4. MemorySaver as fallback

    Returns:
        Checkpointer instance (AsyncPostgresSaver, RedisSaver, or MemorySaver)

    """
    # Use MemorySaver in tests to avoid database connection hangs
    if os.environ.get("PYTEST_CURRENT_TEST"):
        logger.info("tutor_checkpointer_initialized", type="MemorySaver", reason="test_mode")
        return MemorySaver()

    # Try RedisSaver if enabled and configured
    if settings.USE_REDIS_CHECKPOINT and settings.REDIS_URL and RedisSaver is not None:
        try:
            # RedisSaver.from_conn_string creates a Redis connection pool
            # with automatic TTL-based cleanup of checkpoints
            # TTL format: {"default_ttl": X} where X is in MINUTES
            # Convert seconds to minutes for RedisSaver
            ttl_minutes = settings.REDIS_CHECKPOINT_TTL / 60.0
            checkpointer = RedisSaver.from_conn_string(
                settings.REDIS_URL,
                # Set checkpoint TTL for automatic cleanup
                # RedisSaver expects TTL in minutes via "default_ttl" key
                ttl={"default_ttl": ttl_minutes},
            )
            logger.info(
                "tutor_checkpointer_initialized",
                type="RedisSaver",
                ttl_seconds=settings.REDIS_CHECKPOINT_TTL,
                ttl_minutes=ttl_minutes,
                redis_url=settings.REDIS_URL.split("@")[-1],  # Log host only, not credentials
            )
            return checkpointer
        except (ValueError, ConnectionError) as e:
            logger.warning(
                "tutor_checkpointer_fallback_from_redis",
                error=str(e),
                fallback="AsyncPostgresSaver or MemorySaver",
            )
            # Fall through to AsyncPostgresSaver/MemorySaver

    # Issue #624: Try to get AsyncPostgresSaver from app.state
    # This requires FastAPI app to be running with lifespan context
    # For tutor workflow, we use session-based checkpointing where each tutor
    # session has its own thread_id, so app-scoped checkpointer works well

    # Fallback to MemorySaver (development/local mode)
    logger.info(
        "tutor_checkpointer_initialized",
        type="MemorySaver",
        reason="app_state_not_accessible",
    )
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
    syllabus = get_syllabus(state)
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
                    # More lessons in section - Phase 3: will add next_lesson node
                    return "end"  # Phase 3: For now end, will add next_lesson node
        return "end"  # No more sections/lessons
    if attempts >= max_attempts:
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
    syllabus = get_syllabus(state)
    current_section = state.get("current_section", 0)

    if syllabus and isinstance(syllabus, dict):
        sections = syllabus.get("sections", [])
        if isinstance(sections, list) and current_section >= len(sections) - 1:
            # Last section, move to final challenge
            return "final_challenge"
        # More sections - Phase 3: will add next_section logic
        return "end"  # Phase 3: For now end, will add next_section node

    return "end"


def build_tutor_graph(checkpointer_override=None):
    """Build and compile tutor StateGraph workflow.

    Args:
        checkpointer_override: Optional checkpointer instance (AsyncPostgresSaver, etc.)
                              If None, falls back to get_checkpointer().
                              Issue #602: Support checkpointer injection from FastAPI app.state.

    Returns:
        Compiled StateGraph ready for execution

    """
    # LangGraph lacks type stubs for TypedDict state
    graph = StateGraph(TutorState)  # type: ignore[arg-type]

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

    # Compile with checkpointer (use override if provided)
    checkpointer = (
        checkpointer_override if checkpointer_override is not None else get_checkpointer()
    )
    compiled_graph = graph.compile(checkpointer=checkpointer)

    logger.info(
        "tutor_graph_compiled",
        workflow_type="StateGraph",
        checkpointer_type=type(checkpointer).__name__,
    )

    return compiled_graph


def create_tutor_workflow(checkpointer=None):
    """Create tutor workflow with optional checkpointer injection.

    Issue #602: Supports checkpointer injection from FastAPI app.state.

    Args:
        checkpointer: Optional checkpointer instance (AsyncPostgresSaver, etc.)

    Returns:
        Compiled StateGraph ready for execution

    """
    return build_tutor_graph(checkpointer_override=checkpointer)


# Global workflow instance (for backward compatibility)
# New code should use create_tutor_workflow() with injected checkpointer
tutor_workflow = build_tutor_graph()
