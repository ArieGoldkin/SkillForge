"""Integration tests for code quality critic agent with real LLM."""

import os
from uuid import UUID, uuid4

import pytest

from app.models.analysis import Analysis
from app.workflows.agents import run_code_quality_critic


@pytest.fixture
def requires_llm():
    """Skip test if LLM is not configured."""
    llm_model = os.environ.get("LLM_MODEL", "")
    if not llm_model:
        pytest.skip("LLM_MODEL not configured")
    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_OPENAI_API_KEY")
    if not openai_key:
        pytest.skip("OpenAI API key not available")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(180)  # 3 minutes for real LLM calls
async def test_code_quality_critic_integration(
    requires_llm,
    requires_database,
    db_session,
    reset_engine_connections,
    create_test_analysis,
):
    """Test code quality critic agent with real LLM."""
    analysis_id = str(uuid4())
    content = """
    This article explains SOLID principles and clean code practices. It covers
    refactoring techniques, code smells, and maintainability best practices.
    The guide shows examples of good and bad code patterns.
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

    result = await run_code_quality_critic(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
    )

    assert result["agent_type"] == "code_quality_critic"
    assert "findings" in result
    findings = result["findings"]
    assert "code_issues" in findings
    assert "best_practices" in findings
    assert "maintainability_score" in findings
    assert 0.0 <= findings["maintainability_score"] <= 1.0
    assert "refactoring_suggestions" in findings
    assert "recommendation" in findings
    assert result["processing_time_ms"] > 0
