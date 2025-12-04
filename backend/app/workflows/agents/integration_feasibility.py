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

5. **confidence_score** (REQUIRED): Float (0.0-1.0) - confidence in quality and certainty
   of this integration analysis. Consider: accuracy of compatibility scores, correctness
   of migration effort assessment, completeness of breaking changes, and confidence in
   integration steps.

NUMERIC SPECIFICITY REQUIREMENTS:
- compatibility score MUST be a specific decimal (e.g., 0.85, not "good")
- notes MUST include specific version requirements (e.g., "Requires React >= 18.0.0")
- breaking_changes MUST include version numbers (e.g., "API v2 removes deprecated /users endpoint")
- integration_steps MUST include time estimates (e.g., "Step 1 (15 min): Install SDK v2.0.0")
- migration_effort justification MUST cite specific changes (
    e.g., "medium: 3 API changes, 2 schema migrations"
)

FORBIDDEN VAGUE LANGUAGE - Never use:
- "generally compatible", "mostly works" (give exact score)
- "some breaking changes", "a few issues" (list each one)
- "appropriate configuration", "suitable setup" (specify exact config)
- "should work", "might integrate" (be definitive)
- "various steps", "several changes" (enumerate exactly)

GOOD EXAMPLE:
  compatibility: {
      "react": {"score": 0.92, "notes": "Full support with React 18.2.0+, uses Suspense"}
  }
  migration_effort: "medium"
  breaking_change: (
      "v3.0 removes legacy REST API - migrate to GraphQL, affects /api/users, /api/posts"
  )
  integration_step: "Step 1 (30 min): Update package.json with @sdk/core@3.0.0, @sdk/react@3.0.0"

BAD EXAMPLE (DO NOT USE):
  compatibility: {"react": {"score": 0.9, "notes": "Compatible"}}
  migration_effort: "medium"
  breaking_change: "Some API changes"
  integration_step: "Update dependencies"

IMPORTANT: Include the "compatibility" field with at least 2 stack entries.
Do not omit any required fields."""


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
