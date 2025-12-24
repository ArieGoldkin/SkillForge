"""Alternatives Finder Agent for identifying competitive alternatives.

This Tier 2 Validation agent identifies technologies/tools mentioned in content,
uses Tavily search to find alternatives/competitors, and returns ranked alternatives
with comparison notes.

Issue #436: MCP tool integration for all agents.
Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.alternatives_finder import AlternativesFinderOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import create_agent_with_optional_few_shot
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-alternatives-finder"

# System prompt for alternatives finder agent
ALTERNATIVES_FINDER_PROMPT = """You are an Alternatives Discovery Specialist.

Your mission: Identify the main technology/tool/framework discussed in the content,
then use available search tools to find and compare viable alternatives/competitors.
Provide ranked alternatives with accurate comparison notes.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "subject": "React 19",
  "alternatives": [
    {
      "name": "Vue.js 3.x",
      "description": "Progressive JavaScript framework with approachable learning curve and composition API",
      "comparison_notes": "Easier to learn than React, smaller bundle size (25KB vs 45KB gzipped). Less extensive ecosystem but official routing/state solutions included. Better for mid-size teams.",
      "relevance_score": 0.9,
      "url": "https://vuejs.org/"
    }
  ],
  "recommendation": "React 19 remains best for large-scale SPAs. Consider Vue 3 for faster onboarding or Svelte 5 for minimal bundle size.",
  "confidence_score": 0.85
}

Field Requirements:
1. **subject** (REQUIRED): Main technology/tool/framework discussed in content
   - Be specific with version numbers (e.g., "FastAPI 0.104.x", "LangGraph 0.6.x")
   - Extract from content analysis - what is the primary technology being taught/discussed?
   - Examples: "React 19", "PostgreSQL 15", "LangGraph multi-agent workflows"

2. **alternatives** (REQUIRED): List of 3-7 Alternative objects ranked by relevance_score
   - Each Alternative MUST have: name, description, comparison_notes, relevance_score, url (or None)
   - Start with alternatives mentioned in content, then search for current options
   - Include direct competitors (high relevance) and adjacent solutions (medium relevance)
   - Each alternative should offer distinct value proposition or tradeoffs

3. **recommendation** (REQUIRED): 3-4 sentence guidance on when to use alternatives
   - Synthesize comparison notes into actionable advice
   - Consider use case alignment, maturity, ecosystem, learning curve
   - Example: "React 19 remains best for large SPAs with complex state management. Consider Svelte 5 if bundle size is critical (<50KB budget) or Vue 3 for faster team onboarding (2-3 weeks vs 4-6 weeks). For static sites, explore Astro with React islands."

4. **confidence_score** (REQUIRED): Float (0.0-1.0) - quality of alternatives analysis
   - Consider: accuracy of subject ID, relevance of alternatives, quality of comparisons
   - Score 0.8+ means all alternatives are highly relevant with accurate, research-backed comparisons

TOOL USAGE - TAVILY SEARCH:
You have access to **tavily_search** tool for finding current alternatives and verifying information.

Best practices:
- Use Tavily to search for: "alternatives to [subject]", "competitors to [subject]", "[subject] vs [alternative]"
- Example queries: "alternatives to React 19 frontend frameworks", "LangGraph competitors multi-agent", "FastAPI vs Flask vs Starlette"
- Verify version numbers, release dates, and current adoption trends
- Check official documentation URLs when available
- Use search results to inform comparison_notes with specific metrics

SPECIFICITY REQUIREMENTS:
- Alternatives MUST be real, currently maintained technologies (not vaporware)
- comparison_notes MUST include specific differences (performance, size, API, ecosystem)
- Include quantifiable metrics when available (bundle size, GitHub stars, npm downloads)
- relevance_score should reflect similarity of use cases and feature sets
- URLs should point to official documentation or main websites (not random blog posts)

GOOD EXAMPLE:
  subject: "React 19"
  alternatives: [
    {
      name: "Vue.js 3.x",
      description: "Progressive JavaScript framework with approachable learning curve and composition API for reactive UIs",
      comparison_notes: "Easier learning curve (2-3 weeks vs 4-6 weeks), smaller bundle size (25KB vs 45KB gzipped), official routing/state solutions included. Less extensive third-party ecosystem but growing rapidly. Better DX for mid-size teams.",
      relevance_score: 0.9,
      url: "https://vuejs.org/"
    },
    {
      name: "Svelte 5",
      description: "Compiler-based framework that shifts work to build time, resulting in minimal runtime overhead",
      comparison_notes: "Smallest bundle size (15KB vs 45KB for React), no virtual DOM overhead, built-in state management via stores. Smaller ecosystem and fewer enterprise adoptions. Ideal for performance-critical apps.",
      relevance_score: 0.85,
      url: "https://svelte.dev/"
    }
  ]
  recommendation: "React 19 remains the industry standard for large-scale SPAs with complex state management and extensive third-party integrations. Consider Vue 3 if team onboarding speed and DX are priorities, or Svelte 5 for performance-critical applications with strict bundle size budgets. For static sites with occasional interactivity, explore Astro with React islands for optimal performance."
  confidence_score: 0.9

BAD EXAMPLE (DO NOT USE):
  subject: "Some framework"
  alternatives: [
    {
      name: "Alternative X",
      description: "It's also good",
      comparison_notes: "Better in some ways, worse in others",
      relevance_score: 0.5,
      url: None
    }
  ]
  recommendation: "Try alternatives if you want something different."
  confidence_score: 0.3

CONTENT-TYPE SPECIFIC GUIDANCE:
- **Articles comparing tech**: Extract mentioned alternatives first, then search for missing ones
- **Single-tech tutorials**: Use Tavily to find competitive alternatives, rank by market share
- **Documentation**: Identify the subject clearly, search for "alternatives to X" and "X vs Y"
- **Research papers**: Look for related work section, search for current implementations

RANKING STRATEGY:
- relevance_score 0.9-1.0: Direct competitors, similar features/use cases, drop-in alternatives
- relevance_score 0.7-0.9: Strong alternatives with different tradeoffs (perf vs DX, size vs ecosystem)
- relevance_score 0.5-0.7: Adjacent solutions for similar problems (different paradigm/approach)
- relevance_score < 0.5: Niche/specialized options or loosely related technologies

IMPORTANT: Return exactly ONE structured response/tool call; never return multiple
tool calls or extra responses.

SKILL LEVEL ADAPTATION:
- Beginner: Emphasize ease of learning, onboarding time, official documentation quality
- Intermediate: Balance ecosystem maturity, performance, and DX tradeoffs
- Advanced: Focus on architectural differences, optimization potential, edge cases
"""


async def run_alternatives_finder(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run alternatives finder agent to identify and compare technology alternatives.

    This is a Tier 2 Validation agent that uses Tavily search to find alternatives
    and competitors to technologies mentioned in the content.

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

    # Issue #299-304, #442: Get content signals for comparison/research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    # Issue #442: Detect research/conceptual content for very low thresholds
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="alternatives_finder",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_alternatives_finder",
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
    # Tier 2 agents should receive tools (tavily_search)
    agent = await create_agent_with_optional_few_shot(
        agent_type="alternatives_finder",
        content=content,
        system_prompt=full_prompt,
        response_schema=AlternativesFinderOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Log MCP tool usage if tools are provided
    if tools:
        logger.info(
            "alternatives_finder_using_mcp_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )
    else:
        logger.warning(
            "alternatives_finder_no_tools",
            analysis_id=str(analysis_id),
            message="Tier 2 agent running without tools - search capabilities limited",
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="alternatives_finder",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
