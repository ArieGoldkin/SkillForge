"""Integration tests for trend validator agent with real LLM."""

import os
from uuid import UUID, uuid4

import pytest

from app.models.analysis import Analysis
from app.workflows.agents import run_trend_validator


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

    result = await run_trend_validator(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
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
