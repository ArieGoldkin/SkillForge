"""Integration tests for performance analyst agent with real LLM."""

from uuid import UUID, uuid4

import pytest

from app.models.analysis import Analysis
from app.workflows.agents import run_performance_analyst

# Note: requires_llm fixture is provided by backend/tests/conftest.py
# It automatically checks for the correct API key based on LLM_MODEL configuration


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(180)  # 3 minutes for real LLM calls
async def test_performance_analyst_integration(
    requires_llm,
    requires_database,
    db_session,
    reset_engine_connections,
    create_test_analysis,
):
    """Test performance analyst agent with real LLM."""
    analysis_id = str(uuid4())
    content = """
    This article discusses API performance optimization techniques. It covers
    caching strategies, database query optimization, and horizontal scaling.
    The guide explains how to reduce latency and improve throughput.
    """
    content_type = "article"

    # Create Analysis record before calling agent (required for foreign key)
    analysis = Analysis(
        id=UUID(analysis_id),
        url="https://example.com",
        content_type=content_type,
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()

    result = await run_performance_analyst(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
    )

    assert result["agent_type"] == "performance_analyst"
    assert "findings" in result
    findings = result["findings"]
    assert "performance_metrics" in findings
    assert "bottlenecks" in findings
    assert "optimization_opportunities" in findings
    assert "scaling_considerations" in findings
    assert "recommendation" in findings
    assert result["processing_time_ms"] > 0
