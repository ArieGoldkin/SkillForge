"""Unit tests for supervisor agent selection (Issue #299-304).

Tests verify:
1. Supervisor ALWAYS selects at least 3 agents for any content
2. Content signal-based filtering works correctly
3. Auto-activation and minimum enforcement interact properly
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.nodes.supervisor import supervisor_route
from app.domains.analysis.workflows.nodes.supervisor_config import build_supervisor_prompt
from app.domains.analysis.workflows.nodes.supervisor_schema import AgentSelection


@pytest.mark.unit

# Helper to disable signal-based skipping for isolated enforcement tests
def mock_no_skip(agent_name, signals):
    """Mock should_skip_agent to never skip - isolates enforcement testing."""
    return False, None


class TestSupervisorMinimumAgentEnforcement:
    """Tests for minimum agent count enforcement (Issue #299-304).

    Note: These tests mock should_skip_agent to disable content signal filtering,
    allowing isolated testing of the minimum 3-agent enforcement logic.
    """

    @pytest.mark.asyncio
    async def test_minimum_3_agents_enforced_for_simple_content(self):
        """Verify at least 3 agents are selected even for simple content.

        This test ensures the supervisor NEVER selects fewer than 3 agents,
        which was causing poor artifact quality (12% coverage instead of 70%+).
        """
        # Mock LLM to return 3 agents (meets minimum)
        mock_selection = AgentSelection(
            agents=["implementation_planner", "security_auditor", "performance_analyst"],
            reasoning="Simple content needs basic implementation guidance",
            confidence=0.7,
        )

        mock_structured_model = MagicMock()
        mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

        # Mock filter_agents_by_content_type to simulate filtering down to 1 agent
        def mock_filter(agents, content_type):
            return ["implementation_planner"], ["security_auditor", "performance_analyst"]

        with (
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
                return_value=mock_model,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.filter_agents_by_content_type",
                side_effect=mock_filter,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_skip,
            ),
        ):
            result = await supervisor_route(
                content="Simple one-line tip: use async functions for better performance.",
                content_type="article",
                analysis_id="test-123",
            )

            decision = result["supervisor_decision"]
            # CRITICAL: Must have at least 3 agents (enforcement kicked in)
            assert len(decision["agents"]) >= 3, (
                f"Expected at least 3 agents, got {len(decision['agents'])}: {decision['agents']}"
            )
            # Original agent should still be included
            assert "implementation_planner" in decision["agents"]

    @pytest.mark.asyncio
    async def test_minimum_3_agents_enforced_for_two_agent_selection(self):
        """Verify enforcement works when filtering reduces to 2 agents."""
        mock_selection = AgentSelection(
            agents=["implementation_planner", "security_auditor", "performance_analyst"],
            reasoning="Quick security tip",
            confidence=0.8,
        )

        mock_structured_model = MagicMock()
        mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

        # Mock filter to simulate filtering down to 2 agents
        def mock_filter(agents, content_type):
            return ["implementation_planner", "security_auditor"], ["performance_analyst"]

        with (
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
                return_value=mock_model,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.filter_agents_by_content_type",
                side_effect=mock_filter,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_skip,
            ),
        ):
            result = await supervisor_route(
                content="Quick tip: always hash passwords with bcrypt.",
                content_type="article",
                analysis_id="test-456",
            )

            decision = result["supervisor_decision"]
            # Should have at least 3 agents (2 filtered + 1 default added)
            assert len(decision["agents"]) >= 3
            # Original filtered agents should be preserved
            assert "implementation_planner" in decision["agents"]
            assert "security_auditor" in decision["agents"]

    @pytest.mark.asyncio
    async def test_no_enforcement_when_3_or_more_agents_selected(self):
        """Verify enforcement doesn't add agents when 3+ already selected."""
        mock_selection = AgentSelection(
            agents=["implementation_planner", "security_auditor", "performance_analyst"],
            reasoning="Tutorial needs multiple perspectives",
            confidence=0.85,
        )

        mock_structured_model = MagicMock()
        mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

        # Mock filter to keep all 3 agents (no filtering)
        def mock_filter(agents, content_type):
            return agents, []

        with (
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
                return_value=mock_model,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.filter_agents_by_content_type",
                side_effect=mock_filter,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_skip,
            ),
        ):
            result = await supervisor_route(
                content="Tutorial on building secure, performant APIs.",
                content_type="article",
                analysis_id="test-789",
            )

            decision = result["supervisor_decision"]
            # Should have at least 3 agents
            assert len(decision["agents"]) >= 3
            # All original agents should be present
            assert "implementation_planner" in decision["agents"]
            assert "security_auditor" in decision["agents"]
            assert "performance_analyst" in decision["agents"]

    @pytest.mark.asyncio
    async def test_enforcement_adds_default_agents_in_order(self):
        """Verify that default agents are added in the correct priority order."""
        mock_selection = AgentSelection(
            agents=[
                "implementation_planner",
                "security_auditor",
                "performance_analyst",
            ],
            reasoning="Content analysis",
            confidence=0.9,
        )

        mock_structured_model = MagicMock()
        mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

        # Mock filter to simulate all agents being filtered out
        def mock_filter(agents, content_type):
            return [], agents

        with (
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
                return_value=mock_model,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.filter_agents_by_content_type",
                side_effect=mock_filter,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_skip,
            ),
        ):
            result = await supervisor_route(
                content="Article about video processing.",
                content_type="article",
                analysis_id="test-edge",
            )

            decision = result["supervisor_decision"]
            # Should have at least 3 default agents
            assert len(decision["agents"]) >= 3
            # Should include the default agents
            default_agents = ["implementation_planner", "dependency_mapper", "trend_validator"]
            assert any(agent in decision["agents"] for agent in default_agents)

    @pytest.mark.asyncio
    async def test_enforcement_with_auto_activation_combined(self):
        """Verify minimum enforcement works with auto-activation logic."""
        mock_selection = AgentSelection(
            agents=["implementation_planner", "security_auditor", "performance_analyst"],
            reasoning="Simple tutorial",
            confidence=0.7,
        )

        mock_structured_model = MagicMock()
        mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection)
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

        # Content with code patterns (has imports + framework = code detected)
        content_with_imports = """
        import fastapi
        from fastapi import FastAPI

        def create_app():
            app = FastAPI()
            return app
        """

        with (
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
                return_value=mock_model,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_skip,
            ),
        ):
            result = await supervisor_route(
                content=content_with_imports,
                content_type="code",
                analysis_id="test-combined",
            )

            decision = result["supervisor_decision"]
            # Should have at least 3 agents
            assert len(decision["agents"]) >= 3
            # Should include implementation_planner
            assert "implementation_planner" in decision["agents"]
            # dependency_mapper should be auto-activated due to imports
            assert "dependency_mapper" in decision["agents"]

    @pytest.mark.asyncio
    async def test_prompt_enforces_minimum_in_guidelines(self):
        """Verify supervisor prompt explicitly states minimum 3 agents requirement."""
        prompt = build_supervisor_prompt()

        # Should contain the minimum requirement
        assert "MINIMUM 3 AGENTS" in prompt
        assert "3-4 agents" in prompt  # For SHORT content
        assert "Never select fewer than 3 agents" in prompt

        # Should NOT contain old 1-2 agent guidance
        assert "1-2 agents" not in prompt

    @pytest.mark.asyncio
    async def test_prompt_has_no_single_agent_examples(self):
        """Verify supervisor prompt doesn't show 1-agent examples."""
        prompt = build_supervisor_prompt()

        # Should NOT contain examples with just 1 agent
        # Old example was: {"agents": ["implementation_planner"], ...}
        assert '"agents": ["implementation_planner"],' not in prompt

        # All examples should have at least 3 agents
        # Check for the updated simple example
        assert "dependency_mapper" in prompt
        assert "security_auditor" in prompt

    @pytest.mark.asyncio
    async def test_schema_enforces_minimum_3_agents(self):
        """Verify AgentSelection schema requires min_length=3."""
        # Try to create an AgentSelection with fewer than 3 agents
        # This should fail validation
        with pytest.raises(ValueError, match="at least 3"):
            AgentSelection(
                agents=["implementation_planner"],
                reasoning="Test",
                confidence=0.8,
            )

    @pytest.mark.asyncio
    async def test_schema_allows_3_to_8_agents(self):
        """Verify AgentSelection schema allows 3-8 agents."""
        # 3 agents (minimum) - should work
        selection_3 = AgentSelection(
            agents=["implementation_planner", "security_auditor", "dependency_mapper"],
            reasoning="Test",
            confidence=0.8,
        )
        assert len(selection_3.agents) == 3

        # 8 agents (maximum) - should work
        selection_8 = AgentSelection(
            agents=[
                "implementation_planner",
                "security_auditor",
                "performance_analyst",
                "dependency_mapper",
                "tech_comparator",
                "trend_validator",
                "integration_feasibility",
                "code_quality_critic",
            ],
            reasoning="Test",
            confidence=0.8,
        )
        assert len(selection_8.agents) == 8

    @pytest.mark.asyncio
    async def test_content_size_thresholds_still_work(self):
        """Verify content size guidelines are preserved with minimum enforcement."""
        # SHORT content - mock returns 3 agents
        mock_selection_short = AgentSelection(
            agents=["implementation_planner", "security_auditor", "dependency_mapper"],
            reasoning="Short content, 3 agents",
            confidence=0.8,
        )

        # COMPREHENSIVE content - mock returns 6 agents
        mock_selection_comprehensive = AgentSelection(
            agents=[
                "implementation_planner",
                "security_auditor",
                "performance_analyst",
                "dependency_mapper",
                "tech_comparator",
                "trend_validator",
            ],
            reasoning="Comprehensive content, 6 agents",
            confidence=0.9,
        )

        mock_structured_model = MagicMock()
        mock_model = MagicMock()
        mock_model.with_structured_output = MagicMock(return_value=mock_structured_model)

        with (
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.get_chat_model",
                return_value=mock_model,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.emit_streaming_event",
                new_callable=AsyncMock,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.should_skip_agent",
                side_effect=mock_no_skip,
            ),
        ):
            # Test SHORT content
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection_short)
            result_short = await supervisor_route(
                content="x" * 500,  # Short content
                content_type="article",
                analysis_id="test-short",
            )
            # Should have at least 3 agents (no enforcement needed)
            assert len(result_short["supervisor_decision"]["agents"]) >= 3

            # Test COMPREHENSIVE content
            mock_structured_model.ainvoke = AsyncMock(return_value=mock_selection_comprehensive)
            result_comp = await supervisor_route(
                content="x" * 5000,  # Comprehensive content
                content_type="article",
                analysis_id="test-comprehensive",
            )
            # Should have at least 5 agents (6 selected, signal filtering disabled)
            assert len(result_comp["supervisor_decision"]["agents"]) >= 5
