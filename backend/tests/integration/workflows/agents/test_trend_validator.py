"""Integration tests for trend validator agent with real LLM."""

from uuid import UUID, uuid4

import pytest

from app.models.analysis import Analysis
from app.domains.analysis.workflows.agents import run_trend_validator

# Note: requires_llm fixture is provided by backend/tests/conftest.py
# It automatically checks for the correct API key based on LLM_MODEL configuration


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(180)  # 3 minutes for real LLM calls
async def test_trend_validator_integration(
    requires_llm,
    requires_database,
    db_session,
    reset_engine_connections,
    create_test_analysis,
):
    """Test trend validator agent with real LLM."""
    analysis_id = str(uuid4())
    content = """
    This article discusses React and its ecosystem. React has been widely
    adopted in 2025, with a large community and active development. The
    framework continues to evolve with new features and improvements.
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

    result = await run_trend_validator(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
        state=mock_state,
    )

    assert result["agent_type"] == "trend_validator"
    assert "findings" in result
    findings = result["findings"]
    assert "trend_assessments" in findings
    assert "modern_alternatives" in findings
    assert "future_outlook" in findings
    assert "recommendation" in findings
    assert isinstance(findings["trend_assessments"], list)
    assert result["processing_time_ms"] > 0
