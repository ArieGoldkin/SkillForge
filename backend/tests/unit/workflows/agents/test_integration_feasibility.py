"""Unit tests for integration feasibility agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.integration_feasibility import run_integration_feasibility
from app.workflows.agents.schemas import CompatibilityScore, IntegrationFeasibility


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
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
    """Mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.mark.asyncio
@patch("app.workflows.agents.integration_feasibility.create_structured_agent")
@patch("app.workflows.agents.integration_feasibility.run_agent_with_tracking")
async def test_run_integration_feasibility_success(
    mock_run_tracking,
    mock_create_agent,
    mock_session,
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

    result = await run_integration_feasibility(content, content_type, analysis_id, mock_session)

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
):
    """Test error handling in integration feasibility."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_run_tracking.side_effect = Exception("Agent failed")

    with pytest.raises(Exception, match="Agent failed"):
        await run_integration_feasibility(content, content_type, analysis_id, mock_session)
