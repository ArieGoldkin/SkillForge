"""Unit tests for performance analyst agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.performance_analyst import run_performance_analyst
from app.workflows.agents.schemas.performance_analyst import PerformanceAnalysis, PerformanceMetric


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": PerformanceAnalysis(
                performance_metrics=[
                    PerformanceMetric(
                        metric_name="latency",
                        current_value="500ms",
                        target_value="<200ms",
                        notes="API response time",
                    )
                ],
                bottlenecks=["Database queries", "Network latency"],
                optimization_opportunities=["Add caching", "Optimize queries"],
                scaling_considerations="Horizontal scaling recommended",
                recommendation="Implement Redis caching and optimize database queries",
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
@patch("app.workflows.agents.performance_analyst.create_structured_agent")
@patch("app.workflows.agents.performance_analyst.run_agent_with_tracking")
async def test_run_performance_analyst_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
):
    """Test successful performance analyst execution."""
    analysis_id = str(uuid4())
    content = "This article discusses API performance optimization."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "performance_analyst",
        "findings": {
            "performance_metrics": [{"metric_name": "latency", "current_value": "500ms"}],
            "bottlenecks": ["Database queries"],
            "optimization_opportunities": ["Add caching"],
            "scaling_considerations": "Horizontal scaling",
            "recommendation": "Implement caching",
        },
        "processing_time_ms": 1400,
    }

    result = await run_performance_analyst(content, content_type, analysis_id, mock_session)

    assert result["agent_type"] == "performance_analyst"
    assert "findings" in result
    assert "performance_metrics" in result["findings"]
    assert result["processing_time_ms"] > 0
    mock_create_agent.assert_called_once()
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.performance_analyst.create_structured_agent")
@patch("app.workflows.agents.performance_analyst.run_agent_with_tracking")
async def test_run_performance_analyst_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
):
    """Test performance analyst error handling."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.side_effect = RuntimeError("Agent execution failed")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_performance_analyst(content, content_type, analysis_id, mock_session)


@pytest.mark.asyncio
@patch("app.workflows.agents.performance_analyst.create_structured_agent")
async def test_run_performance_analyst_schema_validation(
    mock_create_agent, mock_agent, mock_session
):
    """Test performance analyst schema validation."""
    analysis_id = str(uuid4())
    content = "Performance content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent

    result = await run_performance_analyst(content, content_type, analysis_id, mock_session)

    assert result is not None
    assert "agent_type" in result
