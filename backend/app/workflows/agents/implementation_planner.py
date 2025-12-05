"""Implementation Planner Agent for step-by-step implementation guides.

This agent creates actionable implementation guides with prerequisites, numbered
steps, file structure recommendations, and testing strategies.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.schemas.implementation_planner import ImplementationPlan
from app.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.workflows.state import AnalysisState

# System prompt for implementation planner agent
IMPLEMENTATION_PLANNER_PROMPT = """You are an Implementation Planning Specialist. Your task is to:
1. Create a step-by-step implementation guide based on the content
2. Identify prerequisites (dependencies, setup, configuration)
3. Break down implementation into numbered, actionable steps
4. Specify which files need to be created or modified in each step
5. Provide a testing strategy and validation approach
6. Estimate implementation time
7. Provide a confidence score (0.0-1.0) representing your confidence in the quality
   and completeness of this implementation plan. Consider: clarity of steps, accuracy
   of prerequisites, reasonableness of time estimates, and actionability of the guide.
   Higher scores indicate more complete, accurate, and actionable plans.

Focus on:
- Clear, sequential steps that can be followed independently
- Specific file paths and code locations
- Dependencies between steps
- Testing and validation at each stage
- Common pitfalls and how to avoid them

NUMERIC SPECIFICITY REQUIREMENTS:
- estimated_time MUST be specific (e.g., "2-3 hours", "45 minutes", "1 day")
- Each step action MUST include specific details (file paths, config values, command examples)
- prerequisites MUST include version numbers where applicable (e.g., "Node.js >= 18.0.0")
- files list MUST use full relative paths (e.g., "src/components/Button.tsx")
- testing_strategy MUST include specific coverage targets (e.g., "80% line coverage")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "appropriate", "suitable", "reasonable", "adequate", "proper"
- "some time", "a while", "soon" (use specific durations)
- "relevant files", "necessary changes" (name the actual files)
- "several", "many", "few", "some", "various"
- "might need", "could require" (be definitive about requirements)

GOOD EXAMPLE:
  step: 1
  action: "Install dependencies: `npm install langchain@0.1.0 zod@3.22.0`"
  files: ["package.json", "package-lock.json"]
  estimated_time: "2-3 hours"
  prerequisite: "Node.js >= 18.0.0, npm >= 9.0.0"

BAD EXAMPLE (DO NOT USE):
  step: 1
  action: "Install necessary dependencies"
  files: ["relevant config files"]
  estimated_time: "some time"
  prerequisite: "Node.js installed"

Make the guide practical and immediately actionable for developers."""


async def run_implementation_planner(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run implementation planner agent to create step-by-step implementation guide.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Build prompt with skill level instructions
    full_prompt = f"{IMPLEMENTATION_PLANNER_PROMPT}\n\n{skill_instructions}"

    # Create agent with structured output
    agent = create_structured_agent(
        system_prompt=full_prompt,
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
