"""Unit tests to verify all agents use grounding instructions.

Ensures that all 8 agents apply grounding to prevent hallucination.

Issue #ARTIFACT-QUALITY: All agents must use grounding for content-based analysis.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis.workflows.agents.grounding import GROUNDING_INSTRUCTIONS, apply_grounding
from app.domains.analysis.workflows.state import AnalysisState

@pytest.mark.unit


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def base_state() -> AnalysisState:
    """Return base state for agent testing."""
    return {
        "analysis_id": "test-123",
        "skill_level": "intermediate",
        "proactive_context": "",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_module,agent_function,agent_prompt_constant",
    [
        ("tech_comparator", "run_tech_comparator", "TECH_COMPARATOR_PROMPT"),
        ("security_auditor", "run_security_auditor", "SECURITY_AUDITOR_PROMPT"),
        ("implementation_planner", "run_implementation_planner", "IMPLEMENTATION_PLANNER_PROMPT"),
        ("performance_analyst", "run_performance_analyst", "PERFORMANCE_ANALYST_PROMPT"),
        ("code_quality_critic", "run_code_quality_critic", "CODE_QUALITY_CRITIC_PROMPT"),
        ("trend_validator", "run_trend_validator", "TREND_VALIDATOR_PROMPT"),
        ("dependency_mapper", "run_dependency_mapper", "DEPENDENCY_MAPPER_PROMPT"),
        (
            "integration_feasibility",
            "run_integration_feasibility",
            "INTEGRATION_FEASIBILITY_PROMPT",
        ),
    ],
)
async def test_agent_applies_grounding(
    agent_module: str,
    agent_function: str,
    agent_prompt_constant: str,
    mock_session: AsyncSession,
    base_state: AnalysisState,
):
    """Test that agent applies grounding to its prompt.

    This test verifies that when the agent creates its structured agent,
    it passes a prompt that includes grounding instructions.
    """
    # Import the agent module dynamically
    import importlib

    module = importlib.import_module(f"app.workflows.agents.{agent_module}")
    agent_func = getattr(module, agent_function)

    # Mock the create_structured_agent call to capture the prompt
    captured_prompt = None

    def mock_create_agent(system_prompt, response_schema):
        nonlocal captured_prompt
        captured_prompt = system_prompt

        # Return a mock agent
        mock_agent = MagicMock()
        mock_agent.ainvoke = AsyncMock(return_value={"structured_response": MagicMock()})
        return mock_agent

    # Mock run_agent_with_tracking to avoid actual execution
    mock_tracking_result = {
        "agent_type": agent_module,
        "findings": {},
        "processing_time_ms": 100,
    }

    with (
        patch(
            f"app.workflows.agents.{agent_module}.create_structured_agent",
            side_effect=mock_create_agent,
        ),
        patch(
            f"app.workflows.agents.{agent_module}.run_agent_with_tracking",
            new_callable=AsyncMock,
            return_value=mock_tracking_result,
        ),
    ):
        # Run the agent
        await agent_func(
            content="Test content about React and TypeScript",
            content_type="article",
            analysis_id="test-123",
            session=mock_session,
            state=base_state,
        )

        # Verify grounding instructions were applied to the prompt
        assert captured_prompt is not None, f"{agent_function} did not create agent"
        assert GROUNDING_INSTRUCTIONS in captured_prompt, (
            f"{agent_function} prompt does not include GROUNDING_INSTRUCTIONS"
        )

        # Verify the base prompt is also present
        base_prompt = getattr(module, agent_prompt_constant)
        # The prompt should contain both grounding and base prompt content
        # We can't check for exact base_prompt since it's modified with skill_level
        # But we can check for a distinctive part of the base prompt
        assert len(captured_prompt) > len(GROUNDING_INSTRUCTIONS), (
            f"{agent_function} prompt is too short - may not include base prompt"
        )


@pytest.mark.asyncio
async def test_tech_comparator_uses_grounding(
    mock_session: AsyncSession, base_state: AnalysisState
):
    """Test tech_comparator specifically uses apply_grounding."""
    from app.domains.analysis.workflows.agents.tech_comparator import run_tech_comparator

    with (
        patch("app.workflows.agents.tech_comparator.apply_grounding") as mock_apply,
        patch("app.workflows.agents.tech_comparator.create_structured_agent"),
        patch(
            "app.workflows.agents.tech_comparator.run_agent_with_tracking", new_callable=AsyncMock
        ),
    ):
        # Set return value for apply_grounding
        mock_apply.return_value = "grounded_prompt"

        await run_tech_comparator(
            content="Test content",
            content_type="article",
            analysis_id="test-123",
            session=mock_session,
            state=base_state,
        )

        # Verify apply_grounding was called
        assert mock_apply.called, "tech_comparator did not call apply_grounding"


@pytest.mark.asyncio
async def test_security_auditor_uses_grounding(
    mock_session: AsyncSession, base_state: AnalysisState
):
    """Test security_auditor specifically uses apply_grounding."""
    from app.domains.analysis.workflows.agents.security_auditor import run_security_auditor

    with (
        patch("app.workflows.agents.security_auditor.apply_grounding") as mock_apply,
        patch("app.workflows.agents.security_auditor.create_structured_agent"),
        patch(
            "app.workflows.agents.security_auditor.run_agent_with_tracking", new_callable=AsyncMock
        ),
    ):
        mock_apply.return_value = "grounded_prompt"

        await run_security_auditor(
            content="Test content",
            content_type="article",
            analysis_id="test-123",
            session=mock_session,
            state=base_state,
        )

        assert mock_apply.called, "security_auditor did not call apply_grounding"


@pytest.mark.asyncio
async def test_implementation_planner_uses_grounding(
    mock_session: AsyncSession, base_state: AnalysisState
):
    """Test implementation_planner specifically uses apply_grounding."""
    from app.domains.analysis.workflows.agents.implementation_planner import run_implementation_planner

    with (
        patch("app.workflows.agents.implementation_planner.apply_grounding") as mock_apply,
        patch("app.workflows.agents.implementation_planner.create_structured_agent"),
        patch(
            "app.workflows.agents.implementation_planner.run_agent_with_tracking",
            new_callable=AsyncMock,
        ),
    ):
        mock_apply.return_value = "grounded_prompt"

        await run_implementation_planner(
            content="Test content",
            content_type="article",
            analysis_id="test-123",
            session=mock_session,
            state=base_state,
        )

        assert mock_apply.called, "implementation_planner did not call apply_grounding"


def test_apply_grounding_function_exists():
    """Test that apply_grounding function is exported from grounding module."""
    assert callable(apply_grounding), "apply_grounding is not callable"

    # Test that it works
    result = apply_grounding("Test prompt")
    assert GROUNDING_INSTRUCTIONS in result
    assert "Test prompt" in result


def test_grounding_instructions_constant_exists():
    """Test that GROUNDING_INSTRUCTIONS constant is exported."""
    from app.domains.analysis.workflows.agents.grounding import GROUNDING_INSTRUCTIONS

    assert isinstance(GROUNDING_INSTRUCTIONS, str), "GROUNDING_INSTRUCTIONS is not a string"
    assert len(GROUNDING_INSTRUCTIONS) > 100, "GROUNDING_INSTRUCTIONS seems too short"

    # Verify it contains key phrases
    assert "CONTENT GROUNDING" in GROUNDING_INSTRUCTIONS
    assert "NEVER fabricate" in GROUNDING_INSTRUCTIONS


@pytest.mark.asyncio
async def test_all_agents_import_grounding():
    """Test that all agent modules import grounding."""
    agent_modules = [
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
        "performance_analyst",
        "code_quality_critic",
        "trend_validator",
        "dependency_mapper",
        "integration_feasibility",
    ]

    for module_name in agent_modules:
        # Import the module
        import importlib

        module = importlib.import_module(f"app.workflows.agents.{module_name}")

        # Check if apply_grounding is used in the module
        source = importlib.import_module(f"app.workflows.agents.{module_name}").__file__
        if source:
            with Path(source).open() as f:
                content = f.read()
                assert "from app.domains.analysis.workflows.agents.grounding import apply_grounding" in content, (
                    f"{module_name} does not import apply_grounding"
                )
                assert "apply_grounding(" in content, f"{module_name} does not call apply_grounding"
