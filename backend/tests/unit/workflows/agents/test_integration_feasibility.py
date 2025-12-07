"""Unit tests for integration feasibility agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.integration_feasibility import run_integration_feasibility
from app.workflows.agents.schemas.integration_feasibility import (
    CompatibilityScore,
    IntegrationFeasibility,
)
from app.workflows.state import AnalysisState


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None  # Explicitly disable streaming to use ainvoke
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": IntegrationFeasibility(
                compatibility={
                    "nextjs": CompatibilityScore(score=0.9, notes="Excellent integration"),
                    "fastapi": CompatibilityScore(score=0.8, notes="Good compatibility"),
                },
                migration_effort="low",
                breaking_changes=[],
                integration_steps=["Install package", "Configure settings"],
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
@patch("app.workflows.agents.integration_feasibility.create_structured_agent")
@patch("app.workflows.agents.integration_feasibility.run_agent_with_tracking")
async def test_run_integration_feasibility_success(
    mock_run_tracking,
    mock_create_agent,
    mock_session,
    mock_state,
):
    """Test successful integration feasibility execution."""
    analysis_id = str(uuid4())
    content = "This article discusses integrating a new library with Next.js."
    content_type = "article"

    mock_run_tracking.return_value = {
        "agent_type": "integration_feasibility",
        "findings": {
            "compatibility": {
                "nextjs": {"score": 0.9, "notes": "Excellent"},
            },
            "migration_effort": "low",
            "breaking_changes": [],
            "integration_steps": ["Step 1", "Step 2"],
        },
        "processing_time_ms": 1500,
    }

    result = await run_integration_feasibility(
        content, content_type, analysis_id, mock_session, mock_state
    )

    assert result["agent_type"] == "integration_feasibility"
    assert "findings" in result
    assert result["findings"]["migration_effort"] == "low"
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.integration_feasibility.create_structured_agent")
@patch("app.workflows.agents.integration_feasibility.run_agent_with_tracking")
async def test_integration_feasibility_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_session,
    mock_state,
):
    """Test error handling in integration feasibility."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_run_tracking.side_effect = Exception("Agent failed")

    with pytest.raises(Exception, match="Agent failed"):
        await run_integration_feasibility(
            content, content_type, analysis_id, mock_session, mock_state
        )
