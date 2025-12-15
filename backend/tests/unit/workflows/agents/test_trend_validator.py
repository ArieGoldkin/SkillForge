"""Unit tests for trend validator agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.schemas.trend_validator import TrendAssessment, TrendValidation
from app.workflows.agents.trend_validator import run_trend_validator
from app.workflows.state import AnalysisState


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": TrendValidation(
                trend_assessments=[
                    TrendAssessment(
                        category="framework",
                        trend_status="current",
                        evidence="High GitHub stars and active community",
                        adoption_rate="growing",
                    )
                ],
                modern_alternatives=["Next.js", "Remix"],
                future_outlook="Technology is well-maintained and has strong community support",
                recommendation="Technology is current and recommended for new projects",
                confidence_score=0.83,
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
@patch("app.workflows.agents.trend_validator.create_structured_agent")
@patch("app.workflows.agents.trend_validator.run_agent_with_tracking")
async def test_run_trend_validator_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test successful trend validator execution."""
    analysis_id = str(uuid4())
    content = "This article discusses React and modern frameworks."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "trend_validator",
        "findings": {
            "trend_assessments": [
                {
                    "category": "framework",
                    "trend_status": "current",
                    "evidence": "High adoption",
                    "adoption_rate": "growing",
                }
            ],
            "modern_alternatives": ["Next.js"],
            "future_outlook": "Well-maintained",
            "recommendation": "Recommended for new projects",
        },
        "processing_time_ms": 1200,
    }

    result = await run_trend_validator(content, content_type, analysis_id, mock_session, mock_state)

    assert result["agent_type"] == "trend_validator"
    assert "findings" in result
    assert "trend_assessments" in result["findings"]
    assert result["processing_time_ms"] > 0
    mock_create_agent.assert_called_once()
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.trend_validator.create_structured_agent")
@patch("app.workflows.agents.trend_validator.run_agent_with_tracking")
async def test_run_trend_validator_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test trend validator error handling."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.side_effect = RuntimeError("Agent execution failed")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_trend_validator(content, content_type, analysis_id, mock_session, mock_state)


@pytest.mark.asyncio
@patch("app.workflows.agents.trend_validator.create_structured_agent")
@patch("app.workflows.agents.trend_validator.run_agent_with_tracking")
async def test_run_trend_validator_schema_validation(
    mock_run_tracking, mock_create_agent, mock_agent, mock_session, mock_state
):
    """Test trend validator schema validation.

    Issue #299-304: Properly mock run_agent_with_tracking to avoid hitting real API.
    """
    analysis_id = str(uuid4())
    content = "Trend content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "trend_validator",
        "findings": {"trends": [], "validation_status": "validated"},
    }

    result = await run_trend_validator(content, content_type, analysis_id, mock_session, mock_state)

    assert result is not None
    assert "agent_type" in result
    mock_run_tracking.assert_called_once()
