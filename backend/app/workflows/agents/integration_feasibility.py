"""Integration Feasibility Agent for integration assessment.

This agent analyzes how technologies integrate with modern stacks, assessing
compatibility, migration effort, breaking changes, and providing integration guidance.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas.integration_feasibility import IntegrationFeasibility

# System prompt for integration feasibility agent
INTEGRATION_FEASIBILITY_PROMPT = """You are an Integration Analyst.
Assess technology integration with modern stacks.

For the given content, you MUST provide ALL of these fields:

1. **compatibility** (REQUIRED - DO NOT OMIT): A dictionary mapping stack names to scores.
   Each entry MUST have:
   - score: A float from 0.0 to 1.0
   - notes: A brief explanation string
   Include 2-3 stacks like: react, nextjs, fastapi, docker, etc.
   Example: {"react": {"score": 0.9, "notes": "Native support"}}

2. **migration_effort**: One of: "low", "medium", or "high"

3. **breaking_changes**: List of potential breaking changes

4. **integration_steps**: List of actionable integration steps

IMPORTANT: The 'compatibility' field is REQUIRED. Do not skip it."""


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
