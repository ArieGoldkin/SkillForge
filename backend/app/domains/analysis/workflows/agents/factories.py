"""Agent factory wrappers with few-shot prompting integration.

This module provides factory functions that wrap agent creation with optional
few-shot prompting capabilities. Each factory:
- Checks feature flags to enable/disable few-shot prompting
- Uses A/B testing to assign analyses to control/treatment groups
- Injects relevant examples via semantic search
- Falls back gracefully to baseline agents on errors

Architecture:
- Feature flag: TECHNIQUE_ENABLE_FEW_SHOT controls overall feature
- A/B testing: 20% traffic split between control and treatment
- Variant selection: Deterministic hash-based assignment per analysis_id
- Example retrieval: Semantic search with quality filtering
- Graceful degradation: Falls back to baseline on any errors

Example:
    >>> async with AsyncSessionLocal() as session:
    ...     agent = await create_tech_comparator_agent_with_few_shot(
    ...         content="Comparing React vs Vue",
    ...         system_prompt=TECH_COMPARATOR_PROMPT,
    ...         response_schema=TechComparison,
    ...         analysis_id=analysis_id,
    ...         session=session,
    ...     )

"""

from collections.abc import Sequence
from typing import Any

from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.feature_flags import get_technique_flags
from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.base import (
    ToolCallConfig,
    create_structured_agent,
    create_tool_enabled_agent,
)
from app.shared.services.ab_testing import get_variant_selector
from app.shared.services.agents.few_shot_factory import create_few_shot_agent
from app.shared.services.embeddings.service import EmbeddingService

logger = get_logger(__name__)


async def create_agent_with_optional_few_shot(  # noqa: PLR0913 - Factory needs all params
    agent_type: str,
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
    tools: Sequence[BaseTool] | None = None,
    tool_call_config: ToolCallConfig | None = None,
) -> Runnable:
    """Create agent with optional few-shot prompting based on feature flags.

    This is the core factory function that all agent-specific factories delegate to.
    It handles:
    - Feature flag checking
    - A/B test variant selection
    - Few-shot example injection (treatment group)
    - Baseline agent creation (control group)
    - Tool-enabled vs non-tool agent creation

    Args:
        agent_type: Type of agent (e.g., 'tech_comparator', 'security_auditor')
        content: Input content for analysis (used for semantic example search)
        system_prompt: Base system prompt for the agent
        response_schema: Pydantic model defining expected output structure
        analysis_id: UUID of the analysis (for deterministic variant assignment)
        session: Database session for example retrieval
        tools: Optional MCP tools for tool-enabled agents
        tool_call_config: Optional tool call configuration

    Returns:
        Runnable: Agent instance (with or without few-shot examples)

    Raises:
        Exception: If agent creation fails (after logging and fallback attempts)

    """
    flags = get_technique_flags()

    # If few-shot is disabled, create baseline agent
    if not flags.enable_few_shot:
        logger.debug(
            "few_shot_disabled",
            agent_type=agent_type,
            analysis_id=str(analysis_id),
        )
        if tools:
            return create_tool_enabled_agent(
                system_prompt=system_prompt,
                response_schema=response_schema,
                tools=tools,
                tool_call_config=tool_call_config,
            )
        return create_structured_agent(
            system_prompt=system_prompt,
            response_schema=response_schema,
        )

    # Select A/B test variant (deterministic based on analysis_id)
    variant_selector = get_variant_selector()
    variant = variant_selector.select_variant(
        analysis_id=str(analysis_id),
        technique="few_shot_prompting",
    )

    logger.info(
        "few_shot_variant_selected",
        agent_type=agent_type,
        analysis_id=str(analysis_id),
        variant=variant,
        ab_test_enabled=flags.ab_test_enabled,
    )

    # Create base agent factory for few-shot wrapper
    def base_agent_factory(**kwargs: Any) -> Runnable:
        """Create baseline agent with optional prompt enhancement.

        This factory is passed to create_few_shot_agent() which will:
        - Call it with enhanced system_prompt (treatment variant)
        - Call it with original system_prompt (control variant)
        """
        prompt = kwargs.get("system_prompt", system_prompt)
        if tools:
            return create_tool_enabled_agent(
                system_prompt=prompt,
                response_schema=response_schema,
                tools=tools,
                tool_call_config=tool_call_config,
            )
        return create_structured_agent(
            system_prompt=prompt,
            response_schema=response_schema,
        )

    # Create embedding service for semantic example search
    embedding_service = EmbeddingService()

    # Use few-shot factory (handles both control and treatment)
    agent: Runnable = await create_few_shot_agent(
        agent_type=agent_type,
        content=content,
        base_agent_factory=base_agent_factory,
        session=session,
        embedding_service=embedding_service,
        variant=variant,
        max_examples=flags.few_shot_max_examples,
        min_quality_score=flags.few_shot_min_quality,
        system_prompt=system_prompt,
    )
    return agent


