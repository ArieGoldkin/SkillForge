"""Integration tests for parallel agent execution with all 8 agents."""

import asyncio
import os
from uuid import UUID, uuid4

import pytest

from app.db.session import AsyncSessionLocal
from app.models.analysis import Analysis
from app.workflows.agents import (
    run_code_quality_critic,
    run_dependency_mapper,
    run_implementation_planner,
    run_integration_feasibility,
    run_performance_analyst,
    run_security_auditor,
    run_tech_comparator,
    run_trend_validator,
)

EXPECTED_AGENT_COUNT = 8


@pytest.fixture
def requires_llm():
    """Skip test if LLM is not configured."""
    llm_model = os.environ.get("LLM_MODEL", "")
    if not llm_model:
        pytest.skip("LLM_MODEL not configured")
    # Skip if OpenAI API key is not available
    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_OPENAI_API_KEY")
    if not openai_key:
        pytest.skip("OpenAI API key not available")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(600)  # 10 minutes for all 8 agents in parallel
async def test_execute_agents_all_8_agents_parallel(
    requires_llm,
    requires_database,
    reset_engine_connections,
):
    """Test parallel execution of all 8 agents with separate database sessions.

    This test verifies that all 8 agents can execute in parallel without
    concurrency errors, each using its own database session.
    """
    analysis_id = str(uuid4())
    content = """
    React is a JavaScript library for building user interfaces. It integrates
    well with Next.js and can be used with FastAPI backends. This guide shows
    how to implement a secure, performant full-stack application with proper
    code quality practices and modern dependencies.
    """
    content_type = "article"

    # Create Analysis record before calling agents (required for foreign key)
    async with AsyncSessionLocal() as shared_session:
        analysis = Analysis(
            id=UUID(analysis_id),
            url="https://example.com",
            content_type=content_type,
            status="pending",
        )
        shared_session.add(analysis)
        await shared_session.commit()

    # Each agent gets its own session (matching execute_agents pattern)
    async def run_tech_comparator_session():
        async with AsyncSessionLocal() as session:
            return await run_tech_comparator(content, content_type, analysis_id, session)

    async def run_integration_feasibility_session():
        async with AsyncSessionLocal() as session:
            return await run_integration_feasibility(content, content_type, analysis_id, session)

    async def run_implementation_planner_session():
        async with AsyncSessionLocal() as session:
            return await run_implementation_planner(content, content_type, analysis_id, session)

    async def run_security_auditor_session():
        async with AsyncSessionLocal() as session:
            return await run_security_auditor(content, content_type, analysis_id, session)

    async def run_performance_analyst_session():
        async with AsyncSessionLocal() as session:
            return await run_performance_analyst(content, content_type, analysis_id, session)

    async def run_code_quality_critic_session():
        async with AsyncSessionLocal() as session:
            return await run_code_quality_critic(content, content_type, analysis_id, session)

    async def run_trend_validator_session():
        async with AsyncSessionLocal() as session:
            return await run_trend_validator(content, content_type, analysis_id, session)

    async def run_dependency_mapper_session():
        async with AsyncSessionLocal() as session:
            return await run_dependency_mapper(content, content_type, analysis_id, session)

    # Execute all 8 agents in parallel with separate sessions
    tasks = [
        run_tech_comparator_session(),
        run_integration_feasibility_session(),
        run_implementation_planner_session(),
        run_security_auditor_session(),
        run_performance_analyst_session(),
        run_code_quality_critic_session(),
        run_trend_validator_session(),
        run_dependency_mapper_session(),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all agents completed successfully (no concurrency errors)
    assert len(results) == EXPECTED_AGENT_COUNT
    for result in results:
        assert not isinstance(result, Exception), f"Agent failed with: {result}"
        assert "agent_type" in result
        assert "findings" in result
        assert result["processing_time_ms"] > 0

    # Verify all 8 agent types are present
    agent_types = [r["agent_type"] for r in results]
    assert "tech_comparator" in agent_types
    assert "integration_feasibility" in agent_types
    assert "implementation_planner" in agent_types
    assert "security_auditor" in agent_types
    assert "performance_analyst" in agent_types
    assert "code_quality_critic" in agent_types
    assert "trend_validator" in agent_types
    assert "dependency_mapper" in agent_types
