"""Unit tests for implementation planner agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.implementation_planner import run_implementation_planner
from app.workflows.agents.schemas.implementation_planner import (
    ImplementationPlan,
    ImplementationStep,
)


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None  # Explicitly disable streaming to use ainvoke
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": ImplementationPlan(
                prerequisites=["Node.js 18+", "npm installed"],
                steps=[
                    ImplementationStep(
                        step=1,
                        action="Install dependencies",
                        files=["package.json"],
                    ),
                    ImplementationStep(
                        step=2,
                        action="Configure settings",
                        files=[".env", "config.js"],
                    ),
                ],
                testing_strategy="Unit tests with Jest, integration tests with Playwright",
                estimated_time="2-3 hours",
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
@patch("app.workflows.agents.implementation_planner.create_structured_agent")
@patch("app.workflows.agents.implementation_planner.run_agent_with_tracking")
async def test_run_implementation_planner_success(
    mock_run_tracking,
    mock_create_agent,
    mock_session,
):
    """Test successful implementation planner execution."""
    analysis_id = str(uuid4())
    content = "This article explains how to implement a new feature."
    content_type = "article"

    mock_run_tracking.return_value = {
        "agent_type": "implementation_planner",
        "findings": {
            "prerequisites": ["Node.js"],
            "steps": [
                {"step": 1, "action": "Install", "files": []},
            ],
            "testing_strategy": "Unit tests",
            "estimated_time": "1 hour",
        },
        "processing_time_ms": 1800,
    }

    result = await run_implementation_planner(content, content_type, analysis_id, mock_session)

    assert result["agent_type"] == "implementation_planner"
    assert "findings" in result
    assert "steps" in result["findings"]
    assert len(result["findings"]["steps"]) > 0
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.implementation_planner.create_structured_agent")
@patch("app.workflows.agents.implementation_planner.run_agent_with_tracking")
async def test_implementation_planner_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_session,
):
    """Test error handling in implementation planner."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_run_tracking.side_effect = Exception("Agent failed")

    with pytest.raises(Exception, match="Agent failed"):
        await run_implementation_planner(content, content_type, analysis_id, mock_session)
