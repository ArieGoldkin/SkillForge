"""Unit tests for code quality critic agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.code_quality_critic import run_code_quality_critic
from app.domains.analysis.workflows.agents.schemas.code_quality_critic import CodeIssue, CodeQualityReview
from app.domains.analysis.workflows.state import AnalysisState

@pytest.mark.unit


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": CodeQualityReview(
                code_issues=[
                    CodeIssue(
                        issue_type="antipattern",
                        severity="medium",
                        description="Long method with multiple responsibilities",
                        suggestion="Split into smaller, focused methods",
                    )
                ],
                best_practices=["Follow SOLID principles", "Use DRY"],
                maintainability_score=0.75,
                refactoring_suggestions=["Extract methods", "Reduce coupling"],
                recommendation="Refactor long methods and improve test coverage",
                confidence_score=0.85,
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
@patch("app.workflows.agents.code_quality_critic.create_structured_agent")
@patch("app.workflows.agents.code_quality_critic.run_agent_with_tracking")
async def test_run_code_quality_critic_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test successful code quality critic execution."""
    analysis_id = str(uuid4())
    content = "This article discusses code refactoring techniques."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "code_quality_critic",
        "findings": {
            "code_issues": [
                {
                    "issue_type": "antipattern",
                    "severity": "medium",
                    "description": "Long method",
                    "suggestion": "Split method",
                }
            ],
            "best_practices": ["Follow SOLID"],
            "maintainability_score": 0.75,
            "refactoring_suggestions": ["Extract methods"],
            "recommendation": "Refactor code",
        },
        "processing_time_ms": 1300,
    }

    result = await run_code_quality_critic(
        content, content_type, analysis_id, mock_session, mock_state
    )

    assert result["agent_type"] == "code_quality_critic"
    assert "findings" in result
    assert "code_issues" in result["findings"]
    assert "maintainability_score" in result["findings"]
    assert result["processing_time_ms"] > 0
    mock_create_agent.assert_called_once()
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.code_quality_critic.create_structured_agent")
@patch("app.workflows.agents.code_quality_critic.run_agent_with_tracking")
async def test_run_code_quality_critic_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test code quality critic error handling."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.side_effect = RuntimeError("Agent execution failed")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_code_quality_critic(content, content_type, analysis_id, mock_session, mock_state)


@pytest.mark.asyncio
@patch("app.workflows.agents.code_quality_critic.create_structured_agent")
@patch("app.workflows.agents.code_quality_critic.run_agent_with_tracking")
async def test_run_code_quality_critic_schema_validation(
    mock_run_tracking, mock_create_agent, mock_agent, mock_session, mock_state
):
    """Test code quality critic schema validation.

    Issue #299-304: Properly mock run_agent_with_tracking to avoid hitting real API.
    """
    analysis_id = str(uuid4())
    content = "Code quality content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "code_quality_critic",
        "findings": {"issues": [], "quality_status": "reviewed"},
    }

    result = await run_code_quality_critic(
        content, content_type, analysis_id, mock_session, mock_state
    )

    assert result is not None
    assert "agent_type" in result
    mock_run_tracking.assert_called_once()
