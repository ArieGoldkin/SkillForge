"""Unit tests for tech comparator agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.schemas.agents.tech_comparator import TechComparison, TechComparisonEntry
from app.domains.analysis.workflows.agents.tech_comparator import run_tech_comparator
from app.domains.analysis.workflows.state import AnalysisState



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
                confidence_score=0.87,
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
@patch("app.domains.analysis.workflows.agents.tech_comparator.create_tech_comparator_agent_with_few_shot")
@patch("app.domains.analysis.workflows.agents.tech_comparator.run_agent_with_tracking")
async def test_run_tech_comparator_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
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

    result = await run_tech_comparator(content, content_type, analysis_id, mock_session, mock_state)

    assert result["agent_type"] == "tech_comparator"
    assert "findings" in result
    assert result["findings"]["primary_tech"] == "React"
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.tech_comparator.create_tech_comparator_agent_with_few_shot")
@patch("app.domains.analysis.workflows.agents.tech_comparator.run_agent_with_tracking")
async def test_run_tech_comparator_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_session,
    mock_state,
):
    """Test error handling in tech comparator."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_run_tracking.side_effect = Exception("Agent execution failed")

    with pytest.raises(Exception, match="Agent execution failed"):
        await run_tech_comparator(content, content_type, analysis_id, mock_session, mock_state)


@pytest.mark.asyncio
@patch("app.domains.analysis.workflows.agents.result_processing.save_agent_finding", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.agents.result_processing.emit_agent_progress", new_callable=AsyncMock)
@patch("app.shared.services.messaging.sse_helpers.persist_progress_event_async", new_callable=AsyncMock)
@patch("app.domains.analysis.workflows.agents.invocation.invoke_agent", new_callable=AsyncMock)
async def test_tech_comparator_structured_output(
    mock_invoke_agent,
    mock_persist,
    mock_emit_progress,
    mock_save_finding,
    mock_agent,
    mock_session,
):
    """Test that tech comparator returns structured output."""
    analysis_id = str(uuid4())
    content = "React is a popular JavaScript library."
    content_type = "article"

    # Mock invoke_agent to return structured response
    mock_invoke_agent.return_value = {
        "structured_response": {
            "primary_tech": "React",
            "alternatives": ["Vue.js"],
            "comparison": {},
            "recommendation": "Use React",
            "confidence_score": 0.85,
        }
    }
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
