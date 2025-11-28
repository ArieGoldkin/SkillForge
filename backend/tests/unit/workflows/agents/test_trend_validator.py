"""Unit tests for trend validator agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.schemas.trend_validator import TrendAssessment, TrendValidation
from app.workflows.agents.trend_validator import run_trend_validator


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
            )
        }
    )
    return agent


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
@patch("app.workflows.agents.trend_validator.create_structured_agent")
@patch("app.workflows.agents.trend_validator.run_agent_with_tracking")
async def test_run_trend_validator_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
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

    result = await run_trend_validator(content, content_type, analysis_id, mock_session)

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
):
    """Test trend validator error handling."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.side_effect = RuntimeError("Agent execution failed")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_trend_validator(content, content_type, analysis_id, mock_session)


@pytest.mark.asyncio
@patch("app.workflows.agents.trend_validator.create_structured_agent")
async def test_run_trend_validator_schema_validation(mock_create_agent, mock_agent, mock_session):
    """Test trend validator schema validation."""
    analysis_id = str(uuid4())
    content = "Trend content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent

    result = await run_trend_validator(content, content_type, analysis_id, mock_session)

    assert result is not None
    assert "agent_type" in result
