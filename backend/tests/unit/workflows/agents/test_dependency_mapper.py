"""Unit tests for dependency mapper agent."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflows.agents.dependency_mapper import run_dependency_mapper
from app.workflows.agents.schemas.dependency_mapper import Dependency, DependencyMapping


@pytest.fixture
def mock_agent():
    """Mock agent with structured response."""
    agent = MagicMock()
    agent.astream = None
    agent.ainvoke = AsyncMock(
        return_value={
            "structured_response": DependencyMapping(
                required_dependencies=[
                    Dependency(
                        name="react",
                        version="^18.0.0",
                        purpose="UI library",
                        compatibility="compatible",
                    )
                ],
                optional_dependencies=[
                    Dependency(
                        name="react-dom",
                        version="^18.0.0",
                        purpose="DOM rendering",
                        compatibility="compatible",
                    )
                ],
                version_conflicts=[],
                peer_dependencies=["Node.js >= 16.0.0"],
                installation_notes=["Install via npm: npm install react react-dom"],
                recommendation="Use npm or yarn for dependency management",
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
@patch("app.workflows.agents.dependency_mapper.create_structured_agent")
@patch("app.workflows.agents.dependency_mapper.run_agent_with_tracking")
async def test_run_dependency_mapper_success(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
):
    """Test successful dependency mapper execution."""
    analysis_id = str(uuid4())
    content = "This article discusses React dependencies and setup."
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.return_value = {
        "agent_type": "dependency_mapper",
        "findings": {
            "required_dependencies": [
                {
                    "name": "react",
                    "version": "^18.0.0",
                    "purpose": "UI library",
                    "compatibility": "compatible",
                }
            ],
            "optional_dependencies": [],
            "version_conflicts": [],
            "peer_dependencies": ["Node.js >= 16.0.0"],
            "installation_notes": ["Install via npm"],
            "recommendation": "Use npm for dependency management",
        },
        "processing_time_ms": 1100,
    }

    result = await run_dependency_mapper(content, content_type, analysis_id, mock_session)

    assert result["agent_type"] == "dependency_mapper"
    assert "findings" in result
    assert "required_dependencies" in result["findings"]
    assert result["processing_time_ms"] > 0
    mock_create_agent.assert_called_once()
    mock_run_tracking.assert_called_once()


@pytest.mark.asyncio
@patch("app.workflows.agents.dependency_mapper.create_structured_agent")
@patch("app.workflows.agents.dependency_mapper.run_agent_with_tracking")
async def test_run_dependency_mapper_error_handling(
    mock_run_tracking,
    mock_create_agent,
    mock_agent,
    mock_session,
):
    """Test dependency mapper error handling."""
    analysis_id = str(uuid4())
    content = "Test content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent
    mock_run_tracking.side_effect = RuntimeError("Agent execution failed")

    with pytest.raises(RuntimeError, match="Agent execution failed"):
        await run_dependency_mapper(content, content_type, analysis_id, mock_session)


@pytest.mark.asyncio
@patch("app.workflows.agents.dependency_mapper.create_structured_agent")
async def test_run_dependency_mapper_schema_validation(mock_create_agent, mock_agent, mock_session):
    """Test dependency mapper schema validation."""
    analysis_id = str(uuid4())
    content = "Dependency content"
    content_type = "article"

    mock_create_agent.return_value = mock_agent

    result = await run_dependency_mapper(content, content_type, analysis_id, mock_session)

    assert result is not None
    assert "agent_type" in result
