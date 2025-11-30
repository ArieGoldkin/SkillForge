"""Studio-compatible workflow exports for LangGraph CLI.

LangGraph CLI requires workflows without checkpointers - it handles
persistence automatically. This module provides versions of our workflows
compiled without checkpointers for Studio debugging.

The original workflows (with checkpointers) remain in their original
modules for FastAPI use.
"""

from langgraph.graph import END, StateGraph

from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.workflows.graph_builder import (
    _extract_content_node,
    _generate_embedding_node,
    _supervisor_node,
)
from app.workflows.nodes.agent_router import route_to_agents
from app.workflows.nodes.agents import (
    code_quality_critic_node,
    dependency_mapper_node,
    implementation_planner_node,
    integration_feasibility_node,
    performance_analyst_node,
    security_auditor_node,
    tech_comparator_node,
    trend_validator_node,
)
from app.workflows.state import AnalysisState
from app.workflows.tasks import aggregate_findings, generate_artifact
from app.workflows.tutor.graph_builder import _route_after_assessment, _route_after_review
from app.workflows.tutor.nodes import (
    ask_socratic,
    assess_readiness,
    conduct_review,
    deliver_lesson,
    final_challenge,
    generate_syllabus,
    guide_reflection,
    rephrase_explain,
)
from app.workflows.tutor.state import TutorState

logger = get_logger(__name__)


def _build_analysis_graph_no_checkpointer():
    """Build analysis graph without checkpointer for Studio.

    This rebuilds the same graph structure as build_analysis_graph()
    but compiles without a checkpointer, as required by LangGraph CLI.

    Returns:
        Compiled StateGraph without checkpointer

    """
    graph = StateGraph(AnalysisState)

    # Add workflow nodes
    graph.add_node("extract", _extract_content_node)
    graph.add_node("embedding", _generate_embedding_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("aggregate", aggregate_findings)
    graph.add_node("generate_artifact", generate_artifact)

    # Add all agent nodes
    graph.add_node("tech_comparator", tech_comparator_node)
    graph.add_node("security_auditor", security_auditor_node)
    graph.add_node("implementation_planner", implementation_planner_node)
    graph.add_node("performance_analyst", performance_analyst_node)
    graph.add_node("code_quality_critic", code_quality_critic_node)
    graph.add_node("trend_validator", trend_validator_node)
    graph.add_node("dependency_mapper", dependency_mapper_node)
    graph.add_node("integration_feasibility", integration_feasibility_node)

    # Define edges
    graph.set_entry_point("extract")

    # Fan-out: embedding and supervisor run in parallel after extract
    graph.add_edge("extract", "embedding")
    graph.add_edge("extract", "supervisor")

    # Fan-out: Supervisor routes to selected agents dynamically
    graph.add_conditional_edges(
        "supervisor",
        route_to_agents,
        [
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
            "code_quality_critic",
            "trend_validator",
            "dependency_mapper",
            "integration_feasibility",
            "aggregate",  # Fallback if no agents selected
        ],
    )

    # Fan-in: All agent nodes route to aggregate
    agent_nodes = [
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
        "performance_analyst",
        "code_quality_critic",
        "trend_validator",
        "dependency_mapper",
        "integration_feasibility",
    ]
    for agent_node in agent_nodes:
        graph.add_edge(agent_node, "aggregate")

    # Sequential: aggregate -> generate_artifact -> end
    graph.add_edge("aggregate", "generate_artifact")
    graph.add_edge("generate_artifact", END)

    # Compile WITHOUT checkpointer (Studio handles persistence)
    compiled_graph = graph.compile()

    # Set step timeout
    compiled_graph.step_timeout = STEP_TIMEOUT

    logger.info(
        "studio_analysis_graph_compiled",
        step_timeout=STEP_TIMEOUT,
        checkpointer="none",
    )

    return compiled_graph


def _build_tutor_graph_no_checkpointer():
    """Build tutor graph without checkpointer for Studio.

    This rebuilds the same graph structure as build_tutor_graph()
    but compiles without a checkpointer, as required by LangGraph CLI.

    Returns:
        Compiled StateGraph without checkpointer

    """
    graph = StateGraph(TutorState)

    # Add nodes
    graph.add_node("generate_syllabus", generate_syllabus)
    graph.add_node("deliver_lesson", deliver_lesson)
    graph.add_node("ask_socratic", ask_socratic)
    graph.add_node("assess_readiness", assess_readiness)
    graph.add_node("rephrase_explain", rephrase_explain)
    graph.add_node("conduct_review", conduct_review)
    graph.add_node("final_challenge", final_challenge)
    graph.add_node("guide_reflection", guide_reflection)

    # Set entry point
    graph.set_entry_point("generate_syllabus")

    # Add edges
    graph.add_edge("generate_syllabus", "deliver_lesson")
    graph.add_edge("deliver_lesson", "ask_socratic")
    graph.add_edge("ask_socratic", END)

    # After assessment, route based on readiness
    graph.add_conditional_edges(
        "assess_readiness",
        _route_after_assessment,
        {
            "rephrase_explain": "rephrase_explain",
            "section_review": "conduct_review",
            "end": END,
        },
    )

    # After rephrasing, ask Socratic question again
    graph.add_edge("rephrase_explain", "ask_socratic")

    # After section review, route to final challenge or next section
    graph.add_conditional_edges(
        "conduct_review",
        _route_after_review,
        {
            "final_challenge": "final_challenge",
            "end": END,
        },
    )

    # After final challenge, guide reflection
    graph.add_edge("final_challenge", "guide_reflection")

    # After reflection, session is complete
    graph.add_edge("guide_reflection", END)

    # Compile WITHOUT checkpointer (Studio handles persistence)
    compiled_graph = graph.compile()

    logger.info(
        "studio_tutor_graph_compiled",
        checkpointer="none",
    )

    return compiled_graph


# Export Studio-compatible workflows (no checkpointers)
analysis_workflow = _build_analysis_graph_no_checkpointer()
tutor_workflow = _build_tutor_graph_no_checkpointer()
