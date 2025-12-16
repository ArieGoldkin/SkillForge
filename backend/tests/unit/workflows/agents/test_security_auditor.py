"""Unit tests for security auditor agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.schemas.security_auditor import SecurityAudit, SecurityRisk
from app.domains.analysis.workflows.agents.security_auditor import run_security_auditor
from app.domains.analysis.workflows.state import AnalysisState

@pytest.mark.unit


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None  # Explicitly disable streaming to use ainvoke
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": SecurityAudit(
                security_risks=[
                    SecurityRisk(
                        risk_type="authentication",
                        severity="high",
                        description="No rate limiting on login endpoints",
                        mitigation="Implement rate limiting and CAPTCHA",
                    )
                ],
                best_practices=["Use HTTPS", "Implement CSRF protection"],
                compliance_notes=["OWASP A07:2021 - Identification and Authentication Failures"],
                recommendation="Implement multi-factor authentication and rate limiting",
                confidence_score=0.90,
            )
        }
    )
    return agent


@pytest.fixture
def mock_session():
    """Mock database session.

    Note: session.add() is synchronous, not async, so it's a MagicMock.
    session.execute(), commit(), and refresh() are async, so they're AsyncMock.
    """
    session = AsyncMock(spec=AsyncSession)
    # session.add() is synchronous, not async
    session.add = MagicMock(return_value=None)
    session.commit = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)
    # Mock async methods that return results
    # Note: scalar_one_or_none() is synchronous, not async
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=MagicMock())  # Return mock Analysis
    session.execute = AsyncMock(return_value=mock_result)
    return session


@pytest.fixture
def mock_state():
    """Mock analysis state."""
    return AnalysisState(
        analysis_id=uuid4(),
        url="https://example.com",
        content_type="article",
        skill_level="intermediate",
        raw_content="test content",
        extraction_metadata={},
        content_embedding=[0.1] * 1536,
        supervisor_decision={},
        agent_findings=[],
        aggregated_insights={},
        artifact_id=None,
    )


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.security_auditor.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.security_auditor.run_agent_with_tracking")
async def test_run_security_auditor_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test successful security auditor execution."""
    analysis_id = str(uuid4())
    content = "This article discusses authentication best practices."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "security_auditor",
        "findings": {
            "security_risks": [
                {
                    "risk_type": "authentication",
                    "severity": "high",
                    "description": "No rate limiting",
                    "mitigation": "Implement rate limiting",
                }
            ],
            "best_practices": ["Use HTTPS"],
            "compliance_notes": ["OWASP A07:2021"],
            "recommendation": "Implement MFA",
        },
        "processing_time_ms": 1500,
    }

    result = await run_security_auditor(
        content, content_type, analysis_id, mock_session, mock_state
    )

    assert result["agent_type"] == "security_auditor"
    assert "findings" in result
    assert "security_risks" in result["findings"]
    assert result["processing_time_ms"] > 0
    mock_create_agent.assert_called_once()
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.security_auditor.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.security_auditor.run_agent_with_tracking")
async def test_run_security_auditor_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test security auditor error handling."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.side_effect = RuntimeError("Agent execution failed")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_security_auditor(content, content_type, analysis_id, mock_session, mock_state)


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.security_auditor.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.security_auditor.run_agent_with_tracking")
async def test_run_security_auditor_schema_validation(
    mock_run_tracking, mock_create_agent, mock_agent, mock_session, mock_state
):
    """Test security auditor schema validation.

    Issue #299-304: Properly mock run_agent_with_tracking to avoid hitting real API.
    """
    analysis_id = str(uuid4())
    content = "Security content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "security_auditor",
        "findings": {"vulnerabilities": [], "security_status": "secure"},
    }

    result = await run_security_auditor(
        content, content_type, analysis_id, mock_session, mock_state
    )

    # Verify schema validation passed (no exception raised)
    assert result is not None
    assert "agent_type" in result
    mock_run_tracking.assert_called_once()
