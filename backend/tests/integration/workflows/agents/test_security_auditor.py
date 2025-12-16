"""Integration tests for security auditor agent with real LLM."""

from uuid import UUID, uuid4

import pytest

from app.models.analysis import Analysis
from app.domains.analysis.workflows.agents import run_security_auditor

# Note: requires_llm fixture is provided by backend/tests/conftest.py
# It automatically checks for the correct API key based on LLM_MODEL configuration


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.external
@pytest.mark.timeout(180)  # 3 minutes for real LLM calls
async def test_security_auditor_integration(
    requires_llm,
    requires_database,
    db_session,
    reset_engine_connections,
    create_test_analysis,
):
    """Test security auditor agent with real LLM."""
    analysis_id = str(uuid4())
    content = """
    This article explains authentication best practices. It covers JWT tokens,
    password hashing, and rate limiting. The guide mentions OWASP Top 10
    security risks and how to mitigate them.
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

    result = await run_security_auditor(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=db_session,
        state=mock_state,
    )

    assert result["agent_type"] == "security_auditor"
    assert "findings" in result
    findings = result["findings"]
    assert "security_risks" in findings
    assert "best_practices" in findings
    assert "compliance_notes" in findings
    assert "recommendation" in findings
    assert isinstance(findings["security_risks"], list)
    assert result["processing_time_ms"] > 0
