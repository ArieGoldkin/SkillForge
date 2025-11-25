"""Integration tests for agent implementations with real LLM."""

import os
from uuid import uuid4

import pytest

from app.workflows.agents import (
    run_implementation_planner,
    run_integration_feasibility,
    run_tech_comparator,
)


@pytest.fixture
def requires_llm():
    """Skip test if LLM is not configured."""
    llm_model = os.environ.get("LLM_MODEL", "")
    if not llm_model:
        pytest.skip("LLM_MODEL not configured")
    # Skip if using Ollama and it's not available
    if llm_model.startswith("ollama:"):
        try:
            import httpx

            response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code != 200:
                pytest.skip("Ollama not available")
        except Exception:
            pytest.skip("Ollama not available")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_tech_comparator_integration(
    requires_llm,
    requires_database,
    db_session,
    reset_engine_connections,
):
    """Test tech comparator agent with real LLM."""
    analysis_id = str(uuid4())
    content = """
    React is a popular JavaScript library for building user interfaces.
    It uses a component-based architecture and virtual DOM for efficient rendering.
    React has a large ecosystem with tools like Next.js, Redux, and React Router.
    """
    content_type = "article"

    result = await run_tech_comparator(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
    )

    assert result["agent_type"] == "tech_comparator"
    assert "findings" in result
    findings = result["findings"]
    assert "primary_tech" in findings
    assert "alternatives" in findings
    assert "comparison" in findings
    assert "recommendation" in findings
    assert len(findings["alternatives"]) > 0
    assert result["processing_time_ms"] > 0


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_integration_feasibility_integration(
    requires_llm,
    requires_database,
    db_session,
    reset_engine_connections,
):
    """Test integration feasibility agent with real LLM."""
    analysis_id = str(uuid4())
    content = """
    This article explains how to integrate a new authentication library
    with Next.js and FastAPI. The library supports JWT tokens and OAuth2.
    """
    content_type = "article"

    result = await run_integration_feasibility(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
    )

    assert result["agent_type"] == "integration_feasibility"
    assert "findings" in result
    findings = result["findings"]
    assert "compatibility" in findings
    assert "migration_effort" in findings
    assert findings["migration_effort"] in ["low", "medium", "high"]
    assert "breaking_changes" in findings
    assert "integration_steps" in findings
    assert result["processing_time_ms"] > 0


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(60)
async def test_implementation_planner_integration(
    requires_llm,
    requires_database,
    db_session,
    reset_engine_connections,
):
    """Test implementation planner agent with real LLM."""
    analysis_id = str(uuid4())
    content = """
    This guide shows how to implement server-side rendering with React.
    You'll need to set up a Node.js server, configure webpack, and create
    React components that can be rendered on the server.
    """
    content_type = "article"

    result = await run_implementation_planner(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
    )

    assert result["agent_type"] == "implementation_planner"
    assert "findings" in result
    findings = result["findings"]
    assert "prerequisites" in findings
    assert "steps" in findings
    assert len(findings["steps"]) > 0
    assert "testing_strategy" in findings
    assert "estimated_time" in findings
    # Verify step structure
    for step in findings["steps"]:
        assert "step" in step
        assert "action" in step
        assert "files" in step
    assert result["processing_time_ms"] > 0


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(90)
async def test_agents_parallel_execution_with_separate_sessions(
    requires_llm,
    requires_database,
    reset_engine_connections,
):
    """Test parallel execution of multiple agents with separate database sessions.

    This test verifies that each agent gets its own database session,
    preventing concurrency errors when agents run in parallel.
    """
    import asyncio

    from app.db.session import AsyncSessionLocal

    analysis_id = str(uuid4())
    content = """
    React is a JavaScript library for building user interfaces.
    It integrates well with Next.js and can be used with FastAPI backends.
    This guide shows how to implement a full-stack application.
    """
    content_type = "article"

    # Each agent gets its own session (matching the fix in execute_agents)
    async def run_with_session_1():
        async with AsyncSessionLocal() as session:
            return await run_tech_comparator(content, content_type, analysis_id, session)

    async def run_with_session_2():
        async with AsyncSessionLocal() as session:
            return await run_integration_feasibility(content, content_type, analysis_id, session)

    async def run_with_session_3():
        async with AsyncSessionLocal() as session:
            return await run_implementation_planner(content, content_type, analysis_id, session)

    # Execute all three agents in parallel with separate sessions
    tasks = [
        run_with_session_1(),
        run_with_session_2(),
        run_with_session_3(),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify all agents completed successfully (no concurrency errors)
    assert len(results) == 3
    for result in results:
        assert not isinstance(result, Exception), f"Agent failed with: {result}"
        assert "agent_type" in result
        assert "findings" in result
        assert result["processing_time_ms"] > 0

    # Verify different agent types
    agent_types = [r["agent_type"] for r in results]
    assert "tech_comparator" in agent_types
    assert "integration_feasibility" in agent_types
    assert "implementation_planner" in agent_types
