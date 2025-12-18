"""Unit tests for agent invocation logic."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.workflows.agents.invocation import invoke_agent


class TestInvokeAgent:
    """Tests for invoke_agent function."""

    @pytest.fixture
    def mock_agent(self):
        """Create mock agent with ainvoke method."""
        agent = MagicMock()
        agent.ainvoke = AsyncMock(return_value={"findings": "test results"})
        return agent

    @pytest.fixture
    def mock_sync_agent(self):
        """Create mock agent with only sync invoke method."""
        agent = MagicMock()
        del agent.ainvoke  # Remove ainvoke to force sync path
        agent.invoke = MagicMock(return_value={"findings": "sync results"})
        return agent

    @pytest.fixture
    def input_messages(self):
        """Create sample input messages."""
        return {"messages": [{"role": "user", "content": "Analyze this code"}]}

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_ainvoke_success(self, mock_run_tree, mock_agent, input_messages):
        """Test successful async invocation."""
        mock_run_tree.return_value = None

        result = await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=uuid4(),
            agent_type="tech_comparator",
        )

        assert result == {"findings": "test results"}
        mock_agent.ainvoke.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_ainvoke_with_langsmith_trace(self, mock_run_tree, mock_agent, input_messages):
        """Test invocation captures LangSmith trace ID."""
        run_tree = MagicMock()
        run_tree.id = uuid4()
        mock_run_tree.return_value = run_tree

        result = await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=uuid4(),
            agent_type="tech_comparator",
        )

        assert "findings" in result

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_ainvoke_langsmith_unavailable(self, mock_run_tree, mock_agent, input_messages):
        """Test invocation continues when LangSmith is unavailable."""
        mock_run_tree.side_effect = Exception("LangSmith not available")

        result = await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=uuid4(),
            agent_type="tech_comparator",
        )

        assert result == {"findings": "test results"}

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_ainvoke_error_raises(self, mock_run_tree, mock_agent, input_messages):
        """Test that errors during ainvoke are propagated."""
        mock_run_tree.return_value = None
        mock_agent.ainvoke.side_effect = RuntimeError("Agent execution failed")

        with pytest.raises(RuntimeError, match="Agent execution failed"):
            await invoke_agent(
                agent=mock_agent,
                input_messages=input_messages,
                analysis_id=uuid4(),
                agent_type="tech_comparator",
            )

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_sync_invoke_fallback(self, mock_run_tree, mock_sync_agent, input_messages):
        """Test fallback to sync invoke when ainvoke not available."""
        mock_run_tree.return_value = None

        result = await invoke_agent(
            agent=mock_sync_agent,
            input_messages=input_messages,
            analysis_id=uuid4(),
            agent_type="tech_comparator",
        )

        assert result == {"findings": "sync results"}
        mock_sync_agent.invoke.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_sync_invoke_error_raises(self, mock_run_tree, mock_sync_agent, input_messages):
        """Test that errors during sync invoke are propagated."""
        mock_run_tree.return_value = None
        mock_sync_agent.invoke.side_effect = ValueError("Sync invoke failed")

        with pytest.raises(ValueError, match="Sync invoke failed"):
            await invoke_agent(
                agent=mock_sync_agent,
                input_messages=input_messages,
                analysis_id=uuid4(),
                agent_type="tech_comparator",
            )

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_custom_timeout_parameter(self, mock_run_tree, mock_agent, input_messages):
        """Test that custom timeout is accepted (for logging reference)."""
        mock_run_tree.return_value = None

        result = await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=uuid4(),
            agent_type="tech_comparator",
            timeout=120.0,
        )

        assert result == {"findings": "test results"}

    @pytest.mark.asyncio
    @patch("app.domains.analysis.workflows.agents.invocation.get_current_run_tree")
    async def test_langsmith_run_tree_without_id(self, mock_run_tree, mock_agent, input_messages):
        """Test handling of run tree without id attribute."""
        run_tree = MagicMock(spec=[])  # No id attribute
        mock_run_tree.return_value = run_tree

        result = await invoke_agent(
            agent=mock_agent,
            input_messages=input_messages,
            analysis_id=uuid4(),
            agent_type="tech_comparator",
        )

        assert result == {"findings": "test results"}
