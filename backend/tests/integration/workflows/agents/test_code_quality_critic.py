"""Integration tests for code quality critic agent with real LLM."""

from uuid import UUID, uuid4

import pytest

from app.db.models.analysis import Analysis
from app.domains.analysis.workflows.agents import run_code_quality_critic

# Note: requires_llm fixture is provided by backend/tests/conftest.py
# It automatically checks for the correct API key based on LLM_MODEL configuration


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

    from app.domains.analysis.workflows.state import AnalysisState

    mock_state = AnalysisState(
        analysis_id=UUID(analysis_id),
        url="https://example.com",
        content_type=content_type,
        skill_level="intermediate",  # Default skill level
        raw_content=content,
        extraction_metadata={},
        content_embedding=[0.1] * 1536,
        supervisor_decision={},
        agent_findings=[],
        aggregated_insights={},
        artifact_id=None,
    )

    result = await run_code_quality_critic(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
        state=mock_state,
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
