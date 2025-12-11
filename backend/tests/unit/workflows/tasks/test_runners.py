"""Unit tests for agent runner functions with session management.

Tests verify Issue #268: Agent nodes load content from artifact store
with fallback to raw_content for backward compatibility.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workflows.state import AnalysisState, ContentRef
from app.workflows.tasks.runners import (
    run_code_quality_critic_with_session,
    run_dependency_mapper_with_session,
    run_implementation_planner_with_session,
    run_integration_feasibility_with_session,
    run_performance_analyst_with_session,
    run_security_auditor_with_session,
    run_tech_comparator_with_session,
    run_trend_validator_with_session,
)


@pytest.fixture
def mock_analysis_id():
    """Create a test analysis ID."""
    return uuid.uuid4()


@pytest.fixture
def test_content():
    """Create test content."""
    return "Test article content about React and Vue.js"


@pytest.fixture
def test_content_type():
    """Create test content type."""
    return "article"


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


@pytest.fixture
def mock_state():
    """Create a mock analysis state."""
    return AnalysisState(
        analysis_id=uuid.uuid4(),
        url="https://example.com",
        content_type="article",
        skill_level="intermediate",  # Add default skill level
        raw_content="test content",
        extraction_metadata={},
        content_embedding=[0.1] * 1536,
        supervisor_decision={},
        agent_findings=[],
        aggregated_insights={},
        artifact_id=None,
    )


@patch("app.workflows.tasks.runners.run_tech_comparator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_tech_comparator_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test tech comparator runner with session management."""
    # Make AsyncSessionLocal return our mock session when called
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_tech_comparator", mock_run_agent):
        result = await run_tech_comparator_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state
    )


@patch("app.workflows.tasks.runners.run_integration_feasibility")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_integration_feasibility_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test integration feasibility runner with session management."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_integration_feasibility", mock_run_agent):
        result = await run_integration_feasibility_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state
    )


@patch("app.workflows.tasks.runners.run_implementation_planner")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_implementation_planner_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test implementation planner runner with session management."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_implementation_planner", mock_run_agent):
        result = await run_implementation_planner_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state
    )


@patch("app.workflows.tasks.runners.run_security_auditor")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_security_auditor_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test security auditor runner with session management."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_security_auditor", mock_run_agent):
        result = await run_security_auditor_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    # Security auditor now passes tools=[] for MCP integration
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state, tools=[]
    )


@patch("app.workflows.tasks.runners.run_performance_analyst")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_performance_analyst_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test performance analyst runner with session management."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_performance_analyst", mock_run_agent):
        result = await run_performance_analyst_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state
    )


@patch("app.workflows.tasks.runners.run_code_quality_critic")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_code_quality_critic_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test code quality critic runner with session management."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_code_quality_critic", mock_run_agent):
        result = await run_code_quality_critic_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state
    )


@patch("app.workflows.tasks.runners.run_trend_validator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_trend_validator_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test trend validator runner with session management."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_trend_validator", mock_run_agent):
        result = await run_trend_validator_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state
    )


@patch("app.workflows.tasks.runners.run_dependency_mapper")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_dependency_mapper_with_session(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test dependency mapper runner with session management."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_dependency_mapper", mock_run_agent):
        result = await run_dependency_mapper_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    assert result == {"findings": "test"}
    # Dependency mapper now passes tools=[] for MCP integration
    mock_run_agent.assert_called_once_with(
        test_content, test_content_type, mock_analysis_id, mock_session, mock_state, tools=[]
    )


# GeneratorExit handling tests - verify graceful degradation
@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_tech_comparator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_tech_comparator_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in tech comparator runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_tech_comparator", mock_run_agent):
        result = await run_tech_comparator_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_implementation_planner")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_implementation_planner_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in implementation planner runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_implementation_planner", mock_run_agent):
        result = await run_implementation_planner_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_security_auditor")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_security_auditor_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in security auditor runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_security_auditor", mock_run_agent):
        result = await run_security_auditor_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_integration_feasibility")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_integration_feasibility_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in integration feasibility runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_integration_feasibility", mock_run_agent):
        result = await run_integration_feasibility_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_performance_analyst")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_performance_analyst_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in performance analyst runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_performance_analyst", mock_run_agent):
        result = await run_performance_analyst_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_code_quality_critic")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_code_quality_critic_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in code quality critic runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_code_quality_critic", mock_run_agent):
        result = await run_code_quality_critic_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_trend_validator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_trend_validator_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in trend validator runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_trend_validator", mock_run_agent):
        result = await run_trend_validator_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_dependency_mapper")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_dependency_mapper_with_session_handles_generatorexit(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
    mock_state,
):
    """Test that GeneratorExit is handled gracefully in dependency mapper runner."""
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(side_effect=GeneratorExit("Timeout cancellation"))

    with patch("app.workflows.tasks.runners.run_dependency_mapper", mock_run_agent):
        result = await run_dependency_mapper_with_session(
            test_content, test_content_type, mock_analysis_id, mock_state
        )

    # Should return empty dict on GeneratorExit for graceful degradation
    assert result == {}
    mock_run_agent.assert_called_once()


