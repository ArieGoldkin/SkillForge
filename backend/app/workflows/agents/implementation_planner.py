"""Implementation Planner Agent for step-by-step implementation guides.

This agent creates actionable implementation guides with prerequisites, numbered
steps, file structure recommendations, and testing strategies.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas import ImplementationPlan

# System prompt for implementation planner agent
IMPLEMENTATION_PLANNER_PROMPT = """You are an Implementation Planning Specialist. Your task is to:
1. Create a step-by-step implementation guide based on the content
2. Identify prerequisites (dependencies, setup, configuration)
3. Break down implementation into numbered, actionable steps
4. Specify which files need to be created or modified in each step
5. Provide a testing strategy and validation approach
6. Estimate implementation time

Focus on:
- Clear, sequential steps that can be followed independently
- Specific file paths and code locations
- Dependencies between steps
- Testing and validation at each stage
- Common pitfalls and how to avoid them

Make the guide practical and immediately actionable for developers."""


async def run_implementation_planner(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> dict[str, object]:
    """Run implementation planner agent to create step-by-step implementation guide.

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
        system_prompt=IMPLEMENTATION_PLANNER_PROMPT,
        response_schema=ImplementationPlan,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="implementation_planner",
        session=session,
    )
