"""Integration tests for agent routing with Send API.

Tests verify that the route_to_agents function correctly creates Send objects
for dynamic parallel execution based on supervisor decisions.
"""

import pytest

from app.workflows.nodes.agent_router import route_to_agents
from app.workflows.state import AnalysisState


@pytest.fixture
def sample_state() -> AnalysisState:
    """Sample state with supervisor decision."""
    return {
        "analysis_id": "test-analysis-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test content",
        "supervisor_decision": {
            "agents": ["tech_comparator", "security_auditor", "trend_validator"],
            "priority": [0.9, 0.8, 0.7],
            "reasoning": "Test reasoning",
            "confidence": 0.85,
        },
    }


@pytest.mark.asyncio
async def test_route_to_agents_creates_send_objects(sample_state: AnalysisState) -> None:
    """Test that route_to_agents creates Send objects for selected agents."""
    from langgraph.types import Send

    sends = await route_to_agents(sample_state)

    # Should create 3 Send objects for 3 selected agents
    assert len(sends) == 3
    assert all(isinstance(send, Send) for send in sends)

    # Verify Send objects target correct nodes
    node_names = [send.node for send in sends]
    assert "tech_comparator" in node_names
    assert "security_auditor" in node_names
    assert "trend_validator" in node_names


@pytest.mark.asyncio
async def test_route_to_agents_routes_to_aggregate_when_no_agents_selected() -> None:
    """Test that route_to_agents routes to aggregate when no agents selected."""
    from langgraph.types import Send

    state: AnalysisState = {
        "analysis_id": "test-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test",
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "No agents needed",
            "confidence": 0.5,
        },
    }

    sends = await route_to_agents(state)

    # Should route to aggregate when no agents selected
    assert len(sends) == 1
    assert isinstance(sends[0], Send)
    assert sends[0].node == "aggregate"


@pytest.mark.asyncio
async def test_route_to_agents_handles_unknown_agent_type() -> None:
    """Test that route_to_agents handles unknown agent types gracefully."""
    state: AnalysisState = {
        "analysis_id": "test-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test",
        "supervisor_decision": {
            "agents": ["tech_comparator", "unknown_agent"],
            "priority": [0.9, 0.8],
            "reasoning": "Test",
            "confidence": 0.85,
        },
    }

    sends = await route_to_agents(state)

    # Should only create Send for known agent
    assert len(sends) == 1
    assert sends[0].node == "tech_comparator"


@pytest.mark.asyncio
async def test_route_to_agents_all_8_agents() -> None:
    """Test route_to_agents with all 8 agents selected."""
    state: AnalysisState = {
        "analysis_id": "test-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test",
        "supervisor_decision": {
            "agents": [
                "tech_comparator",
                "security_auditor",
                "implementation_planner",
                "performance_analyst",
                "code_quality_critic",
                "trend_validator",
                "dependency_mapper",
                "integration_feasibility",
            ],
            "priority": [0.9] * 8,
            "reasoning": "All agents needed",
            "confidence": 0.95,
        },
    }

    sends = await route_to_agents(state)

    # Should create 8 Send objects
    assert len(sends) == 8

    # Verify all agent nodes are targeted
    node_names = [send.node for send in sends]
    expected_nodes = [
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
        "performance_analyst",
        "code_quality_critic",
        "trend_validator",
        "dependency_mapper",
        "integration_feasibility",
    ]
    assert set(node_names) == set(expected_nodes)
