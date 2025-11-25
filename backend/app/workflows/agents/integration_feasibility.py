"""Integration Feasibility Agent for integration assessment.

This agent analyzes how technologies integrate with modern stacks, assessing
compatibility, migration effort, breaking changes, and providing integration guidance.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas import IntegrationFeasibility

# System prompt for integration feasibility agent
INTEGRATION_FEASIBILITY_PROMPT = """You are an Integration Feasibility Analyst. Your task is to:
1. Analyze how the technology integrates with modern development stacks
2. Assess compatibility with common frameworks and tools
   (Next.js, React, FastAPI, PostgreSQL, Docker, etc.)
3. Evaluate migration effort (low/medium/high) and identify potential breaking changes
4. Provide step-by-step integration guidance

CRITICAL: You MUST include a "compatibility" field with at least 2-3 stack assessments.
Each compatibility entry must contain: score (0.0-1.0) and notes (string).
Assess compatibility for stacks mentioned in the content (
    e.g., nextjs, fastapi, postgresql, react, docker
).

Focus on:
- API compatibility and integration patterns
- Dependency management and version conflicts
- Configuration requirements
- Migration paths from similar technologies
- Potential breaking changes and mitigation strategies

Provide practical, actionable integration recommendations."""


async def run_integration_feasibility(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> dict[str, object]:
    """Run integration feasibility agent to assess integration compatibility.

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
        system_prompt=INTEGRATION_FEASIBILITY_PROMPT,
        response_schema=IntegrationFeasibility,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="integration_feasibility",
        session=session,
    )
