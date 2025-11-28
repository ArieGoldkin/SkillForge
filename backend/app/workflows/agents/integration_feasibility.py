"""Integration Feasibility Agent for integration assessment.

This agent analyzes how technologies integrate with modern stacks, assessing
compatibility, migration effort, breaking changes, and providing integration guidance.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.schemas.integration_feasibility import IntegrationFeasibility

# System prompt for integration feasibility agent
INTEGRATION_FEASIBILITY_PROMPT = """You are an Integration Analyst.
Assess technology integration with modern stacks.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure:
{
  "compatibility": {
    "react": {"score": 0.9, "notes": "Native support"},
    "nextjs": {"score": 0.85, "notes": "SSR compatible"},
    "fastapi": {"score": 0.8, "notes": "Python backend compatible"}
  },
  "migration_effort": "medium",
  "breaking_changes": ["List", "of", "breaking", "changes"],
  "integration_steps": ["Step 1", "Step 2", "Step 3"]
}

Field Requirements:
1. **compatibility** (REQUIRED): Dictionary with 2-3 stack entries.
   - Keys: stack names like "react", "nextjs", "fastapi", "docker"
   - Values: {"score": 0.0-1.0, "notes": "string"}
   - Example: {"react": {"score": 0.9, "notes": "Native support"}}

2. **migration_effort** (REQUIRED): One of: "low", "medium", "high"

3. **breaking_changes** (REQUIRED): List of strings (can be empty [])

4. **integration_steps** (REQUIRED): List of strings (can be empty [])

IMPORTANT: Include the "compatibility" field with at least 2 stack entries. "
    "Do not omit any required fields."""


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
