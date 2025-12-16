"""Unit tests for performance analyst agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.performance_analyst import run_performance_analyst
from app.domains.analysis.workflows.agents.schemas.performance_analyst import PerformanceAnalysis, PerformanceMetric
from app.domains.analysis.workflows.state import AnalysisState



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
                confidence_score=0.82,
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
@patch("app.domains.analysis.workflows.agents.performance_analyst.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.performance_analyst.run_agent_with_tracking")
async def test_run_performance_analyst_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
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

    result = await run_performance_analyst(
        content, content_type, analysis_id, mock_session, mock_state
    )

    assert result["agent_type"] == "performance_analyst"
    assert "findings" in result
    assert "performance_metrics" in result["findings"]
    assert result["processing_time_ms"] > 0
    mock_create_agent.assert_called_once()
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.performance_analyst.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.performance_analyst.run_agent_with_tracking")
async def test_run_performance_analyst_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test performance analyst error handling."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.side_effect = RuntimeError("Agent execution failed")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_performance_analyst(content, content_type, analysis_id, mock_session, mock_state)


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.performance_analyst.create_structured_agent")
@patch("app.domains.analysis.workflows.agents.performance_analyst.run_agent_with_tracking")
async def test_run_performance_analyst_schema_validation(
    mock_run_tracking, mock_create_agent, mock_agent, mock_session, mock_state
):
    """Test performance analyst schema validation.

    Issue #299-304: Properly mock run_agent_with_tracking to avoid hitting real API.
    """
    analysis_id = str(uuid4())
    content = "Performance content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "performance_analyst",
        "findings": {"optimizations": [], "performance_status": "analyzed"},
    }

    result = await run_performance_analyst(
        content, content_type, analysis_id, mock_session, mock_state
    )

    assert result is not None
    assert "agent_type" in result
    mock_run_tracking.assert_called_once()
