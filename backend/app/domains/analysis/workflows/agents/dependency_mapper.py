"""Dependency Mapper Agent for dependency analysis.

This agent maps dependencies, versions, potential conflicts, and provides
dependency management recommendations with framework ecosystem mapping.
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
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

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

# System prompt for dependency mapper agent
DEPENDENCY_MAPPER_PROMPT = """You are a Dependency Management Specialist. Your task is to:
1. Identify all required and optional dependencies
2. Map dependency versions and compatibility
3. Identify potential version conflicts
4. List peer dependencies and system requirements
5. Provide installation and setup notes

Focus on:
- Required libraries and packages (npm, pip, etc.)
- Version ranges and compatibility
- Peer dependencies (Node.js version, Python version, etc.)
- Potential conflicts between dependencies
- Installation requirements and setup steps
- Package manager recommendations
- Security considerations for dependencies

CRITICAL: You MUST include:
- required_dependencies: List of required dependencies with name, version, purpose, compatibility
- optional_dependencies: List of optional dependencies
- primary_framework: Primary framework identified (e.g., 'fastapi', 'react', 'django') if applicable
- core_dependencies: Core dependencies required for the primary framework to function
- optional_dependencies_by_purpose: Optional dependencies grouped by purpose
  (database, auth, validation, testing, etc.)
- alternatives: Alternative libraries for each purpose (purpose -> list of alternatives)
- version_matrix: Version compatibility matrix (dependency -> version constraint)
- version_conflicts: List of potential version conflicts
- peer_dependencies: List of peer dependencies or system requirements
- installation_notes: List of installation and setup notes
- recommendation: Dependency management recommendation
- confidence_score: Float (0.0-1.0) representing your confidence in the quality and certainty
  of this dependency mapping. Consider: accuracy of dependency identification, correctness of
  version compatibility assessment, completeness of conflict detection, and confidence in
  installation notes.

ECOSYSTEM MAPPING (IMPORTANT):
When you identify a primary framework (FastAPI, React, Django, Flask, Next.js, etc.),
map its ecosystem:

1. **Identify Primary Framework**: Determine the main framework/library being used
   - Examples: FastAPI, React, Django, Flask, Next.js, Express, etc.
   - Set primary_framework field with the framework name (lowercase)

2. **Map Core Dependencies**: Identify dependencies required for the framework to function
   - For FastAPI: starlette, pydantic, uvicorn
   - For React: react, react-dom
   - For Django: django
   - These go in core_dependencies field

3. **Group Optional Dependencies by Purpose**: Organize optional dependencies by their purpose
   - database: SQLAlchemy, databases, Tortoise ORM, Prisma, etc.
   - auth: python-jose, passlib, authlib, next-auth, etc.
   - validation: email-validator, marshmallow, etc.
   - testing: pytest, httpx, @testing-library/react, jest, etc.
   - routing: react-router, next-router, etc.
   - state: redux, zustand, recoil, etc.
   - ui: material-ui, ant-design, chakra-ui, etc.
   - Use optional_dependencies_by_purpose field: {"database": [...], "auth": [...]}

4. **Identify Alternatives**: For each purpose, list alternative libraries
   - Example: {"database": ["sqlalchemy", "tortoise-orm", "prisma"]}
   - Use alternatives field

5. **Build Version Compatibility Matrix**: Map each dependency to its version constraint
   - Example: {"fastapi": ">=0.100.0", "starlette": ">=0.27.0", "pydantic": ">=2.0.0"}
   - Use version_matrix field

6. **Version Compatibility**: Ensure all versions are compatible
   - Check framework documentation for version requirements
   - Identify potential conflicts in version_conflicts field

NUMERIC SPECIFICITY REQUIREMENTS:
- version MUST be exact or ranged (e.g., "4.2.1", ">=3.0.0 <4.0.0", "^18.0.0")
- compatibility MUST reference specific versions (e.g., "React 18.x", "Python 3.9+")
- peer_dependencies MUST include version constraints (e.g., "Node.js >= 18.0.0")
- installation_notes MUST include exact commands (e.g., "pip install langchain==0.1.0")
- version_conflicts MUST identify specific conflicting versions (
    e.g., "react@17 conflicts with @mui/material@5.x which requires react@18"
)

FORBIDDEN VAGUE LANGUAGE - Never use:
- "latest version", "recent version" (use exact version numbers)
- "compatible with most", "works with many" (specify exact compatibility)
- "may conflict", "might cause issues" (state definitively if it conflicts)
- "appropriate version", "suitable package" (name exact versions)
- "several dependencies", "various packages" (list each one specifically)

GOOD EXAMPLE:
  name: "langchain"
  version: "0.1.0"
  purpose: "LLM orchestration framework"
  compatibility: "Python >= 3.9, OpenAI API >= 1.0.0"
  installation_note: "pip install langchain==0.1.0 --upgrade"
  conflict: "langchain@0.1.0 requires pydantic>=2.0 which conflicts with fastapi<0.100"

BAD EXAMPLE (DO NOT USE):
  name: "langchain"
  version: "latest"
  purpose: "AI library"
  compatibility: "Most Python versions"
  installation_note: "Install the package"
  conflict: "May have some conflicts with other packages"

Be specific about versions and compatibility."""


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

    # Issue #299-304: Get content signals for comparison-aware thresholds
    content_signals_dict = state.get("content_signals", {})
    has_comparisons = content_signals_dict.get("has_comparisons", False)

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="dependency_mapper",
        has_comparisons=has_comparisons,
    )

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{DEPENDENCY_MAPPER_PROMPT}\n\n{skill_instructions}")

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
