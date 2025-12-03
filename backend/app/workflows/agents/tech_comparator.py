"""Tech Comparator Agent for technology comparison analysis.

This agent identifies the primary technology discussed in content and compares
it to relevant alternatives, providing pros, cons, use cases, and recommendations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.schemas.tech_comparator import TechComparison

# System prompt for tech comparator agent
TECH_COMPARATOR_PROMPT = """You are a Technical Comparison Specialist.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure:
{
  "primary_tech": "LangGraph",
  "alternatives": ["LangChain Agents", "Temporal", "Ray"],
  "comparison": {
    "LangGraph": {
      "pros": ["Pros list"],
      "cons": ["Cons list"],
      "use_cases": ["Use cases list"]
    },
    "LangChain Agents": {
      "pros": ["Pros list"],
      "cons": ["Cons list"],
      "use_cases": ["Use cases list"]
    }
  },
  "recommendation": "Clear recommendation text"
}

Field Requirements:
1. **primary_tech** (REQUIRED): String - primary technology name
2. **alternatives** (REQUIRED): List of 2-3 alternative technology names
3. **comparison** (REQUIRED): Dictionary mapping tech names to comparison entries
   - MUST include entry for primary_tech
   - MUST include entry for each alternative
   - Each entry: {"pros": [], "cons": [], "use_cases": []}
4. **recommendation** (REQUIRED): String with clear recommendation
5. **confidence_score** (REQUIRED): Float (0.0-1.0) - confidence in quality and certainty
   of this comparison. Consider: accuracy of identification, completeness of analysis,
   relevance of alternatives, and confidence in recommendation.

IMPORTANT: The "comparison" field must include entries for primary_tech AND "
    "all alternatives. Do not omit any required fields."""


async def run_tech_comparator(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> dict[str, object]:
    """Run tech comparator agent to analyze and compare technologies.

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
        system_prompt=TECH_COMPARATOR_PROMPT,
        response_schema=TechComparison,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        session=session,
    )
