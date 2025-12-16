"""Trend Validator Agent for technology trend assessment.

This agent assesses if technologies align with 2025 trends, evaluates adoption rates,
and identifies modern alternatives for legacy technologies.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.grounding import apply_grounding
from app.workflows.agents.schemas.trend_validator import TrendValidation
from app.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.workflows.state import AnalysisState
from app.workflows.utils.content_signals import get_threshold_for_expectation

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
- confidence_score: Float (0.0-1.0) representing your confidence in the quality and certainty
  of this trend validation. Consider: accuracy of trend status assessment, correctness of
  adoption rate evaluation, completeness of modern alternatives identification, and confidence
  in future outlook predictions.

NUMERIC SPECIFICITY REQUIREMENTS:
- current_adoption MUST include metrics (e.g., "45K GitHub stars", "2M weekly npm downloads")
- growth_rate MUST be quantified (e.g., "+25% YoY growth", "3x adoption since 2023")
- market_share MUST be percentage-based (e.g., "32% of Fortune 500 companies")
- job_market MUST include numbers (e.g., "15K+ job postings on LinkedIn", "$150K avg salary")
- timeline predictions MUST be specific (e.g., "EOL December 2025", "stable until 2027")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "growing popularity", "increasing adoption" (give exact growth rate)
- "many companies use", "widely adopted" (provide percentage or count)
- "good community support", "active development" (cite commit frequency, contributors)
- "may become obsolete", "might be replaced" (state timeline and alternatives)
- "trending", "popular", "mainstream" without numbers

GOOD EXAMPLE:
  technology: "React"
  trend_status: "current"
  current_adoption: "224K GitHub stars, 23M weekly npm downloads, 42% market share"
  growth_rate: "+12% YoY adoption, slowing from +25% in 2022"
  job_market: "48K open positions globally, $145K median US salary"
  future_outlook: "Stable until 2028+, Server Components adoption reaching 35% by 2026"

BAD EXAMPLE (DO NOT USE):
  technology: "React"
  trend_status: "current"
  current_adoption: "Very popular among developers"
  growth_rate: "Still growing"
  job_market: "Many job opportunities available"
  future_outlook: "Should remain relevant for the foreseeable future"

Base assessments on current 2025 data and industry trends.

Return exactly ONE structured response/tool call. Do NOT return multiple tool
calls or additional responses."""


async def run_trend_validator(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run trend validator agent to assess technology trends and adoption.

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

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Issue #299-304: Get content-aware specificity threshold
    # Read from flat field injected by build_scoped_context()
    expectation = state.get("agent_expectation")
    specificity_threshold = get_threshold_for_expectation(expectation)

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{TREND_VALIDATOR_PROMPT}\n\n{skill_instructions}")

    # Create agent with structured output
    agent = create_structured_agent(
        system_prompt=full_prompt,
        response_schema=TrendValidation,
    )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="trend_validator",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
