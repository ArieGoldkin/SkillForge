"""Tech Comparator Agent for technology comparison analysis.

This agent identifies the primary technology discussed in content and compares
it to relevant alternatives, providing pros, cons, use cases, and recommendations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas.tech_comparator import TechComparison

# System prompt for tech comparator agent
TECH_COMPARATOR_PROMPT = """You are a Technical Comparison Specialist. Your task is to:
1. Identify the primary technology/framework discussed in the content
2. Compare it to 2-3 relevant alternatives that serve similar purposes
3. Create a structured comparison table with pros, cons, and use cases for each technology
4. Provide a clear recommendation based on the comparison

CRITICAL: You MUST include a "comparison" field with entries for:
- The primary technology (identified in step 1)
- Each alternative technology (from step 2)
Each comparison entry must contain: pros (list), cons (list), and use_cases (list).

Focus on:
- Technical capabilities and features
- Performance characteristics
- Ecosystem and community support
- Learning curve and developer experience
- Use case suitability

Be objective and provide balanced comparisons."""


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
