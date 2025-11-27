"""Dependency Mapper Agent for dependency analysis.

This agent maps dependencies, versions, potential conflicts, and provides
dependency management recommendations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas.dependency_mapper import DependencyMapping

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
- version_conflicts: List of potential version conflicts
- peer_dependencies: List of peer dependencies or system requirements
- installation_notes: List of installation and setup notes
- recommendation: Dependency management recommendation

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
