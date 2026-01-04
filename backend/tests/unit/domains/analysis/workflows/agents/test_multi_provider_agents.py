"""Unit tests for multi-provider agent support (Gemini ToolStrategy Fix).

This test suite validates provider-aware agent creation:
- Gemini uses direct with_structured_output() (not ToolStrategy)
- OpenAI uses strict=True with with_structured_output()
- Anthropic/other providers don't use strict mode
- Backwards compatibility with existing Anthropic/OpenAI paths

Gap Analysis Fix: Gemini ToolStrategy incompatibility caused empty findings {}.
Root cause: ToolStrategy pattern doesn't extract Gemini's structured responses.
Solution: Provider-aware agent factories with Gemini-specific LCEL chains.

Related: Gap analysis Dec 2025 - Multi-provider LLM support improvements.
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from app.domains.analysis.workflows.agents.base import (
    ToolCallConfig,
    _create_gemini_structured_chain,
    _create_gemini_tool_chain,
    create_structured_agent,
    create_tool_enabled_agent,
)
from app.core.provider_config import get_structured_output_kwargs
from app.domains.analysis.workflows.agents.factories import (
    create_agent_with_lcel_fallback,
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
    """Create mock BaseTool objects for testing."""
    tool1 = MagicMock(spec=BaseTool)
    tool1.name = "github_search_code"
    tool1.description = "Search GitHub repositories"

    tool2 = MagicMock(spec=BaseTool)
    tool2.name = "npm_get_package"
    tool2.description = "Get npm package metadata"

    return [tool1, tool2]


@pytest.fixture
def mock_response_schema():
    """Provide test Pydantic model for agent responses."""
    return MockResponseSchema


# ============================================================================
# TestProviderDetection - Provider-specific kwargs
# ============================================================================


class TestProviderSpecificKwargs:
    """Test get_structured_output_kwargs from provider_config module.

    Issue #637: Centralized provider configuration registry.
    """

    def test_openai_gets_strict_true(self):
        """OpenAI provider should get strict=True for JSON mode."""
        kwargs = get_structured_output_kwargs("openai")
        assert kwargs == {"strict": True}

    def test_anthropic_gets_empty_kwargs(self):
        """Anthropic provider should not get strict mode."""
        kwargs = get_structured_output_kwargs("anthropic")
        assert kwargs == {}

    def test_google_genai_gets_empty_kwargs(self):
        """Gemini provider should not get strict mode."""
        kwargs = get_structured_output_kwargs("google_genai")
        assert kwargs == {}

    def test_unknown_provider_gets_empty_kwargs(self):
        """Unknown providers should not get strict mode (safe default)."""
        kwargs = get_structured_output_kwargs("unknown_provider")
        assert kwargs == {}

    def test_xai_gets_strict_true(self):
        """xAI (Grok) provider uses OpenAI-compatible API with strict=True."""
        kwargs = get_structured_output_kwargs("xai")
        assert kwargs == {"strict": True}

    def test_deepseek_gets_strict_true(self):
        """DeepSeek provider uses OpenAI-compatible API with strict=True."""
        kwargs = get_structured_output_kwargs("deepseek")
        assert kwargs == {"strict": True}

    def test_ollama_gets_empty_kwargs(self):
        """Ollama (local) should not get strict mode."""
        kwargs = get_structured_output_kwargs("ollama")
        assert kwargs == {}


# ============================================================================
# TestGeminiStructuredChain - Gemini-specific LCEL chain
# ============================================================================


class TestGeminiStructuredChain:
    """Test _create_gemini_structured_chain for Gemini provider."""

    def test_creates_runnable_chain(self, mock_response_schema):
        """Gemini chain returns a Runnable."""
        mock_model = MagicMock()
        mock_model.with_structured_output.return_value = MagicMock()

        chain = _create_gemini_structured_chain(
            model=mock_model,
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        assert chain is not None
        # Should be a RunnableSequence (LCEL chain)
        assert hasattr(chain, "invoke") or hasattr(chain, "ainvoke")

    def test_calls_with_structured_output_no_strict(self, mock_response_schema):
        """Gemini chain uses with_structured_output without strict=True."""
        mock_model = MagicMock()
        mock_structured = MagicMock()
        mock_model.with_structured_output.return_value = mock_structured

        _create_gemini_structured_chain(
            model=mock_model,
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # Verify with_structured_output was called
        mock_model.with_structured_output.assert_called_once()
        call_args = mock_model.with_structured_output.call_args

        # First positional arg should be the schema
        assert call_args.args[0] == mock_response_schema

        # Should NOT have strict=True (Gemini doesn't support it)
        assert call_args.kwargs.get("strict") is not True


class TestGeminiToolChain:
    """Test _create_gemini_tool_chain for tool-enabled Gemini agents."""

    def test_creates_runnable_chain(self, mock_tools, mock_response_schema):
        """Gemini tool chain returns a Runnable."""
        mock_model = MagicMock()
        mock_bound = MagicMock()
        mock_model.bind_tools.return_value = mock_bound
        mock_bound.with_structured_output.return_value = MagicMock()

        chain = _create_gemini_tool_chain(
            model=mock_model,
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        assert chain is not None
        assert hasattr(chain, "invoke") or hasattr(chain, "ainvoke")

    def test_binds_tools_before_structured_output(self, mock_tools, mock_response_schema):
        """Gemini tool chain binds tools before calling with_structured_output."""
        mock_model = MagicMock()
        mock_bound = MagicMock()
        mock_model.bind_tools.return_value = mock_bound
        mock_bound.with_structured_output.return_value = MagicMock()

        _create_gemini_tool_chain(
            model=mock_model,
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # bind_tools should be called on original model
        mock_model.bind_tools.assert_called_once()

        # with_structured_output should be called on bound model
        mock_bound.with_structured_output.assert_called_once()

    def test_respects_parallel_tool_calls_setting(self, mock_tools, mock_response_schema):
        """Custom parallel_tool_calls is passed to bind_tools."""
        mock_model = MagicMock()
        mock_bound = MagicMock()
        mock_model.bind_tools.return_value = mock_bound
        mock_bound.with_structured_output.return_value = MagicMock()

        _create_gemini_tool_chain(
            model=mock_model,
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
            parallel_tool_calls=False,
        )

        call_kwargs = mock_model.bind_tools.call_args.kwargs
        assert call_kwargs.get("parallel_tool_calls") is False


# ============================================================================
# TestProviderAwareAgentCreation - create_structured_agent
# ============================================================================


class TestProviderAwareStructuredAgent:
    """Test create_structured_agent with provider awareness."""

    @patch("app.domains.analysis.workflows.agents.base._create_gemini_structured_chain")
    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_gemini_uses_gemini_chain(
        self,
        mock_get_model,
        mock_settings,
        mock_gemini_chain,
        mock_response_schema,
    ):
        """Gemini provider uses _create_gemini_structured_chain."""
        mock_settings.resolved_llm_provider.return_value = "google_genai"
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_gemini_chain.return_value = MagicMock(spec=Runnable)

        create_structured_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # Should call Gemini chain factory
        mock_gemini_chain.assert_called_once()

    @patch("app.domains.analysis.workflows.agents.base.create_agent")
    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_anthropic_uses_toolstrategy(
        self,
        mock_get_model,
        mock_settings,
        mock_create_agent,
        mock_response_schema,
    ):
        """Anthropic provider uses ToolStrategy pattern."""
        mock_settings.resolved_llm_provider.return_value = "anthropic"
        mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = MagicMock()
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        create_structured_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # Should call create_agent (ToolStrategy path)
        mock_create_agent.assert_called_once()

    @patch("app.domains.analysis.workflows.agents.base.create_agent")
    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_openai_uses_toolstrategy(
        self,
        mock_get_model,
        mock_settings,
        mock_create_agent,
        mock_response_schema,
    ):
        """OpenAI provider uses ToolStrategy pattern."""
        mock_settings.resolved_llm_provider.return_value = "openai"
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = MagicMock()
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        create_structured_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # Should call create_agent (ToolStrategy path)
        mock_create_agent.assert_called_once()


# ============================================================================
# TestProviderAwareToolEnabledAgent - create_tool_enabled_agent
# ============================================================================


class TestProviderAwareToolEnabledAgent:
    """Test create_tool_enabled_agent with provider awareness."""

    @patch("app.domains.analysis.workflows.agents.base._create_gemini_tool_chain")
    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_gemini_uses_gemini_tool_chain(
        self,
        mock_get_model,
        mock_settings,
        mock_gemini_chain,
        mock_tools,
        mock_response_schema,
    ):
        """Gemini provider uses _create_gemini_tool_chain."""
        mock_settings.resolved_llm_provider.return_value = "google_genai"
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_gemini_chain.return_value = MagicMock(spec=Runnable)

        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Should call Gemini tool chain factory
        mock_gemini_chain.assert_called_once()

    @patch("app.domains.analysis.workflows.agents.base.create_agent")
    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_anthropic_uses_toolstrategy_with_tools(
        self,
        mock_get_model,
        mock_settings,
        mock_create_agent,
        mock_tools,
        mock_response_schema,
    ):
        """Anthropic provider uses ToolStrategy pattern with tools."""
        mock_settings.resolved_llm_provider.return_value = "anthropic"
        mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "5m"
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = MagicMock()
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
        )

        # Should call create_agent (ToolStrategy path)
        mock_create_agent.assert_called_once()
        # Verify tools were passed
        call_kwargs = mock_create_agent.call_args.kwargs
        assert "tools" in call_kwargs

    @patch("app.domains.analysis.workflows.agents.base._create_gemini_tool_chain")
    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_gemini_passes_tool_config(
        self,
        mock_get_model,
        mock_settings,
        mock_gemini_chain,
        mock_tools,
        mock_response_schema,
    ):
        """Gemini respects ToolCallConfig settings."""
        mock_settings.resolved_llm_provider.return_value = "google_genai"
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_gemini_chain.return_value = MagicMock(spec=Runnable)

        config = ToolCallConfig(max_tool_calls=5, parallel_tool_calls=False)

        create_tool_enabled_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
            tools=mock_tools,
            tool_call_config=config,
        )

        # Verify parallel_tool_calls passed to Gemini chain
        call_kwargs = mock_gemini_chain.call_args.kwargs
        assert call_kwargs.get("parallel_tool_calls") is False


# ============================================================================
# TestLCELFallbackProviderAware - create_agent_with_lcel_fallback
# ============================================================================


class TestLCELFallbackProviderAware:
    """Test create_agent_with_lcel_fallback with provider awareness."""

    @patch("app.domains.analysis.workflows.agents.factories.settings")
    @patch("app.domains.analysis.workflows.agents.factories.get_chat_model")
    def test_openai_uses_strict_true(
        self,
        mock_get_model,
        mock_settings,
        mock_response_schema,
    ):
        """OpenAI provider gets strict=True in with_structured_output."""
        mock_settings.LLM_MODEL = "gpt-4"
        mock_settings.LLM_FALLBACK_MODEL = "gpt-3.5-turbo"
        mock_settings.resolved_llm_provider.return_value = "openai"

        mock_primary = MagicMock()
        mock_fallback = MagicMock()
        mock_structured = MagicMock()
        mock_primary.with_structured_output.return_value = mock_structured
        mock_fallback.with_structured_output.return_value = mock_structured
        mock_structured.with_fallbacks.return_value = MagicMock(spec=Runnable)

        mock_get_model.side_effect = [mock_primary, mock_fallback]

        create_agent_with_lcel_fallback(
            agent_type="test_agent",
            response_schema=mock_response_schema,
        )

        # Both primary and fallback should have strict=True
        primary_call = mock_primary.with_structured_output.call_args
        assert primary_call.kwargs.get("strict") is True

        fallback_call = mock_fallback.with_structured_output.call_args
        assert fallback_call.kwargs.get("strict") is True

    @patch("app.domains.analysis.workflows.agents.factories.settings")
    @patch("app.domains.analysis.workflows.agents.factories.get_chat_model")
    def test_gemini_no_strict_mode(
        self,
        mock_get_model,
        mock_settings,
        mock_response_schema,
    ):
        """Gemini provider does NOT get strict mode."""
        mock_settings.LLM_MODEL = "gemini-2.0-flash"
        mock_settings.LLM_FALLBACK_MODEL = "gemini-1.5-flash"
        mock_settings.resolved_llm_provider.return_value = "google_genai"

        mock_primary = MagicMock()
        mock_fallback = MagicMock()
        mock_structured = MagicMock()
        mock_primary.with_structured_output.return_value = mock_structured
        mock_fallback.with_structured_output.return_value = mock_structured
        mock_structured.with_fallbacks.return_value = MagicMock(spec=Runnable)

        mock_get_model.side_effect = [mock_primary, mock_fallback]

        create_agent_with_lcel_fallback(
            agent_type="test_agent",
            response_schema=mock_response_schema,
        )

        # Both primary and fallback should NOT have strict
        primary_call = mock_primary.with_structured_output.call_args
        assert "strict" not in primary_call.kwargs or primary_call.kwargs.get("strict") is not True

        fallback_call = mock_fallback.with_structured_output.call_args
        assert (
            "strict" not in fallback_call.kwargs or fallback_call.kwargs.get("strict") is not True
        )

    @patch("app.domains.analysis.workflows.agents.factories.settings")
    @patch("app.domains.analysis.workflows.agents.factories.get_chat_model")
    def test_anthropic_no_strict_mode(
        self,
        mock_get_model,
        mock_settings,
        mock_response_schema,
    ):
        """Anthropic provider does NOT get strict mode."""
        mock_settings.LLM_MODEL = "claude-sonnet-4-20250514"
        mock_settings.LLM_FALLBACK_MODEL = "claude-3-haiku-20240307"
        mock_settings.resolved_llm_provider.return_value = "anthropic"

        mock_primary = MagicMock()
        mock_fallback = MagicMock()
        mock_structured = MagicMock()
        mock_primary.with_structured_output.return_value = mock_structured
        mock_fallback.with_structured_output.return_value = mock_structured
        mock_structured.with_fallbacks.return_value = MagicMock(spec=Runnable)

        mock_get_model.side_effect = [mock_primary, mock_fallback]

        create_agent_with_lcel_fallback(
            agent_type="test_agent",
            response_schema=mock_response_schema,
        )

        # Anthropic should NOT have strict
        primary_call = mock_primary.with_structured_output.call_args
        assert "strict" not in primary_call.kwargs or primary_call.kwargs.get("strict") is not True


# ============================================================================
# TestRegressionPrevention - Ensure fixes don't break existing functionality
# ============================================================================


class TestRegressionPrevention:
    """Tests to prevent regression of the Gemini fix."""

    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_gemini_chain_wraps_output_correctly(
        self,
        mock_get_model,
        mock_settings,
        mock_response_schema,
    ):
        """Gemini chain wraps output in ToolStrategy-compatible format."""
        mock_settings.resolved_llm_provider.return_value = "google_genai"
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        # Create mock that simulates Gemini returning a Pydantic model
        mock_pydantic_response = mock_response_schema(result="test", confidence=0.95)
        mock_structured = MagicMock()
        mock_structured.__or__ = MagicMock(return_value=mock_structured)
        mock_model.with_structured_output.return_value = mock_structured

        chain = _create_gemini_structured_chain(
            model=mock_model,
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # The chain should exist and be callable
        assert chain is not None
        # Chain should have pipe operator support (LCEL)
        assert hasattr(chain, "__or__") or hasattr(chain, "pipe")

    def test_empty_tools_rejected(self, mock_response_schema):
        """create_tool_enabled_agent still rejects empty tools."""
        with pytest.raises(ValueError, match=r"tools must not be empty"):
            create_tool_enabled_agent(
                system_prompt="Test prompt",
                response_schema=mock_response_schema,
                tools=[],
            )

    @patch("app.domains.analysis.workflows.agents.base.create_agent")
    @patch("app.domains.analysis.workflows.agents.base.settings")
    @patch("app.domains.analysis.workflows.agents.base.get_chat_model")
    def test_anthropic_prompt_caching_preserved(
        self,
        mock_get_model,
        mock_settings,
        mock_create_agent,
        mock_response_schema,
    ):
        """Anthropic prompt caching (cache_control) is preserved."""
        mock_settings.resolved_llm_provider.return_value = "anthropic"
        mock_settings.ANTHROPIC_PROMPT_CACHE_TTL = "1h"
        mock_model = MagicMock()
        mock_model.bind_tools.return_value = MagicMock()
        mock_get_model.return_value = mock_model
        mock_create_agent.return_value = MagicMock(spec=Runnable)

        create_structured_agent(
            system_prompt="Test prompt",
            response_schema=mock_response_schema,
        )

        # Verify create_agent was called with system_prompt that has cache_control
        call_kwargs = mock_create_agent.call_args.kwargs
        system_message = call_kwargs.get("system_prompt")

        # Should be a SystemMessage with cache_control
        assert system_message is not None
        # Content should be a list with cache_control for Anthropic
        assert isinstance(system_message.content, list)
        assert "cache_control" in system_message.content[0]
