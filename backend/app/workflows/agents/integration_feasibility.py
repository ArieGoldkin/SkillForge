"""Integration Feasibility Agent for integration assessment.

This agent analyzes how technologies integrate with modern stacks, assessing
compatibility, migration effort, breaking changes, and providing integration guidance.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas import IntegrationFeasibility

# System prompt for integration feasibility agent
INTEGRATION_FEASIBILITY_PROMPT = """You are an Integration Analyst.
Assess technology integration with modern stacks.

For the given content, provide:
1. compatibility: Score (0.0-1.0) and notes for 2-3 common stacks
   (nextjs, fastapi, react, docker, etc.)
2. migration_effort: low/medium/high
3. breaking_changes: List of potential issues
4. integration_steps: Actionable steps to integrate

Be concise. Focus on practical, actionable insights."""


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
