"""Dependency Mapper Agent for dependency analysis.

This agent maps dependencies, versions, potential conflicts, and provides
dependency management recommendations with framework ecosystem mapping.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.dependency_mapper import DependencyMapping
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import (
    create_dependency_mapper_agent_with_few_shot,
)
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-dependency-mapper"

# Framework ecosystems mapping
FRAMEWORK_ECOSYSTEMS = {
    "fastapi": {
        "core": ["starlette", "pydantic", "uvicorn"],
        "database": ["sqlalchemy", "databases", "tortoise-orm", "prisma"],
        "auth": ["python-jose", "passlib", "authlib"],
        "validation": ["email-validator"],
        "testing": ["pytest", "httpx", "pytest-asyncio"],
    },
    "django": {
        "core": ["django"],
        "database": ["psycopg2", "mysqlclient", "django-extensions"],
        "auth": ["django-allauth", "djangorestframework-simplejwt"],
        "validation": ["django-crispy-forms"],
        "testing": ["pytest-django", "django-test-plus"],
    },
    "flask": {
        "core": ["flask", "werkzeug", "jinja2"],
        "database": ["flask-sqlalchemy", "flask-migrate"],
        "auth": ["flask-login", "flask-jwt-extended"],
        "validation": ["flask-wtf", "marshmallow"],
        "testing": ["pytest-flask"],
    },
    "react": {
        "core": ["react", "react-dom"],
        "routing": ["react-router", "react-router-dom"],
        "state": ["redux", "zustand", "recoil"],
        "ui": ["material-ui", "ant-design", "chakra-ui"],
        "testing": ["@testing-library/react", "jest"],
    },
    "next.js": {
        "core": ["next", "react", "react-dom"],
        "routing": ["next-router"],
        "database": ["prisma", "@prisma/client"],
        "auth": ["next-auth", "auth0"],
        "testing": ["@testing-library/react", "jest"],
    },
}


async def run_dependency_mapper(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run dependency mapper agent.

    Args:
        content: Analyzed content
        content_type: Type of content
        analysis_id: Analysis ID
        session: Database session
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced dependency analysis

    Returns:
        Agent findings dict

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Issue #299-304: Get content-aware specificity threshold
    # Read from flat field injected by build_scoped_context()
    expectation = state.get("agent_expectation")

    # Issue #299-304, #442: Get content signals for comparison/research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    # Issue #442: Detect research/conceptual content for very low thresholds
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="dependency_mapper",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting (Phase 1, Week 2.3)
    # Handles both tool-enabled and non-tool variants
    agent = await create_dependency_mapper_agent_with_few_shot(
        content=content,
        system_prompt=full_prompt,
        response_schema=DependencyMapping,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    if tools:
        logger.info(
            "dependency_mapper_using_mcp_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="dependency_mapper",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
