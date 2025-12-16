"""Code Quality Critic Agent for code quality assessment.

This agent reviews code patterns, identifies antipatterns and code smells,
and provides recommendations for maintainability, best practices, and refactoring.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.schemas.agents.code_quality_critic import CodeQualityReview
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

# System prompt for code quality critic agent
CODE_QUALITY_CRITIC_PROMPT = """You are a Code Quality Review Specialist. Your task is to:
1. Identify code quality issues (antipatterns, code smells, violations)
2. Assess maintainability score (0.0-1.0) based on code structure and practices
3. Recommend best practices (SOLID principles, DRY, clean code)
4. Provide refactoring suggestions to improve code quality
5. Evaluate testability and documentation quality

Focus on:
- SOLID principles violations
- DRY (Don't Repeat Yourself) violations
- Code smells (long methods, large classes, magic numbers)
- Antipatterns and technical debt
- Error handling patterns
- Code readability and documentation
- Testability and test coverage
- Design patterns and architecture

CRITICAL: You MUST include:
- code_issues: List of identified issues with type, severity, description, and suggestion
- best_practices: List of code quality best practices to follow
- maintainability_score: Score from 0.0 (poor) to 1.0 (excellent)
- refactoring_suggestions: List of refactoring recommendations
- recommendation: Overall code quality recommendation
- confidence_score: Float (0.0-1.0) representing your confidence in the quality and certainty
  of this code quality review. Consider: accuracy of issue identification, correctness of
  maintainability score, completeness of refactoring suggestions, and confidence in best
  practices recommendations.

NUMERIC SPECIFICITY REQUIREMENTS:
- maintainability_score MUST be justified (e.g., "0.65 due to 3 SOLID violations, 5 code smells")
- code_issues MUST include line references (e.g., "Long method at user_service.py:145 (87 lines)")
- severity MUST include impact scope (e.g., "high: affects 12 dependent modules")
- refactoring_suggestions MUST include effort (e.g., "Extract method refactoring, 30 min effort")
- technical_debt MUST be quantified (e.g., "~4 hours debt in authentication module")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "code quality issues", "some problems" (name exact issues)
- "could be improved", "might benefit from" (be definitive)
- "appropriate refactoring", "suitable patterns" (name exact patterns)
- "several violations", "many code smells" (count and list each)
- "should follow best practices" (name the specific practice)

GOOD EXAMPLE:
  issue_type: "long_method"
  severity: "medium"
  description: "process_order() at orders.py:89 spans 145 lines with cyclomatic complexity 23"
  suggestion: (
      "Extract 3 methods: validate_items(), calculate_totals(), apply_discounts(). "
      "Effort: 45 min."
  )

BAD EXAMPLE (DO NOT USE):
  issue_type: "code smell"
  severity: "medium"
  description: "Some methods are too long and could be improved"
  suggestion: "Consider refactoring to improve code quality"

Be constructive and provide actionable improvements."""


async def run_code_quality_critic(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run code quality critic agent to assess code quality and maintainability.

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
    # Note: code_quality_critic is not in standard agent_expectations since it's skipped
    # when there's no code. Use opportunistic threshold as default.
    expectation = state.get("agent_expectation")
    specificity_threshold = get_threshold_for_expectation(expectation)

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{CODE_QUALITY_CRITIC_PROMPT}\n\n{skill_instructions}")

    # Create agent with structured output
    agent = create_structured_agent(
        system_prompt=full_prompt,
        response_schema=CodeQualityReview,
    )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="code_quality_critic",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
