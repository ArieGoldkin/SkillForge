"""Agent routing function for dynamic parallel execution using LangGraph Send API.

This module provides the routing function that uses LangGraph's Send API to
dynamically route to selected agent nodes for parallel execution.
"""

from langgraph.types import Send

from app.core.logging import get_logger
from app.workflows.state import AnalysisState

logger = get_logger(__name__)


def route_to_agents(state: AnalysisState) -> list[Send]:
    """Route to selected agents using Send API for dynamic parallel execution.

    This function reads the supervisor's agent selection from state and returns
    a list of Send objects, one per selected agent. LangGraph automatically
    executes all Send targets in parallel.

    Args:
        state: Current workflow state with supervisor_decision populated

    Returns:
        List of Send objects targeting selected agent nodes. Empty list if
        no agents selected (workflow will skip to aggregate).

    Example:
        If supervisor selects ["tech_comparator", "security_auditor"], returns:
        [
            Send("tech_comparator", state),
            Send("security_auditor", state),
        ]
    """
    supervisor_decision = state.get("supervisor_decision", {})
    selected_agents = supervisor_decision.get("agents", [])

    if not selected_agents:
        logger.debug(
            "agent_router_no_agents_selected",
            analysis_id=state.get("analysis_id"),
        )
        # Return Send to aggregate when no agents selected (explicit routing)
        return [Send("aggregate", state)]

    # Map agent types to node names (must match node names in graph_builder)
    agent_node_map = {
        "tech_comparator": "tech_comparator",
        "security_auditor": "security_auditor",
        "implementation_planner": "implementation_planner",
        "performance_analyst": "performance_analyst",
        "code_quality_critic": "code_quality_critic",
        "trend_validator": "trend_validator",
        "dependency_mapper": "dependency_mapper",
        "integration_feasibility": "integration_feasibility",
    }

    # Create Send objects for each selected agent
    sends = []
    for agent_type in selected_agents:
        if agent_type in agent_node_map:
            node_name = agent_node_map[agent_type]
            sends.append(Send(node_name, state))
            logger.debug(
                "agent_router_send_created",
                agent_type=agent_type,
                node_name=node_name,
                analysis_id=state.get("analysis_id"),
            )
        else:
            logger.warning(
                "agent_router_unknown_agent",
                agent_type=agent_type,
                analysis_id=state.get("analysis_id"),
                available_agents=list(agent_node_map.keys()),
            )

    logger.info(
        "agent_router_routing",
        analysis_id=state.get("analysis_id"),
        selected_agents=selected_agents,
        send_count=len(sends),
    )

    return sends
