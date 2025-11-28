"""Unit tests for tech comparator agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.schemas.tech_comparator import TechComparison, TechComparisonEntry
from app.workflows.agents.tech_comparator import run_tech_comparator


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None  # Explicitly disable streaming to use ainvoke
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": TechComparison(
                primary_tech="React",
                alternatives=["Vue.js", "Angular"],
                comparison={
                    "React": TechComparisonEntry(
                        pros=["Large ecosystem", "Strong community"],
                        cons=["Steep learning curve"],
                        use_cases=["SPAs", "Complex UIs"],
                    ),
                    "Vue.js": TechComparisonEntry(
                        pros=["Easy to learn", "Good documentation"],
                        cons=["Smaller ecosystem"],
                        use_cases=["Small projects", "Rapid prototyping"],
                    ),
                },
                recommendation="Use React for complex applications, Vue.js for simpler projects",
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
@patch("app.workflows.agents.tech_comparator.create_structured_agent")
@patch("app.workflows.agents.tech_comparator.run_agent_with_tracking")
async def test_run_tech_comparator_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
):
    """Test successful tech comparator execution."""
    analysis_id = str(uuid4())
    content = "This article discusses React hooks and best practices."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "tech_comparator",
        "findings": {
            "primary_tech": "React",
            "alternatives": ["Vue.js", "Angular"],
            "comparison": {},
            "recommendation": "Use React",
        },
        "processing_time_ms": 1200,
    }

    result = await run_tech_comparator(content, content_type, analysis_id, mock_session)

    assert result["agent_type"] == "tech_comparator"
    assert "findings" in result
    assert result["findings"]["primary_tech"] == "React"
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.tech_comparator.create_structured_agent")
@patch("app.workflows.agents.tech_comparator.run_agent_with_tracking")
async def test_run_tech_comparator_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_session,
):
    """Test error handling in tech comparator."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_run_tracking.side_effect = Exception("Agent execution failed")

    with pytest.raises(Exception, match="Agent execution failed"):
        await run_tech_comparator(content, content_type, analysis_id, mock_session)


@pytest.mark.asyncio
@patch("app.workflows.agents.base.create_structured_agent")
@patch("app.workflows.agents.result_processing.emit_agent_progress")
@patch("app.workflows.agents.result_processing.save_agent_finding")
async def test_tech_comparator_structured_output(
    mock_save_finding,
    mock_emit_progress,
    mock_create_agent,
    mock_agent,
    mock_session,
):
    """Test that tech comparator returns structured output."""
    analysis_id = str(uuid4())
    content = "React is a popular JavaScript library."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_save_finding.return_value = MagicMock()

    result = await run_agent_with_tracking(
        agent=mock_agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        session=mock_session,
    )

    assert result["agent_type"] == "tech_comparator"
    assert "findings" in result
    assert isinstance(result["findings"], dict)
    mock_emit_progress.assert_called()
