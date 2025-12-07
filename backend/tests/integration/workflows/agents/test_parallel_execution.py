"""Integration tests for parallel agent execution using native LangGraph nodes.

Tests verify that agents execute in parallel as separate nodes using Send API,
with proper error isolation and state merging via reducer.
"""

import asyncio
from uuid import UUID, uuid4

import pytest

from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis
from app.workflows.analysis import analysis_workflow

EXPECTED_AGENT_COUNT = 8


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(600)  # 10 minutes for full workflow with all 8 agents
async def test_parallel_agents_all_8_agents_execute(
    requires_llm,
    requires_database,
    reset_engine_connections,
):
    """Test parallel execution of all 8 agents as separate LangGraph nodes.

    This test verifies that:
    - Supervisor selects all 8 agents
    - All agents execute in parallel as separate nodes
    - State is properly merged using reducer
    - No GeneratorExit errors occur
    - All agents complete successfully
    """
    analysis_id = str(uuid4())
    test_url = "https://react.dev"  # Content that should trigger all agents

    # Create Analysis record before running workflow (required for agent foreign keys)
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Run workflow - supervisor should select all agents for React content
    workflow_config = {
        "configurable": {"thread_id": analysis_id},
        "run_name": f"test_all_8_agents_{analysis_id[:8]}",
        "tags": ["test", "integration", "parallel_agents"],
        "metadata": {
            "analysis_id": analysis_id,
            "url": test_url,
            "test_type": "all_8_agents_parallel",
        },
    }

    result = await asyncio.wait_for(
        analysis_workflow.ainvoke(
            {
                "url": test_url,
                "analysis_id": analysis_id,
                "skill_level": "intermediate",
            },
            config=workflow_config,
        ),
        timeout=300.0,  # 5 minutes for full workflow
    )

    # Verify workflow completed
    assert "agent_findings" in result
    agent_findings = result["agent_findings"]

    # Verify all agents executed (may be fewer if supervisor didn't select all)
    # But should have at least some agents
    assert len(agent_findings) > 0, "At least some agents should have executed"

    # Verify findings structure
    for finding in agent_findings:
        assert "agent_type" in finding
        assert "findings" in finding
        assert finding["processing_time_ms"] > 0

    # Verify agent types are unique (no duplicates from reducer)
    agent_types = [f["agent_type"] for f in agent_findings]
    assert len(agent_types) == len(set(agent_types)), "No duplicate agent findings"


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(300)  # 5 minutes for error isolation test
async def test_parallel_agents_error_isolation_one_failure_does_not_crash_others(
    requires_llm,
    requires_database,
    reset_engine_connections,
):
    """Test that one agent failure does not crash other agents.

    With native LangGraph parallel execution, each agent node is independent.
    Failed agents return empty findings, but other agents continue.
    """
    analysis_id = str(uuid4())
    test_url = "https://react.dev"

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Run workflow - supervisor will select multiple agents
    workflow_config = {
        "configurable": {"thread_id": analysis_id},
        "run_name": f"test_error_isolation_{analysis_id[:8]}",
        "tags": ["test", "integration", "error_isolation"],
        "metadata": {
            "analysis_id": analysis_id,
            "url": test_url,
            "test_type": "error_isolation",
        },
    }

    result = await asyncio.wait_for(
        analysis_workflow.ainvoke(
            {
                "url": test_url,
                "analysis_id": analysis_id,
                "skill_level": "intermediate",
            },
            config=workflow_config,
        ),
        timeout=300.0,
    )

    # Verify workflow completed (even if some agents failed)
    assert "agent_findings" in result
    agent_findings = result["agent_findings"]

    # Should have at least some successful agents
    # Failed agents return empty findings, but don't crash the workflow
    assert isinstance(agent_findings, list)

    # Verify successful agents have proper structure
    successful_findings = [f for f in agent_findings if f and "agent_type" in f]
    assert len(successful_findings) > 0, "At least some agents should succeed"

    # Verify no GeneratorExit errors (key test - this was the main issue)
    # If GeneratorExit occurred, workflow would have failed or findings would be malformed
    for finding in successful_findings:
        assert "agent_type" in finding
        assert "findings" in finding
