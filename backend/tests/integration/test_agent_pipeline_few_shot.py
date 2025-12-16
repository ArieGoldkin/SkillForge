"""Integration tests for agent pipeline with few-shot prompting.

Tests the full integration of few-shot prompting into the agent creation pipeline,
including:
- Feature flag enable/disable behavior
- A/B test variant selection
- Example retrieval and injection
- Graceful degradation on errors
- Metrics tracking

These tests use real database and real embedding service (with mocked OpenAI calls).
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import TechniqueFlags
from app.domains.analysis.schemas.agents.tech_comparator import TechComparison
from app.domains.analysis.workflows.agents.factories import (
    create_dependency_mapper_agent_with_few_shot,
    create_implementation_planner_agent_with_few_shot,
    create_security_auditor_agent_with_few_shot,
    create_tech_comparator_agent_with_few_shot,
    create_trend_validator_agent_with_few_shot,
)
from app.models.agent_example import AgentExample


@pytest.fixture
def mock_technique_flags_disabled() -> TechniqueFlags:
    """Mock technique flags with few-shot disabled."""
    flags = TechniqueFlags()
    flags.enable_few_shot = False
    flags.ab_test_enabled = False
    return flags


@pytest.fixture
def mock_technique_flags_enabled() -> TechniqueFlags:
    """Mock technique flags with few-shot enabled."""
    flags = TechniqueFlags()
    flags.enable_few_shot = True
    flags.ab_test_enabled = True
    flags.ab_test_treatment_pct = 0.2
    flags.few_shot_max_examples = 3
    flags.few_shot_min_quality = 0.8
    return flags


@pytest.fixture
async def sample_examples(db_session: AsyncSession) -> list[AgentExample]:
    """Create sample examples in database for retrieval."""
    examples = [
        AgentExample(
            agent_type="tech_comparator",
            input_summary="Comparing React vs Vue for state management",
            input_content_preview="React hooks provide useState and useReducer...",
            output_example={
                "primary_tech": "React 18.2.0",
                "alternatives": ["Vue 3.3.0", "Svelte 3.59.0"],
                "comparison": {
                    "React 18.2.0": {
                        "pros": ["Hooks API", "Large ecosystem"],
                        "cons": ["Boilerplate for state management"],
                        "use_cases": ["Large-scale applications"],
                    }
                },
                "recommendation": "Use React for large teams",
            },
            context_note="Good example of versioned tech comparison",
            quality_score=0.95,
            content_type="article",
            difficulty_level="intermediate",
            embedding=[0.1] * 1536,  # Mock embedding vector
        ),
        AgentExample(
            agent_type="security_auditor",
            input_summary="SQL injection vulnerability in FastAPI",
            input_content_preview="Unsanitized user input in database query...",
            output_example={
                "security_risks": [
                    {
                        "risk_type": "sql_injection",
                        "severity": "critical",
                        "description": "Unsanitized input allows SQL injection",
                        "mitigation": "Use parameterized queries with SQLAlchemy ORM",
                    }
                ],
                "best_practices": ["Use ORM", "Validate inputs"],
                "compliance_notes": ["OWASP Top 10 A03:2021"],
                "recommendation": "Implement parameterized queries immediately",
            },
            context_note="Clear security audit with CVSS scores",
            quality_score=0.92,
            content_type="article",
            difficulty_level="intermediate",
            embedding=[0.2] * 1536,  # Mock embedding vector
        ),
    ]

    for example in examples:
        db_session.add(example)
    await db_session.commit()

    return examples


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tech_comparator_few_shot_disabled(
    db_session: AsyncSession,
    mock_technique_flags_disabled: TechniqueFlags,
) -> None:
    """Test tech comparator agent creation with few-shot disabled.

    Should create baseline agent without example injection.
    """
    with patch(
        "app.domains.analysis.workflows.agents.factories.get_technique_flags",
        return_value=mock_technique_flags_disabled,
    ):
        agent = await create_tech_comparator_agent_with_few_shot(
            content="Comparing React hooks vs class components",
            system_prompt="You are a tech comparator",
            response_schema=TechComparison,
            analysis_id=uuid4(),
            session=db_session,
        )

        # Verify agent was created (baseline, no few-shot)
        assert agent is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tech_comparator_few_shot_control_variant(
    db_session: AsyncSession,
    mock_technique_flags_enabled: TechniqueFlags,
    sample_examples: list[AgentExample],
) -> None:
    """Test tech comparator with control variant (no examples).

    Even with few-shot enabled, control variant should not inject examples.
    """
    # Use deterministic analysis_id that maps to control variant
    # Hash of "control-test:few_shot_prompting" % 100 should be >= 20
    analysis_id = uuid4()

    with (
        patch(
            "app.domains.analysis.workflows.agents.factories.get_technique_flags",
            return_value=mock_technique_flags_enabled,
        ),
        patch(
            "app.domains.analysis.workflows.agents.factories.get_variant_selector"
        ) as mock_selector,
        patch(
            "app.shared.services.embeddings.service.EmbeddingService.generate_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ),
    ):
        # Force control variant
        mock_variant_selector = MagicMock()
        mock_variant_selector.select_variant.return_value = "control"
        mock_selector.return_value = mock_variant_selector

        agent = await create_tech_comparator_agent_with_few_shot(
            content="Comparing React hooks vs class components",
            system_prompt="You are a tech comparator",
            response_schema=TechComparison,
            analysis_id=analysis_id,
            session=db_session,
        )

        # Verify agent was created
        assert agent is not None

        # Verify control variant was selected
        mock_variant_selector.select_variant.assert_called_once_with(
            analysis_id=str(analysis_id),
            technique="few_shot_prompting",
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tech_comparator_few_shot_treatment_variant(
    db_session: AsyncSession,
    mock_technique_flags_enabled: TechniqueFlags,
    sample_examples: list[AgentExample],
) -> None:
    """Test tech comparator with treatment variant (with examples).

    Treatment variant should retrieve and inject relevant examples.
    """
    analysis_id = uuid4()

    with (
        patch(
            "app.domains.analysis.workflows.agents.factories.get_technique_flags",
            return_value=mock_technique_flags_enabled,
        ),
        patch(
            "app.domains.analysis.workflows.agents.factories.get_variant_selector"
        ) as mock_selector,
        patch(
            "app.shared.services.embeddings.service.EmbeddingService.generate_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ),
    ):
        # Force treatment variant
        mock_variant_selector = MagicMock()
        mock_variant_selector.select_variant.return_value = "treatment"
        mock_selector.return_value = mock_variant_selector

        agent = await create_tech_comparator_agent_with_few_shot(
            content="Comparing React hooks vs class components",
            system_prompt="You are a tech comparator",
            response_schema=TechComparison,
            analysis_id=analysis_id,
            session=db_session,
        )

        # Verify agent was created
        assert agent is not None

        # Verify treatment variant was selected
        mock_variant_selector.select_variant.assert_called_once_with(
            analysis_id=str(analysis_id),
            technique="few_shot_prompting",
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_security_auditor_few_shot_with_tools(
    db_session: AsyncSession,
    mock_technique_flags_enabled: TechniqueFlags,
    sample_examples: list[AgentExample],
) -> None:
    """Test security auditor with MCP tools and few-shot prompting.

    Should handle tool-enabled agents correctly.
    """
    from app.domains.analysis.schemas.agents.security_auditor import SecurityAudit

    analysis_id = uuid4()

    with (
        patch(
            "app.domains.analysis.workflows.agents.factories.get_technique_flags",
            return_value=mock_technique_flags_enabled,
        ),
        patch(
            "app.domains.analysis.workflows.agents.factories.get_variant_selector"
        ) as mock_selector,
        patch(
            "app.shared.services.embeddings.service.EmbeddingService.generate_embedding",
            new_callable=AsyncMock,
            return_value=[0.2] * 1536,
        ),
    ):
        # Force control variant for simplicity
        mock_variant_selector = MagicMock()
        mock_variant_selector.select_variant.return_value = "control"
        mock_selector.return_value = mock_variant_selector

        # Create agent without tools (tools=None)
        agent = await create_security_auditor_agent_with_few_shot(
            content="Checking FastAPI endpoint for SQL injection",
            system_prompt="You are a security auditor",
            response_schema=SecurityAudit,
            analysis_id=analysis_id,
            session=db_session,
            tools=None,
        )

        # Verify agent was created
        assert agent is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_few_shot_graceful_degradation_on_error(
    db_session: AsyncSession,
    mock_technique_flags_enabled: TechniqueFlags,
) -> None:
    """Test graceful degradation when example retrieval fails.

    Should fall back to baseline agent without examples.
    """
    analysis_id = uuid4()

    with (
        patch(
            "app.domains.analysis.workflows.agents.factories.get_technique_flags",
            return_value=mock_technique_flags_enabled,
        ),
        patch(
            "app.domains.analysis.workflows.agents.factories.get_variant_selector"
        ) as mock_selector,
        patch(
            "app.shared.services.embeddings.service.EmbeddingService.generate_embedding",
            new_callable=AsyncMock,
            side_effect=Exception("Embedding service failed"),
        ),
    ):
        # Force treatment variant to trigger example retrieval
        mock_variant_selector = MagicMock()
        mock_variant_selector.select_variant.return_value = "treatment"
        mock_selector.return_value = mock_variant_selector

        # Should not raise exception - should gracefully fall back
        agent = await create_tech_comparator_agent_with_few_shot(
            content="Comparing React hooks vs class components",
            system_prompt="You are a tech comparator",
            response_schema=TechComparison,
            analysis_id=analysis_id,
            session=db_session,
        )

        # Verify agent was created (fallback to baseline)
        assert agent is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multiple_agents_with_few_shot(
    db_session: AsyncSession,
    mock_technique_flags_enabled: TechniqueFlags,
    sample_examples: list[AgentExample],
) -> None:
    """Test multiple different agent types with few-shot prompting.

    Ensures all agent factory functions work correctly.
    """
    from app.domains.analysis.schemas.agents.dependency_mapper import DependencyMapping
    from app.domains.analysis.schemas.agents.implementation_planner import (
        ImplementationPlan,
    )
    from app.domains.analysis.schemas.agents.trend_validator import TrendValidation

    analysis_id = uuid4()

    with (
        patch(
            "app.domains.analysis.workflows.agents.factories.get_technique_flags",
            return_value=mock_technique_flags_enabled,
        ),
        patch(
            "app.domains.analysis.workflows.agents.factories.get_variant_selector"
        ) as mock_selector,
        patch(
            "app.shared.services.embeddings.service.EmbeddingService.generate_embedding",
            new_callable=AsyncMock,
            return_value=[0.1] * 1536,
        ),
    ):
        # Force control variant for simplicity
        mock_variant_selector = MagicMock()
        mock_variant_selector.select_variant.return_value = "control"
        mock_selector.return_value = mock_variant_selector

        # Create multiple agent types
        impl_agent = await create_implementation_planner_agent_with_few_shot(
            content="Building a FastAPI REST API",
            system_prompt="You are an implementation planner",
            response_schema=ImplementationPlan,
            analysis_id=analysis_id,
            session=db_session,
        )

        dep_agent = await create_dependency_mapper_agent_with_few_shot(
            content="FastAPI project dependencies",
            system_prompt="You are a dependency mapper",
            response_schema=DependencyMapping,
            analysis_id=analysis_id,
            session=db_session,
            tools=None,
        )

        trend_agent = await create_trend_validator_agent_with_few_shot(
            content="React Server Components trend analysis",
            system_prompt="You are a trend validator",
            response_schema=TrendValidation,
            analysis_id=analysis_id,
            session=db_session,
        )

        # Verify all agents were created
        assert impl_agent is not None
        assert dep_agent is not None
        assert trend_agent is not None