# Issue #268: Test artifact loading with content_ref
@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.ArtifactStore")
@patch("app.workflows.tasks.runners.run_tech_comparator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_tech_comparator_loads_from_artifact(
    mock_session_local,
    mock_run_agent,
    mock_artifact_store_class,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
):
    """Test that tech comparator loads content from artifact store when content_ref present."""
    # Setup content_ref in state
    analysis_id = str(mock_analysis_id)
    content_ref: ContentRef = {
        "uri": f"analysis://{analysis_id}/content",
        "summary": "Test summary",
        "size_bytes": 1000,
        "content_type": "text/markdown",
        "available_sections": ["summary", "full"],
    }
    state = AnalysisState(
        analysis_id=mock_analysis_id,
        url="https://example.com",
        content_type="article",
        skill_level="intermediate",
        raw_content="fallback content",
        content_ref=content_ref,
        extraction_metadata={},
        content_embedding=[0.1] * 1536,
        supervisor_decision={},
        agent_findings=[],
        aggregated_insights={},
        artifact_id=None,
    )

    # Mock artifact store load
    mock_store_instance = MagicMock()
    mock_store_instance.load = AsyncMock(return_value="loaded from artifact")
    mock_artifact_store_class.return_value = mock_store_instance

    # Mock session and agent
    mock_session_local.return_value = mock_session
    mock_run_agent.return_value = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_tech_comparator", mock_run_agent):
        result = await run_tech_comparator_with_session(
            test_content, test_content_type, mock_analysis_id, state
        )

    # Verify artifact store was used
    mock_artifact_store_class.assert_called_once_with(mock_session)
    mock_store_instance.load.assert_called_once()

    # Verify agent was called with loaded content, not fallback
    assert mock_run_agent.call_count == 1
    call_args = mock_run_agent.call_args[0]
    assert call_args[0] == "loaded from artifact"  # First argument should be loaded content


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.run_tech_comparator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_tech_comparator_falls_back_to_raw_content(
    mock_session_local,
    mock_run_agent,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
):
    """Test that tech comparator falls back to raw_content when content_ref missing."""
    # State without content_ref
    state = AnalysisState(
        analysis_id=mock_analysis_id,
        url="https://example.com",
        content_type="article",
        skill_level="intermediate",
        raw_content="fallback content",
        extraction_metadata={},
        content_embedding=[0.1] * 1536,
        supervisor_decision={},
        agent_findings=[],
        aggregated_insights={},
        artifact_id=None,
    )

    # Mock session and agent
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_tech_comparator", mock_run_agent):
        result = await run_tech_comparator_with_session(
            test_content, test_content_type, mock_analysis_id, state
        )

    # Verify agent was called with fallback content
    assert mock_run_agent.call_count == 1
    call_args = mock_run_agent.call_args[0]
    assert call_args[0] == test_content  # Should use fallback content


@pytest.mark.asyncio
@patch("app.workflows.tasks.runners.ArtifactStore")
@patch("app.workflows.tasks.runners.run_tech_comparator")
@patch("app.db.session.AsyncSessionLocal")
async def test_run_tech_comparator_falls_back_on_artifact_error(
    mock_session_local,
    mock_run_agent,
    mock_artifact_store_class,
    mock_analysis_id,
    test_content,
    test_content_type,
    mock_session,
):
    """Test that tech comparator falls back to raw_content when artifact loading fails."""
    # Setup content_ref in state
    analysis_id = str(mock_analysis_id)
    content_ref: ContentRef = {
        "uri": f"analysis://{analysis_id}/content",
        "summary": "Test summary",
        "size_bytes": 1000,
        "content_type": "text/markdown",
        "available_sections": ["summary", "full"],
    }
    state = AnalysisState(
        analysis_id=mock_analysis_id,
        url="https://example.com",
        content_type="article",
        skill_level="intermediate",
        raw_content="fallback content",
        content_ref=content_ref,
        extraction_metadata={},
        content_embedding=[0.1] * 1536,
        supervisor_decision={},
        agent_findings=[],
        aggregated_insights={},
        artifact_id=None,
    )

    # Mock artifact store load to raise error
    mock_store_instance = MagicMock()
    mock_store_instance.load = AsyncMock(side_effect=Exception("Database error"))
    mock_artifact_store_class.return_value = mock_store_instance

    # Mock session and agent
    mock_session_local.return_value = mock_session
    mock_run_agent = AsyncMock(return_value={"findings": "test"})

    with patch("app.workflows.tasks.runners.run_tech_comparator", mock_run_agent):
        result = await run_tech_comparator_with_session(
            test_content, test_content_type, mock_analysis_id, state
        )

    # Verify artifact store was attempted
    mock_artifact_store_class.assert_called_once_with(mock_session)
    mock_store_instance.load.assert_called_once()

    # Verify agent was called with fallback content after error
    assert mock_run_agent.call_count == 1
    call_args = mock_run_agent.call_args[0]
    assert call_args[0] == test_content  # Should fall back to original content
