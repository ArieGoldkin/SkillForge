"""Unit tests for tool-enabled agent factory (Issue #232).

This test suite follows TDD - tests are written before implementation.
The tests validate the new tool-enabled agent factory functions:
- ToolCallConfig dataclass
- _build_tool_enhanced_prompt() helper
- create_tool_enabled_agent() factory
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.domains.analysis.workflows.agents.base import (

    ToolCallConfig,
    _build_tool_enhanced_prompt,
    create_structured_agent,
    create_tool_enabled_agent,
)

# ============================================================================
# Test Schemas and Fixtures
# ============================================================================


class MockResponseSchema(BaseModel):
    """Mock Pydantic schema for agent response testing."""

    result: str
    confidence: float


@pytest.fixture
def mock_tools():
    """Create mock BaseTool objects for testing.

    Returns:
        List of two mock tools with names and descriptions.

    """
    tool1 = MagicMock(spec=BaseTool)
    tool1.name = "github_search_code"
    tool1.description = "Search GitHub repositories for code matching a query"

    tool2 = MagicMock(spec=BaseTool)
    tool2.name = "npm_get_package"
    tool2.description = "Get npm package metadata including versions and dependencies"

    return [tool1, tool2]


@pytest.fixture
def mock_response_schema():
    """Provide test Pydantic model for agent responses."""
    return MockResponseSchema


# ============================================================================
# TestToolCallConfig - Dataclass Configuration
# ============================================================================


class TestToolCallConfig:
    """Test ToolCallConfig dataclass for agent tool call configuration."""

    def test_config_defaults(self):
        """Verify default values: max_tool_calls=10, parallel_tool_calls=True."""
        config = ToolCallConfig()

        assert config.max_tool_calls == 10
        assert config.parallel_tool_calls is True

    def test_config_custom_max_calls(self):
        """Test custom max_tool_calls value."""
        config = ToolCallConfig(max_tool_calls=5)

        assert config.max_tool_calls == 5
        assert config.parallel_tool_calls is True  # Default still applies

    def test_config_disable_parallel(self):
        """Test parallel_tool_calls=False."""
        config = ToolCallConfig(parallel_tool_calls=False)

        assert config.max_tool_calls == 10  # Default still applies
        assert config.parallel_tool_calls is False

    def test_config_all_custom(self):
        """Test all custom values."""
        config = ToolCallConfig(max_tool_calls=3, parallel_tool_calls=False)

        assert config.max_tool_calls == 3
        assert config.parallel_tool_calls is False


# ============================================================================
# TestBuildToolEnhancedPrompt - Prompt Enhancement Helper
# ============================================================================


class TestBuildToolEnhancedPrompt:
    """Test _build_tool_enhanced_prompt helper function."""

    def test_includes_tool_descriptions(self, mock_tools):
        """Verify tool names and descriptions appear in output."""
        base_prompt = "You are a security analyst."
        max_tool_calls = 10

        result = _build_tool_enhanced_prompt(base_prompt, mock_tools, max_tool_calls)

        # Check tool names appear
        assert "github_search_code" in result
        assert "npm_get_package" in result

        # Check descriptions appear
        assert "Search GitHub repositories" in result
        assert "Get npm package metadata" in result

    def test_includes_max_calls_limit(self, mock_tools):
        """Verify max_tool_calls number appears in guidelines."""
        base_prompt = "You are a security analyst."
        max_tool_calls = 5

        result = _build_tool_enhanced_prompt(base_prompt, mock_tools, max_tool_calls)

        # Should mention the limit somewhere
        assert "5" in result or "five" in result.lower()

    def test_preserves_base_prompt(self, mock_tools):
        """Base prompt content is preserved at start."""
        base_prompt = "You are a security analyst with expertise in CVE detection."
        max_tool_calls = 10

        result = _build_tool_enhanced_prompt(base_prompt, mock_tools, max_tool_calls)

        # Original prompt should be at the start
        assert result.startswith(base_prompt) or base_prompt in result[:200]

    def test_empty_tools_returns_base_prompt(self):
        """Empty tools list returns base prompt unchanged."""
        base_prompt = "You are a security analyst."
        max_tool_calls = 10

        result = _build_tool_enhanced_prompt(base_prompt, [], max_tool_calls)

        # With no tools, should return base prompt unchanged
        assert result == base_prompt

    def test_includes_usage_guidelines(self, mock_tools):
        """Verify tool usage guidelines are included."""
        base_prompt = "You are a security analyst."
        max_tool_calls = 10

        result = _build_tool_enhanced_prompt(base_prompt, mock_tools, max_tool_calls)

        # Should have guidelines section
        assert "tool" in result.lower() or "available" in result.lower()
        assert "guidelines" in result.lower() or "usage" in result.lower()


# ============================================================================
# TestCreateToolEnabledAgent - Factory Function
# ============================================================================


class TestCreateToolEnabledAgent:
    """Test create_tool_enabled_agent factory function."""

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_returns_runnable(
        self,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Factory returns a Runnable instance."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model

        mock_agent = MagicMock(spec=Runnable)
        mock_create_agent.return_value = mock_agent

        # Call factory
        result = create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Verify result is the agent
        assert result is mock_agent
        # Verify create_agent was called
        mock_create_agent.assert_called_once()

    def test_raises_on_empty_tools(self, mock_response_schema):
        """Empty tools list raises ValueError."""
        with pytest.raises(ValueError, match=r"tools must not be empty.*create_structured_agent"):
            create_tool_enabled_agent(
                system_prompt="Test prompt",
                response_schema=mock_response_schema,
                tools=[],
            )

    def test_raises_on_none_tools(self, mock_response_schema):
        """None tools raises ValueError."""
        # Note: Sequence[BaseTool] type hint should prevent None, but test defensive code
        with pytest.raises(ValueError, match=r"tools must not be empty.*create_structured_agent"):
            create_tool_enabled_agent(
                system_prompt="Test prompt",
                response_schema=mock_response_schema,
                tools=None,  # type: ignore
            )

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_uses_default_config(
        self,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Default ToolCallConfig is used when not provided."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Call without config
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Verify bind_tools called with default parallel_tool_calls=True
        mock_model.bind_tools.assert_called_once()
        call_kwargs = mock_model.bind_tools.call_args.kwargs
        assert call_kwargs.get("parallel_tool_calls") is True

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_uses_custom_config(
        self,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Custom ToolCallConfig is respected."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Custom config
        custom_config = ToolCallConfig(max_tool_calls=3, parallel_tool_calls=False)

        # Call with custom config (note: parameter is tool_call_config)
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
            tool_call_config=custom_config,
        )

        # Verify bind_tools called with custom parallel_tool_calls=False
        mock_model.bind_tools.assert_called_once()
        call_kwargs = mock_model.bind_tools.call_args.kwargs
        assert call_kwargs.get("parallel_tool_calls") is False

    @patch("app.workflows.agents.base._build_tool_enhanced_prompt")
    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_enhances_prompt_with_tools(
        self,
        mock_get_model,
        mock_create_agent,
        mock_build_prompt,
        mock_tools,
        mock_response_schema,
    ):
        """System prompt is enhanced with tool information."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        original_prompt = "Test prompt"
        enhanced_prompt = "Enhanced prompt with tools"
        mock_build_prompt.return_value = enhanced_prompt

        # Call factory
        create_tool_enabled_agent(
            system_prompt=original_prompt,
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Verify prompt enhancement was called with correct parameters
        mock_build_prompt.assert_called_once()
        call_kwargs = mock_build_prompt.call_args.kwargs
        assert call_kwargs.get("base_prompt") == original_prompt
        assert call_kwargs.get("tools") == mock_tools
        assert call_kwargs.get("max_tool_calls") == 10  # Default

        # Verify enhanced prompt was passed to create_agent
        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args.kwargs
        assert call_kwargs.get("system_prompt") == enhanced_prompt

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    @patch("app.workflows.agents.base.logger")
    def test_logs_tool_creation(
        self,
        mock_logger,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Creating agent logs tool names and config."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Call factory
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Verify logging occurred
        assert mock_logger.info.called
        # Check log content
        log_call = mock_logger.info.call_args
        assert "creating_tool_enabled_agent" in log_call.args or log_call.kwargs

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_binds_tools_with_parallel_true(
        self,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Tools are bound with parallel_tool_calls=True by default."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Call with default config
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Verify bind_tools called with correct parameters
        mock_model.bind_tools.assert_called_once()
        call_args = mock_model.bind_tools.call_args
        # Tools should be passed as a list
        assert isinstance(call_args.args[0], list)
        assert call_args.kwargs.get("parallel_tool_calls") is True

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_binds_tools_with_parallel_false(
        self,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """When tool_call_config.parallel_tool_calls=False, tools bound accordingly."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Custom config with parallel=False
        custom_config = ToolCallConfig(parallel_tool_calls=False)

        # Call factory
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
            tool_call_config=custom_config,
        )

        # Verify bind_tools called with parallel_tool_calls=False
        mock_model.bind_tools.assert_called_once()
        call_args = mock_model.bind_tools.call_args
        assert call_args.kwargs.get("parallel_tool_calls") is False

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_passes_tools_to_create_agent(
        self,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Tools are passed to create_agent function."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Call factory
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Verify create_agent received tools
        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args.kwargs
        # Tools should be passed as list
        assert "tools" in call_kwargs
        tools_arg = call_kwargs["tools"]
        assert isinstance(tools_arg, list)

    @patch("app.workflows.agents.base._build_tool_enhanced_prompt")
    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_custom_max_tool_calls_passed_to_prompt_builder(
        self,
        mock_get_model,
        mock_create_agent,
        mock_build_prompt,
        mock_tools,
        mock_response_schema,
    ):
        """Custom max_tool_calls is passed to prompt enhancement."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)
        mock_build_prompt.return_value = "Enhanced prompt"

        # Custom config with different max_tool_calls
        custom_config = ToolCallConfig(max_tool_calls=7)

        # Call factory
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
            tool_call_config=custom_config,
        )

        # Verify prompt builder received custom max_tool_calls
        mock_build_prompt.assert_called_once()
        call_kwargs = mock_build_prompt.call_args.kwargs
        assert call_kwargs.get("max_tool_calls") == 7


# ============================================================================
# TestBackwardsCompatibility - Ensure Existing Code Works
# ============================================================================


class TestBackwardsCompatibility:
    """Test that existing create_structured_agent function remains unchanged."""

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_create_structured_agent_still_works(
        self,
        mock_get_model,
        mock_create_agent,
        mock_response_schema,
    ):
        """Existing create_structured_agent function unchanged."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Call existing function without tools
        result = create_structured_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # Should work and return agent
        assert result is not None
        mock_create_agent.assert_called_once()

        # Should bind with empty tools and parallel=False (existing behavior)
        mock_model.bind_tools.assert_called_once()
        call_args = mock_model.bind_tools.call_args
        assert call_args.args[0] == []  # Empty tools
        assert call_args.kwargs.get("parallel_tool_calls") is False

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_create_structured_agent_no_tools(
        self,
        mock_get_model,
        mock_create_agent,
        mock_response_schema,
    ):
        """create_structured_agent works with tools=None."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Call with tools=None (default)
        result = create_structured_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=None,
        )

        # Should work
        assert result is not None

    @patch("app.workflows.agents.base.create_agent")
    @patch("app.workflows.agents.base.get_chat_model")
    def test_tool_enabled_vs_structured_agent_differences(
        self,
        mock_get_model,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Verify key differences between tool-enabled and structured-only agents."""
        # Setup mocks
        mock_model = MagicMock()
        mock_bound_model = MagicMock()
        mock_model.bind_tools.return_value = mock_bound_model
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        # Call structured agent (no tools)
        create_structured_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # Should use parallel_tool_calls=False
        structured_call = mock_model.bind_tools.call_args
        assert structured_call.kwargs.get("parallel_tool_calls") is False

        # Reset mocks
        mock_model.bind_tools.reset_mock()

        # Call tool-enabled agent
        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Should use parallel_tool_calls=True (default)
        tool_enabled_call = mock_model.bind_tools.call_args
        assert tool_enabled_call.kwargs.get("parallel_tool_calls") is True
        # Should have non-empty tools
        assert len(tool_enabled_call.args[0]) > 0
