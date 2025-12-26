"""Agent routing function for dynamic parallel execution using LangGraph Send API.

This module provides the routing function that uses LangGraph's Send API to
dynamically route to selected agent nodes for parallel execution.

Issue #246: Uses context scoping to pass minimal state to each agent.
Issue #266: Injects proactive memory context for agents with inject_memory=True.
"""

from langgraph.types import Send

from app.core.logging import get_logger
from app.db.session import get_session_factory
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.memory.proactive_recall import (
    fetch_proactive_context,
    format_memory_context,
)
from app.shared.workflows.context_scope import AGENT_SCOPES, build_scoped_context

logger = get_logger(__name__)


async def route_to_agents(state: AnalysisState) -> list[Send]:
    """Route to selected agents using Send API for dynamic parallel execution.

    This function reads the supervisor's agent selection from state and returns
    a list of Send objects, one per selected agent. LangGraph automatically
    executes all Send targets in parallel.

    For agents with inject_memory=True in their ContextScope, proactive memory
    recall is performed and injected into the scoped state as "prior_memory".

    Args:
        state: Current workflow state with supervisor_decision populated

    Returns:
        List of Send objects targeting selected agent nodes. Empty list if
        no agents selected (workflow will skip to aggregate).

    Example:
        If supervisor selects ["tech_comparator", "security_auditor"], returns:
        [
            Send("tech_comparator", scoped_state_with_memory),
            Send("security_auditor", scoped_state_with_memory),
        ]

    """
    supervisor_decision = state.get("supervisor_decision", {})
    selected_agents_raw = supervisor_decision.get("agents", [])
    # Ensure selected_agents is a list (type narrowing for mypy)
    selected_agents: list[str] = (
        selected_agents_raw if isinstance(selected_agents_raw, list) else []
    )

    if not selected_agents:
        logger.debug(
            "agent_router_no_agents_selected",
            analysis_id=state.get("analysis_id"),
        )
        # Return Send to aggregate when no agents selected (explicit routing)
        return [Send("aggregate", state)]

    # Map agent types to node names (must match node names in graph_builder)
    agent_node_map = {
        # Tier 1 Universal agents (Issue #499) - always run on all content types
        "key_insights": "key_insights",
        "pros_cons": "pros_cons",
        "audience_fit": "audience_fit",
        "actionable": "actionable",
        # Tier 2 Validation agents - tool-enabled (Standard mode+)
        "tech_comparator": "tech_comparator",
        "security_auditor": "security_auditor",
        "implementation_planner": "implementation_planner",
        "performance_analyst": "performance_analyst",
        "code_quality_critic": "code_quality_critic",
        "trend_validator": "trend_validator",
        "dependency_mapper": "dependency_mapper",
        "integration_feasibility": "integration_feasibility",
        # Tier 3 Research agents (Issue #501) - memory-enabled (Deep Dive mode)
        "deep_researcher": "deep_researcher",
        "community_pulse": "community_pulse",
        "knowledge_curator": "knowledge_curator",
        "learning_path_advisor": "learning_path_advisor",
    }

    # Extract content summary for memory queries (Issue #266)
    content_summary = _get_content_summary(state)

    # Create Send objects for each selected agent with scoped context
    sends = []
    for agent_type in selected_agents:
        if agent_type in agent_node_map:
            node_name = agent_node_map[agent_type]

            # Build scoped context for this agent (Issue #246)
            scoped_state = build_scoped_context(state, agent_type)

            # Check if agent needs memory injection (Issue #266)
            scope = AGENT_SCOPES.get(agent_type)
            if scope and scope.inject_memory and content_summary:
                prior_memory = await _fetch_agent_memory(agent_type, content_summary)
                if prior_memory:
                    scoped_state["prior_memory"] = prior_memory
                    logger.debug(
                        "agent_router_memory_injected",
                        agent_type=agent_type,
                        memory_length=len(prior_memory),
                        analysis_id=state.get("analysis_id"),
                    )

            sends.append(Send(node_name, scoped_state))
            logger.debug(
                "agent_router_send_created",
                agent_type=agent_type,
                node_name=node_name,
                analysis_id=state.get("analysis_id"),
                scoped_fields=list(scoped_state.keys()),
            )
        else:
            logger.warning(
                "agent_router_unknown_agent",
                agent_type=agent_type,
                analysis_id=state.get("analysis_id"),
                available_agents=list(agent_node_map.keys()),
            )

    # Issue #547 (GAP 4): Track dispatched agents for fan-in validation
    # This allows aggregation to know exactly how many agents to expect
    dispatched_agent_types = [
        agent_type for agent_type in selected_agents if agent_type in agent_node_map
    ]

    logger.info(
        "agent_router_routing",
        analysis_id=state.get("analysis_id"),
        selected_agents=selected_agents,
        dispatched_agents=dispatched_agent_types,
        send_count=len(sends),
        expected_agent_count=len(dispatched_agent_types),
    )

    # Note: We return Send objects which create parallel branches
    # The expected_agent_count and dispatched_agents are logged for observability
    # but actual state updates happen via agent findings accumulation
    return sends


def _get_content_summary(state: AnalysisState) -> str:
    """Extract a content summary for memory similarity search.

    Tries content_ref.summary first, falls back to truncated raw_content.

    Args:
        state: Current workflow state

    Returns:
        Content summary (empty string if no content available)

    """
    # Try content_ref summary first (most common case)
    content_ref = state.get("content_ref")
    if content_ref and isinstance(content_ref, dict):
        summary = content_ref.get("summary")
        if summary and isinstance(summary, str):
            return summary

    # Fall back to truncated raw_content
    raw_content = state.get("raw_content")
    if raw_content and isinstance(raw_content, str):
        return raw_content[:500]  # First 500 chars as summary

    # No content available
    return ""


async def _fetch_agent_memory(agent_type: str, content_summary: str) -> str:
    """Fetch proactive memory context for an agent with graceful fallback.

    This function handles all error cases gracefully to ensure memory fetch
    failures never block agent routing.

    Args:
        agent_type: Type of agent (e.g., "security_auditor")
        content_summary: Content summary for similarity search

    Returns:
        Formatted memory context string, or empty string on error

    """
    try:
        # Get database session
        session_factory = get_session_factory()
        async with session_factory() as session:
            # Fetch relevant memory snippets
            snippets = await fetch_proactive_context(
                session=session,
                content_summary=content_summary,
                agent_type=agent_type,
            )

            # Format for injection
            return format_memory_context(snippets)

    except ValueError as e:
        # Missing OPENAI_API_KEY or other config issues
        logger.warning(
            "agent_router_memory_fetch_config_error",
            agent_type=agent_type,
            error=str(e),
            fallback="continuing_without_memory",
        )
        return ""

    except Exception as e:  # noqa: BLE001
        # Database errors or other unexpected issues
        logger.warning(
            "agent_router_memory_fetch_error",
            agent_type=agent_type,
            error=str(e),
            error_type=type(e).__name__,
            fallback="continuing_without_memory",
        )
        return ""
