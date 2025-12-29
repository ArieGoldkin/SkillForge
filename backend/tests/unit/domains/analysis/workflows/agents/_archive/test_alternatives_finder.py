"""Unit tests for alternatives finder agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.domains.analysis.workflows.agents.alternatives_finder import run_alternatives_finder
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.schemas.agents.alternatives_finder import (
    Alternative,
    AlternativesFinderOutput,
)
from app.domains.analysis.workflows.state import AnalysisState


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": AlternativesFinderOutput(
                subject="React 19",
                alternatives=[
                    Alternative(
                        name="Vue.js 3.x",
                        description="Progressive JavaScript framework with approachable learning curve",
                        comparison_notes="Easier to learn, smaller bundle size (25KB vs 45KB gzipped). Less extensive ecosystem.",
                        relevance_score=0.9,
                        url="https://vuejs.org/",
                    ),
                    Alternative(
                        name="Svelte 5",
                        description="Compiler-based framework with minimal runtime overhead",
                        comparison_notes="Smallest bundle size (15KB), no virtual DOM. Smaller ecosystem.",
                        relevance_score=0.85,
                        url="https://svelte.dev/",
                    ),
                ],
                recommendation="React 19 remains best for large SPAs. Consider Vue 3 for faster onboarding or Svelte 5 for minimal bundle size.",
                confidence_score=0.88,
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
@patch(
    "app.domains.analysis.workflows.agents.alternatives_finder.create_agent_with_optional_few_shot"
)
@patch("app.domains.analysis.workflows.agents.alternatives_finder.run_agent_with_tracking")
async def test_run_alternatives_finder_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test successful alternatives finder execution."""
    analysis_id = str(uuid4())
    content = "This article discusses React 19 and modern frontend frameworks."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "alternatives_finder",
        "findings": {
            "subject": "React 19",
            "alternatives": [
                {
                    "name": "Vue.js 3.x",
                    "description": "Progressive JavaScript framework",
                    "comparison_notes": "Easier to learn, smaller bundle size",
                    "relevance_score": 0.9,
                    "url": "https://vuejs.org/",
                }
            ],
            "recommendation": "React 19 remains best for large SPAs",
            "confidence_score": 0.88,
        },
        "processing_time_ms": 1234,
    }

    result = await run_alternatives_finder(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=mock_session,
        state=mock_state,
        tools=None,
    )

    # Verify agent was created with correct parameters
    mock_create_agent.assert_called_once()
    create_call_kwargs = mock_create_agent.call_args.kwargs
    assert create_call_kwargs["agent_type"] == "alternatives_finder"
    assert create_call_kwargs["content"] == content
    assert "alternatives" in create_call_kwargs["system_prompt"].lower()

    # Verify agent was run with tracking
    mock_run_tracking.assert_called_once()
    tracking_call_kwargs = mock_run_tracking.call_args.kwargs
    assert tracking_call_kwargs["agent_type"] == "alternatives_finder"
    assert tracking_call_kwargs["content"] == content
    assert tracking_call_kwargs["content_type"] == content_type

    # Verify result structure
    assert result["agent_type"] == "alternatives_finder"
    assert "findings" in result
    assert result["findings"]["subject"] == "React 19"
    assert len(result["findings"]["alternatives"]) == 1
    assert result["findings"]["confidence_score"] == 0.88


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.alternatives_finder.create_agent_with_optional_few_shot"
)
@patch("app.domains.analysis.workflows.agents.alternatives_finder.run_agent_with_tracking")
async def test_run_alternatives_finder_with_tools(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test alternatives finder with Tavily search tools."""
    analysis_id = str(uuid4())
    content = "This article discusses LangGraph for multi-agent systems."
    content_type = "article"

    # Mock Tavily search tool
    mock_tavily_tool = MagicMock()
    mock_tavily_tool.name = "tavily_search"
    tools = [mock_tavily_tool]

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "alternatives_finder",
        "findings": {
            "subject": "LangGraph",
            "alternatives": [
                {
                    "name": "AutoGen",
                    "description": "Multi-agent framework by Microsoft",
                    "comparison_notes": "Similar capabilities but different API design",
                    "relevance_score": 0.85,
                    "url": "https://microsoft.github.io/autogen/",
                }
            ],
            "recommendation": "LangGraph offers better LangChain integration",
            "confidence_score": 0.82,
        },
        "processing_time_ms": 1567,
    }

    result = await run_alternatives_finder(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=mock_session,
        state=mock_state,
        tools=tools,
    )

    # Verify tools were passed to agent creation
    mock_create_agent.assert_called_once()
    create_call_kwargs = mock_create_agent.call_args.kwargs
    assert create_call_kwargs["tools"] == tools

    # Verify result
    assert result["agent_type"] == "alternatives_finder"
    assert result["findings"]["subject"] == "LangGraph"
    assert len(result["findings"]["alternatives"]) == 1


@pytest.mark.asyncio
@patch(
    "app.domains.analysis.workflows.agents.alternatives_finder.create_agent_with_optional_few_shot"
)
@patch("app.domains.analysis.workflows.agents.alternatives_finder.run_agent_with_tracking")
async def test_run_alternatives_finder_skill_level_adaptation(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
    mock_state,
):
    """Test alternatives finder adapts to skill level."""
    analysis_id = str(uuid4())
    content = "Python web frameworks comparison"
    content_type = "article"

    # Set skill level to beginner
    mock_state["skill_level"] = "beginner"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "alternatives_finder",
        "findings": {
            "subject": "Flask",
            "alternatives": [],
            "recommendation": "Start with Flask for simplicity",
            "confidence_score": 0.85,
        },
        "processing_time_ms": 980,
    }

    result = await run_alternatives_finder(
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        session=mock_session,
        state=mock_state,
        tools=None,
    )

    # Verify skill level was used
    mock_create_agent.assert_called_once()
    create_call_kwargs = mock_create_agent.call_args.kwargs
    # Should contain beginner-specific instructions
    assert (
        "beginner" in create_call_kwargs["system_prompt"].lower()
        or "onboarding" in create_call_kwargs["system_prompt"].lower()
    )

    assert result["agent_type"] == "alternatives_finder"
