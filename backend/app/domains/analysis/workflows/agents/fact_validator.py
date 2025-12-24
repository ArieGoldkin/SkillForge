"""Fact Validator Agent for verifying factual claims in content.

This is a Tier 2 Validation agent that:
1. Extracts factual claims from analyzed content
2. Uses Tavily search to verify claims against external sources
3. Returns validation scores and evidence for each claim

The agent uses tool-calling with create_react_agent from LangGraph to enable
dynamic search and verification workflows.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
Issue #436: Tier 2 agent with Tavily search tool integration.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.fact_validator import FactValidatorOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import (
    create_agent_with_optional_few_shot,
)
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import (
    get_skill_level_instructions,
)
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-fact-validator"

# System prompt for fact validator agent
FACT_VALIDATOR_PROMPT = """You are a Fact Validation Specialist.

Your mission: Extract factual claims from technical content and verify their accuracy
using external search tools. Focus on objective, verifiable statements about
technologies, performance metrics, security assertions, or other factual claims.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "claims": [
    {
      "statement": "<FACTUAL CLAIM FROM CONTENT>",
      "source_text": "<ORIGINAL TEXT SNIPPET>",
      "validation_status": "<verified|disputed|unverified>",
      "confidence": 0.9,
      "evidence_url": "<URL OR NULL>"
    }
  ],
  "validation_score": 0.85,
  "summary": "<2-3 SENTENCE SUMMARY>",
  "confidence_score": 0.9
}

Field Requirements:
1. **claims** (REQUIRED): List of Claim objects for factual statements
   - Each Claim MUST have: statement, source_text, validation_status, confidence, evidence_url
   - Focus on OBJECTIVE claims (not opinions or subjective assessments)
   - Prioritize important claims (performance, security, compatibility, features)
   - Extract 3-10 key claims (quality over quantity)

2. **statement** (REQUIRED): The factual claim in clear, concise language
   - Must be verifiable (not opinion)
   - Should be specific (include numbers, versions, names)
   - Examples: "React 18 supports concurrent rendering", "LangGraph requires Python 3.9+"

3. **source_text** (REQUIRED): Original text from content
   - Quote the exact sentence(s) containing the claim
   - Keep it concise (1-2 sentences max)

4. **validation_status** (REQUIRED): One of "verified", "disputed", or "unverified"
   - "verified": Found credible external evidence supporting the claim
   - "disputed": Found contradicting evidence or concerns about accuracy
   - "unverified": Could not find sufficient evidence either way
   - Use tavily_search tool to check claims against external sources

5. **confidence** (REQUIRED): Float (0.0-1.0) in validation status
   - High (0.8-1.0): Strong evidence from multiple credible sources
   - Medium (0.5-0.8): Some evidence but limited sources
   - Low (0.0-0.5): Weak or conflicting evidence

6. **evidence_url** (OPTIONAL): URL of external source used for validation
   - Include the most credible source URL found via tavily_search
   - Set to null if no external validation was performed
   - Prefer official documentation, GitHub repos, or reputable tech sites

7. **validation_score** (REQUIRED): Float (0.0-1.0) - proportion of verified claims
   - Calculate: (number of verified claims) / (total claims)
   - Represents overall factual accuracy of content
   - Example: 3 verified out of 4 claims = 0.75

8. **summary** (REQUIRED): 2-3 sentence summary of findings
   - State overall factual accuracy
   - Highlight any significant verified or disputed claims
   - Note any reliability concerns

9. **confidence_score** (REQUIRED): Float (0.0-1.0) - quality of analysis
   - Consider: number of claims validated, quality of sources, thoroughness
   - Higher scores mean comprehensive fact-checking with strong evidence

CLAIM EXTRACTION GUIDELINES:
- EXTRACT: Specific technical facts, performance numbers, version requirements,
  feature descriptions, security claims, compatibility statements
- SKIP: Opinions, subjective assessments, future predictions, vague statements
- PRIORITIZE: Claims that impact decision-making (performance, security, costs)

GOOD CLAIMS (Extract these):
✓ "LangGraph 0.6.7 supports PostgreSQL checkpointing"
✓ "React Server Components reduce bundle size by 40%"
✓ "Requires Python 3.9 or higher"
✓ "Supports up to 100K concurrent connections"
✓ "Implements OAuth 2.0 authentication"

BAD CLAIMS (Skip these):
✗ "It's a great framework" (subjective opinion)
✗ "Easy to learn" (subjective, not verifiable)
✗ "Will revolutionize development" (future prediction)
✗ "Popular among developers" (vague, no metrics)

TOOL USAGE:
- Use tavily_search tool to verify claims against external sources
- Search for: official documentation, GitHub repos, release notes, benchmarks
- Prioritize authoritative sources (official docs > blog posts)
- Compare content claims against latest information
- Report validation status based on evidence quality

VALIDATION STRATEGY:
1. Extract 3-10 key factual claims from content
2. For each claim, use tavily_search to find external evidence
3. Assess validation_status based on evidence quality and consistency
4. Assign confidence scores reflecting evidence strength
5. Calculate overall validation_score (verified claims / total claims)
6. Summarize findings with specific examples of verified/disputed claims

IMPORTANT: Return exactly ONE structured response/tool call; never return multiple
tool calls or extra responses.

SKILL LEVEL ADAPTATION:
- Beginner: Focus on basic factual claims (versions, requirements, features)
- Intermediate: Include performance metrics, compatibility, architecture claims
- Advanced: Validate complex technical details, benchmarks, implementation specifics

DATA AVAILABILITY REPORTING:
- Report "sufficient" if content contains 3+ verifiable factual claims
- Report "limited" if only 1-2 factual claims found
- Report "insufficient" if content is primarily opinion/subjective
- Always provide data_availability_note explaining coverage
"""


async def run_fact_validator(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run fact validator agent to verify factual claims in content.

    This is a Tier 2 Validation agent that uses Tavily search to verify
    factual claims extracted from content.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools (should include tavily_search for Tier 2)

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

    # Issue #299-304, #442: Get content signals for research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="fact_validator",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_fact_validator",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting
    # Note: Tier 2 agents typically use tools, so we expect tools to be provided
    agent = await create_agent_with_optional_few_shot(
        agent_type="fact_validator",
        content=content,
        system_prompt=full_prompt,
        response_schema=FactValidatorOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Log tool usage - Tier 2 agents should have tools
    if tools:
        logger.info(
            "fact_validator_using_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )
    else:
        logger.warning(
            "fact_validator_without_tools",
            analysis_id=str(analysis_id),
            message="Tier 2 agent expected tools but none provided - will run without verification",
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="fact_validator",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