# Agent-specific factory functions (for clean API and type safety)


async def create_tech_comparator_agent_with_few_shot(
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> Runnable:
    """Create tech comparator agent with optional few-shot prompting.

    Args:
        content: Input content for analysis
        system_prompt: System prompt for tech comparator
        response_schema: Expected output schema (TechComparison)
        analysis_id: Analysis UUID
        session: Database session

    Returns:
        Runnable: Tech comparator agent instance

    """
    return await create_agent_with_optional_few_shot(
        agent_type="tech_comparator",
        content=content,
        system_prompt=system_prompt,
        response_schema=response_schema,
        analysis_id=analysis_id,
        session=session,
    )


async def create_security_auditor_agent_with_few_shot(  # noqa: PLR0913 - Factory needs all params
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
    tools: Sequence[BaseTool] | None = None,
) -> Runnable:
    """Create security auditor agent with optional few-shot prompting.

    Args:
        content: Input content for analysis
        system_prompt: System prompt for security auditor
        response_schema: Expected output schema (SecurityAudit)
        analysis_id: Analysis UUID
        session: Database session
        tools: Optional MCP tools

    Returns:
        Runnable: Security auditor agent instance

    """
    return await create_agent_with_optional_few_shot(
        agent_type="security_auditor",
        content=content,
        system_prompt=system_prompt,
        response_schema=response_schema,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
        tool_call_config=ToolCallConfig(max_tool_calls=15) if tools else None,
    )


async def create_implementation_planner_agent_with_few_shot(
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> Runnable:
    """Create implementation planner agent with optional few-shot prompting.

    Args:
        content: Input content for analysis
        system_prompt: System prompt for implementation planner
        response_schema: Expected output schema (ImplementationPlan)
        analysis_id: Analysis UUID
        session: Database session

    Returns:
        Runnable: Implementation planner agent instance

    """
    return await create_agent_with_optional_few_shot(
        agent_type="implementation_planner",
        content=content,
        system_prompt=system_prompt,
        response_schema=response_schema,
        analysis_id=analysis_id,
        session=session,
    )


async def create_dependency_mapper_agent_with_few_shot(  # noqa: PLR0913 - Factory needs all params
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
    tools: Sequence[BaseTool] | None = None,
) -> Runnable:
    """Create dependency mapper agent with optional few-shot prompting.

    Args:
        content: Input content for analysis
        system_prompt: System prompt for dependency mapper
        response_schema: Expected output schema (DependencyMapping)
        analysis_id: Analysis UUID
        session: Database session
        tools: Optional MCP tools

    Returns:
        Runnable: Dependency mapper agent instance

    """
    return await create_agent_with_optional_few_shot(
        agent_type="dependency_mapper",
        content=content,
        system_prompt=system_prompt,
        response_schema=response_schema,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
        tool_call_config=ToolCallConfig(max_tool_calls=20) if tools else None,
    )


async def create_trend_validator_agent_with_few_shot(
    content: str,
    system_prompt: str,
    response_schema: type[BaseModel],
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> Runnable:
    """Create trend validator agent with optional few-shot prompting.

    Args:
        content: Input content for analysis
        system_prompt: System prompt for trend validator
        response_schema: Expected output schema (TrendValidation)
        analysis_id: Analysis UUID
        session: Database session

    Returns:
        Runnable: Trend validator agent instance

    """
    return await create_agent_with_optional_few_shot(
        agent_type="trend_validator",
        content=content,
        system_prompt=system_prompt,
        response_schema=response_schema,
        analysis_id=analysis_id,
        session=session,
    )
