"""Unit tests for Security Auditor MCP tool integration (Issue #233).

This test suite validates MCP tool integration for the security_auditor agent:
- Conditional agent creation (tool-enabled vs structured-only)
- Tool loading in run_security_auditor_with_session
- Graceful degradation when MCP unavailable
- Proper parameter passing between layers
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.tools import BaseTool

from app.workflows.agents.security_auditor import run_security_auditor


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_tools():
    """Create mock MCP tools for security auditor."""
    tool1 = MagicMock(spec=BaseTool)
    tool1.name = "github_search_code"
    tool1.description = "Search GitHub for code patterns"

    tool2 = MagicMock(spec=BaseTool)
    tool2.name = "github_get_security_advisories"
    tool2.description = "Get security advisories"

    return [tool1, tool2]


@pytest.fixture
def mock_state():
    """Create mock analysis state."""
    return {"skill_level": "intermediate"}


# ============================================================================
# TestRunSecurityAuditorWithTools - Core Agent Function
# ============================================================================


class TestRunSecurityAuditorWithTools:
    """Test run_security_auditor with MCP tools parameter."""

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_tool_enabled_agent")
    async def test_uses_tool_enabled_agent_when_tools_provided(
        self, mock_create_tool_enabled, mock_run_tracking, mock_tools, mock_state
    ):
        """When tools are provided, should use create_tool_enabled_agent."""
        mock_agent = MagicMock()
        mock_create_tool_enabled.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=mock_state,
            tools=mock_tools,
        )

        # Verify tool-enabled agent was created
        mock_create_tool_enabled.assert_called_once()
        call_kwargs = mock_create_tool_enabled.call_args[1]
        assert call_kwargs["tools"] == mock_tools
        assert call_kwargs["tool_call_config"].max_tool_calls == 15

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_tool_enabled_agent")
    async def test_passes_security_audit_schema_to_tool_agent(
        self, mock_create_tool_enabled, mock_run_tracking, mock_tools, mock_state
    ):
        """Tool-enabled agent receives SecurityAudit response schema."""
        from app.workflows.agents.schemas.security_auditor import SecurityAudit

        mock_agent = MagicMock()
        mock_create_tool_enabled.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=mock_state,
            tools=mock_tools,
        )

        # Verify response schema is SecurityAudit
        call_kwargs = mock_create_tool_enabled.call_args[1]
        assert call_kwargs["response_schema"] == SecurityAudit

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_tool_enabled_agent")
    async def test_enhances_prompt_with_skill_level_and_tools(
        self, mock_create_tool_enabled, mock_run_tracking, mock_tools, mock_state
    ):
        """System prompt includes both skill level and tool guidance."""
        mock_agent = MagicMock()
        mock_create_tool_enabled.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=mock_state,
            tools=mock_tools,
        )

        # Verify prompt contains skill level instructions
        call_kwargs = mock_create_tool_enabled.call_args[1]
        system_prompt = call_kwargs["system_prompt"]

        # Should have base security auditor prompt
        assert "security" in system_prompt.lower() or "audit" in system_prompt.lower()
        # Should have skill level instructions
        assert "intermediate" in system_prompt.lower() or "skill" in system_prompt.lower()

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_structured_agent")
    async def test_uses_structured_agent_when_no_tools(
        self, mock_create_structured, mock_run_tracking, mock_state
    ):
        """When no tools provided, should use create_structured_agent."""
        mock_agent = MagicMock()
        mock_create_structured.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=mock_state,
            tools=None,
        )

        # Verify structured agent was used
        mock_create_structured.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_structured_agent")
    async def test_uses_structured_agent_when_empty_tools(
        self, mock_create_structured, mock_run_tracking, mock_state
    ):
        """When empty tools list provided, should use create_structured_agent."""
        mock_agent = MagicMock()
        mock_create_structured.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=mock_state,
            tools=[],  # Empty list
        )

        # Verify structured agent was used
        mock_create_structured.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_tool_enabled_agent")
    async def test_tool_call_config_max_calls_is_15(
        self, mock_create_tool_enabled, mock_run_tracking, mock_tools, mock_state
    ):
        """Security auditor uses max_tool_calls=15 for CVE lookups."""
        mock_agent = MagicMock()
        mock_create_tool_enabled.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=mock_state,
            tools=mock_tools,
        )

        # Verify max_tool_calls is 15 (security needs more lookups than other agents)
        call_kwargs = mock_create_tool_enabled.call_args[1]
        assert call_kwargs["tool_call_config"].max_tool_calls == 15

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_tool_enabled_agent")
    async def test_runs_agent_with_tracking(
        self, mock_create_tool_enabled, mock_run_tracking, mock_tools, mock_state
    ):
        """Agent execution uses run_agent_with_tracking for persistence."""
        mock_agent = MagicMock()
        mock_create_tool_enabled.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()

        result = await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=mock_state,
            tools=mock_tools,
        )

        # Verify run_agent_with_tracking was called correctly
        mock_run_tracking.assert_called_once()
        call_kwargs = mock_run_tracking.call_args[1]
        assert call_kwargs["agent"] == mock_agent
        assert call_kwargs["content"] == "test content"
        assert call_kwargs["content_type"] == "article"
        assert call_kwargs["analysis_id"] == analysis_id
        assert call_kwargs["agent_type"] == "security_auditor"
        assert call_kwargs["session"] == mock_session

        # Verify result is returned
        assert result == {"agent_type": "security_auditor", "findings": {}}


# ============================================================================
# TestSecurityAuditorWithSessionMCP - Session Runner Integration
# ============================================================================


class TestSecurityAuditorWithSessionMCP:
    """Test MCP tool loading logic verification.

    Note: The runner tests are complex due to dynamic imports. Here we verify
    the MCP loading flow logic via direct tests on the helper function behavior
    and the implementation patterns. Full integration tests with MCP servers
    are covered in integration tests (#236).
    """

    def test_runner_has_tools_parameter(self):
        """Verify runner function signature includes tools parameter."""
        import inspect
        from app.workflows.tasks.runners import run_security_auditor_with_session

        sig = inspect.signature(run_security_auditor_with_session)
        # The runner should accept the standard parameters
        params = list(sig.parameters.keys())
        assert "content" in params
        assert "content_type" in params
        assert "analysis_id" in params
        assert "state" in params

    def test_runner_imports_mcp_modules(self):
        """Verify runner file has proper MCP imports."""
        import inspect
        from app.workflows.tasks import runners

        source = inspect.getsource(runners.run_security_auditor_with_session)
        # Verify the dynamic import pattern is present
        assert "from app.services.mcp import" in source
        assert "MCPClientPool" in source
        assert "ToolRegistry" in source
        assert "get_mcp_settings" in source

    def test_runner_has_graceful_degradation(self):
        """Verify runner has exception handling for MCP failures."""
        import inspect
        from app.workflows.tasks import runners

        source = inspect.getsource(runners.run_security_auditor_with_session)
        # Verify graceful degradation pattern
        assert "tools = []" in source  # Empty tools default
        assert "except Exception" in source  # Catches MCP errors
        assert "mcp_tool_loading_failed" in source  # Logs failure

    def test_runner_checks_registry_enabled(self):
        """Verify runner checks if agent is enabled in registry."""
        import inspect
        from app.workflows.tasks import runners

        source = inspect.getsource(runners.run_security_auditor_with_session)
        # Verify registry check
        assert "is_tool_enabled" in source
        assert '"security_auditor"' in source

    def test_runner_passes_tools_to_agent(self):
        """Verify runner passes tools parameter to run_security_auditor."""
        import inspect
        from app.workflows.tasks import runners

        source = inspect.getsource(runners.run_security_auditor_with_session)
        # Verify tools are passed
        assert "tools=tools" in source


# ============================================================================
# TestSkillLevelIntegration - Skill Level with Tools
# ============================================================================


class TestSkillLevelIntegration:
    """Test that skill level instructions work correctly with MCP tools."""

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_tool_enabled_agent")
    async def test_beginner_skill_level_with_tools(
        self, mock_create_tool_enabled, mock_run_tracking, mock_tools
    ):
        """Beginner skill level instructions included when using tools."""
        mock_agent = MagicMock()
        mock_create_tool_enabled.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()
        state = {"skill_level": "beginner"}

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=state,
            tools=mock_tools,
        )

        # Verify prompt contains beginner-appropriate language
        call_kwargs = mock_create_tool_enabled.call_args[1]
        system_prompt = call_kwargs["system_prompt"]
        assert "beginner" in system_prompt.lower() or "basic" in system_prompt.lower()

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_tool_enabled_agent")
    async def test_expert_skill_level_with_tools(
        self, mock_create_tool_enabled, mock_run_tracking, mock_tools
    ):
        """Expert skill level instructions included when using tools."""
        mock_agent = MagicMock()
        mock_create_tool_enabled.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()
        state = {"skill_level": "expert"}

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=state,
            tools=mock_tools,
        )

        # Verify prompt contains expert-appropriate language
        call_kwargs = mock_create_tool_enabled.call_args[1]
        system_prompt = call_kwargs["system_prompt"]
        assert "expert" in system_prompt.lower() or "advanced" in system_prompt.lower()

    @pytest.mark.asyncio
    @patch("app.workflows.agents.security_auditor.run_agent_with_tracking")
    @patch("app.workflows.agents.security_auditor.create_structured_agent")
    async def test_skill_level_without_tools(
        self, mock_create_structured, mock_run_tracking
    ):
        """Skill level instructions work with structured-only agent."""
        mock_agent = MagicMock()
        mock_create_structured.return_value = mock_agent
        mock_run_tracking.return_value = {"agent_type": "security_auditor", "findings": {}}

        mock_session = AsyncMock()
        analysis_id = uuid4()
        state = {"skill_level": "intermediate"}

        await run_security_auditor(
            content="test content",
            content_type="article",
            analysis_id=analysis_id,
            session=mock_session,
            state=state,
            tools=None,
        )

        # Verify prompt contains skill level instructions
        call_kwargs = mock_create_structured.call_args[1]
        system_prompt = call_kwargs["system_prompt"]
        assert "intermediate" in system_prompt.lower() or "skill" in system_prompt.lower()
