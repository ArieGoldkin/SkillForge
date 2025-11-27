"""Trend Validator Agent for technology trend assessment.

This agent assesses if technologies align with 2025 trends, evaluates adoption rates,
and identifies modern alternatives for legacy technologies.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent, run_agent_with_tracking
from app.workflows.agents.schemas.trend_validator import TrendValidation

# System prompt for trend validator agent
TREND_VALIDATOR_PROMPT = """You are a Technology Trend Analyst. Your task is to:
1. Assess technology trends in the 2025 landscape
2. Evaluate adoption rates and community activity
3. Identify if technologies are emerging, current, stable, declining, or legacy
4. Provide modern alternatives for outdated technologies
5. Predict future outlook and sustainability

Focus on:
- 2025 technology trends and industry standards
- GitHub stars, npm/pip downloads, community activity
- Official support status and maintenance
- Industry adoption and job market trends
- Modern alternatives and migration paths
- Future-proofing considerations
- Ecosystem maturity and stability

CRITICAL: You MUST include:
- trend_assessments: List of assessments for different aspects (framework, language, pattern, tool)
- modern_alternatives: List of modern alternatives if technology is legacy/declining
- future_outlook: Future predictions and sustainability assessment
- recommendation: Recommendation based on trend analysis

Base assessments on current 2025 data and industry trends."""


async def run_trend_validator(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
) -> dict[str, object]:
    """Run trend validator agent to assess technology trends and adoption.

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
        system_prompt=TREND_VALIDATOR_PROMPT,
        response_schema=TrendValidation,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="trend_validator",
        session=session,
    )
