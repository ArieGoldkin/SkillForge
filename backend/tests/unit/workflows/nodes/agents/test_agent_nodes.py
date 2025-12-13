"""Unit tests for agent node functions."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.workflows.nodes.agents.code_quality_critic_node import code_quality_critic_node
from app.workflows.nodes.agents.dependency_mapper_node import dependency_mapper_node
from app.workflows.nodes.agents.integration_feasibility_node import integration_feasibility_node
from app.workflows.nodes.agents.performance_analyst_node import performance_analyst_node


@pytest.fixture
def mock_state():
    """Create mock analysis state."""
    return {
        "analysis_id": uuid4(),
        "raw_content": "Test content for analysis",
        "content_type": "article",
    }


@pytest.fixture
def mock_run_tree():
    """Create mock LangSmith run tree."""
    tree = MagicMock()
    tree.id = uuid4()
    tree.metadata = {}
    tree.tags = []
    return tree


@pytest.fixture
def mock_agent_result():
    """Create mock agent result."""
    return {
        "findings": {"key": "value"},
        "confidence_score": 0.85,
    }


class TestCodeQualityCriticNode:
    """Tests for code_quality_critic_node."""

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.code_quality_critic_node.run_code_quality_critic_with_session"
    )
    @patch("app.workflows.nodes.agents.code_quality_critic_node.get_current_run_tree")
    async def test_successful_execution(
        self, mock_get_tree, mock_runner, mock_state, mock_run_tree, mock_agent_result
    ):
        """Test successful agent execution."""
        mock_get_tree.return_value = mock_run_tree
        mock_runner.return_value = mock_agent_result

        result = await code_quality_critic_node(mock_state)

        assert "agent_findings" in result
        assert result["agent_findings"] == [mock_agent_result]
        mock_runner.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.code_quality_critic_node.run_code_quality_critic_with_session"
    )
    @patch("app.workflows.nodes.agents.code_quality_critic_node.get_current_run_tree")
    async def test_handles_generator_exit(self, mock_get_tree, mock_runner, mock_state):
        """Test graceful handling of GeneratorExit (cancellation)."""
        mock_get_tree.return_value = None
        mock_runner.side_effect = GeneratorExit()

        result = await code_quality_critic_node(mock_state)

        assert result == {"agent_findings": []}

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.code_quality_critic_node.run_code_quality_critic_with_session"
    )
    @patch("app.workflows.nodes.agents.code_quality_critic_node.get_current_run_tree")
    async def test_handles_exception(self, mock_get_tree, mock_runner, mock_state):
        """Test graceful handling of exceptions."""
        mock_get_tree.return_value = None
        mock_runner.side_effect = RuntimeError("Agent failed")

        result = await code_quality_critic_node(mock_state)

        assert result == {"agent_findings": []}

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.code_quality_critic_node.run_code_quality_critic_with_session"
    )
    @patch("app.workflows.nodes.agents.code_quality_critic_node.get_current_run_tree")
    async def test_without_langsmith(
        self, mock_get_tree, mock_runner, mock_state, mock_agent_result
    ):
        """Test execution without LangSmith available."""
        mock_get_tree.side_effect = Exception("LangSmith not available")
        mock_runner.return_value = mock_agent_result

        result = await code_quality_critic_node(mock_state)

        assert "agent_findings" in result


class TestDependencyMapperNode:
    """Tests for dependency_mapper_node."""

    @pytest.mark.asyncio
    @patch("app.workflows.nodes.agents.dependency_mapper_node.run_dependency_mapper_with_session")
    @patch("app.workflows.nodes.agents.dependency_mapper_node.get_current_run_tree")
    async def test_successful_execution(
        self, mock_get_tree, mock_runner, mock_state, mock_run_tree, mock_agent_result
    ):
        """Test successful agent execution."""
        mock_get_tree.return_value = mock_run_tree
        mock_runner.return_value = mock_agent_result

        result = await dependency_mapper_node(mock_state)

        assert "agent_findings" in result
        assert result["agent_findings"] == [mock_agent_result]

    @pytest.mark.asyncio
    @patch("app.workflows.nodes.agents.dependency_mapper_node.run_dependency_mapper_with_session")
    @patch("app.workflows.nodes.agents.dependency_mapper_node.get_current_run_tree")
    async def test_handles_exception(self, mock_get_tree, mock_runner, mock_state):
        """Test graceful handling of exceptions."""
        mock_get_tree.return_value = None
        mock_runner.side_effect = RuntimeError("Agent failed")

        result = await dependency_mapper_node(mock_state)

        assert result == {"agent_findings": []}


class TestIntegrationFeasibilityNode:
    """Tests for integration_feasibility_node."""

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.integration_feasibility_node.run_integration_feasibility_with_session"
    )
    @patch("app.workflows.nodes.agents.integration_feasibility_node.get_current_run_tree")
    async def test_successful_execution(
        self, mock_get_tree, mock_runner, mock_state, mock_run_tree, mock_agent_result
    ):
        """Test successful agent execution."""
        mock_get_tree.return_value = mock_run_tree
        mock_runner.return_value = mock_agent_result

        result = await integration_feasibility_node(mock_state)

        assert "agent_findings" in result
        assert result["agent_findings"] == [mock_agent_result]

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.integration_feasibility_node.run_integration_feasibility_with_session"
    )
    @patch("app.workflows.nodes.agents.integration_feasibility_node.get_current_run_tree")
    async def test_handles_generator_exit(self, mock_get_tree, mock_runner, mock_state):
        """Test graceful handling of cancellation."""
        mock_get_tree.return_value = None
        mock_runner.side_effect = GeneratorExit()

        result = await integration_feasibility_node(mock_state)

        assert result == {"agent_findings": []}


class TestPerformanceAnalystNode:
    """Tests for performance_analyst_node."""

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.performance_analyst_node.run_performance_analyst_with_session"
    )
    @patch("app.workflows.nodes.agents.performance_analyst_node.get_current_run_tree")
    async def test_successful_execution(
        self, mock_get_tree, mock_runner, mock_state, mock_run_tree, mock_agent_result
    ):
        """Test successful agent execution."""
        mock_get_tree.return_value = mock_run_tree
        mock_runner.return_value = mock_agent_result

        result = await performance_analyst_node(mock_state)

        assert "agent_findings" in result
        assert result["agent_findings"] == [mock_agent_result]

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.performance_analyst_node.run_performance_analyst_with_session"
    )
    @patch("app.workflows.nodes.agents.performance_analyst_node.get_current_run_tree")
    async def test_handles_exception(self, mock_get_tree, mock_runner, mock_state):
        """Test graceful handling of exceptions."""
        mock_get_tree.return_value = None
        mock_runner.side_effect = RuntimeError("Agent failed")

        result = await performance_analyst_node(mock_state)

        assert result == {"agent_findings": []}

    @pytest.mark.asyncio
    @patch(
        "app.workflows.nodes.agents.performance_analyst_node.run_performance_analyst_with_session"
    )
    @patch("app.workflows.nodes.agents.performance_analyst_node.get_current_run_tree")
    async def test_updates_langsmith_metadata(
        self, mock_get_tree, mock_runner, mock_state, mock_run_tree, mock_agent_result
    ):
        """Test that LangSmith metadata is updated."""
        mock_get_tree.return_value = mock_run_tree
        mock_runner.return_value = mock_agent_result

        await performance_analyst_node(mock_state)

        assert "analysis_id" in mock_run_tree.metadata
        assert "parallel-execution" in mock_run_tree.tags
