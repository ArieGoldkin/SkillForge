"""Dependency Mapper Agent for dependency analysis.

This agent maps dependencies, versions, potential conflicts, and provides
dependency management recommendations with framework ecosystem mapping.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.schemas.dependency_mapper import DependencyMapping

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


async def run_dependency_mapper(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> dict[str, object]:
    """Run dependency mapper agent to map dependencies and versions.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Create agent with structured output
    agent = create_structured_agent(
        system_prompt=DEPENDENCY_MAPPER_PROMPT,
        response_schema=DependencyMapping,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="dependency_mapper",
        session=session,
    )
