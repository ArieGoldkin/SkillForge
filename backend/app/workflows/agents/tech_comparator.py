"""Tech Comparator Agent for technology comparison analysis.

This agent identifies the primary technology discussed in content and compares
it to relevant alternatives, providing pros, cons, use cases, and recommendations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.execution import run_agent_with_tracking
from app.workflows.agents.grounding import apply_grounding
from app.workflows.agents.schemas.tech_comparator import TechComparison
from app.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.workflows.state import AnalysisState
from app.workflows.utils.content_signals import get_threshold_for_expectation

# System prompt for tech comparator agent
TECH_COMPARATOR_PROMPT = """You are a Technical Comparison Specialist.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "primary_tech": "<PRIMARY TECH FROM CONTENT>",
  "alternatives": ["<ALT 1 FROM CONTENT>", "<ALT 2>", "<ALT 3>"],
  "comparison": {
    "<PRIMARY TECH>": {
      "pros": ["<ACTUAL PROS FROM CONTENT>"],
      "cons": ["<ACTUAL CONS FROM CONTENT>"],
      "use_cases": ["<ACTUAL USE CASES FROM CONTENT>"]
    }
  },
  "recommendation": "<RECOMMENDATION BASED ON CONTENT>"
}

Field Requirements:
1. **primary_tech** (REQUIRED): String - primary technology name with version (
    e.g., "LangGraph 0.6.7"
)
2. **alternatives** (REQUIRED): List of 2-3 alternative technology names with versions
3. **comparison** (REQUIRED): Dictionary mapping tech names to comparison entries
   - MUST include entry for primary_tech
   - MUST include entry for each alternative
   - Each entry: {"pros": [], "cons": [], "use_cases": []}
4. **recommendation** (REQUIRED): String with clear recommendation
5. **confidence_score** (REQUIRED): Float (0.0-1.0) - confidence in quality and certainty
   of this comparison. Consider: accuracy of identification, completeness of analysis,
   relevance of alternatives, and confidence in recommendation.

NUMERIC SPECIFICITY REQUIREMENTS:
- primary_tech MUST include version (e.g., "LangGraph 0.6.7", "React 18.2.0")
- alternatives MUST include versions (e.g., "LangChain Agents 0.1.0")
- pros MUST include quantifiable benefits (e.g., "40% faster cold start", "3x better throughput")
- cons MUST include specific limitations (
    e.g., "Max 100 concurrent executions", "No TypeScript support"
)
- use_cases MUST include scale (e.g., "Best for 10K-100K daily users", "Handles 50K+ req/sec")

FORBIDDEN VAGUE LANGUAGE - Never use:
- "better performance", "faster" (quantify: "2x faster", "150ms vs 450ms")
- "more features", "richer ecosystem" (list specific features)
- "good for most projects", "suitable for many use cases" (specify exact use cases)
- "some limitations", "a few drawbacks" (enumerate each)
- "popular choice", "widely used" (cite adoption metrics)

GOOD EXAMPLE:
  primary_tech: "LangGraph 0.6.7"
  pros: [
      "Native state persistence with PostgreSQL checkpointing",
      "Built-in retry with 3x backoff",
      "50% less boilerplate than LangChain Agents",
  ]
  cons: ["Requires Python 3.9+", "Max 256MB state size", "No native JavaScript SDK"]
  use_cases: [
      "Multi-step agentic workflows processing 1K-50K tasks/day",
      "RAG pipelines with <500ms latency requirements",
  ]

BAD EXAMPLE (DO NOT USE):
  primary_tech: "LangGraph"
  pros: ["Good performance", "Easy to use", "Popular framework"]
  cons: ["Some learning curve", "Limited documentation"]
  use_cases: ["Various AI applications", "Building agents"]

IMPORTANT: The "comparison" field must include entries for primary_tech AND all alternatives.
Do not omit any required fields. Return exactly ONE structured response/tool call; never
return multiple tool calls or extra responses.

COMPARISON STRATEGY:
- If multiple frameworks are detected (e.g., Django vs FastAPI), treat them as the primary subjects.
- Focus on "Build vs Buy" if applicable.
- Highlight "Standard vs Modern" approaches (e.g., Redux vs Zustand)."""


async def run_tech_comparator(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run tech comparator agent to analyze and compare technologies.

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
    supervisor_decision = state.get("supervisor_decision", {})
    expectation = None
    if isinstance(supervisor_decision, dict):
        agent_expectations = supervisor_decision.get("agent_expectations", {})
        if isinstance(agent_expectations, dict):
            expectation = agent_expectations.get("tech_comparator")
    specificity_threshold = get_threshold_for_expectation(expectation)

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{TECH_COMPARATOR_PROMPT}\n\n{skill_instructions}")

    # Create agent with structured output
    agent = create_structured_agent(
        system_prompt=full_prompt,
        response_schema=TechComparison,
    )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="tech_comparator",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
