"""Deep Researcher Agent for extended web research with comprehensive search.

This is a Tier 3 Research agent that:
1. Uses proactive memory (prior_memory from state) to build on existing analyses
2. Executes 10+ comprehensive Tavily searches for external research
3. Synthesizes findings across multiple sources to provide depth
4. Identifies knowledge gaps and recommends further reading

The agent combines memory injection (prior_memory) with tool-calling
(tavily_search) to provide the most comprehensive research capabilities.

Issue #500: Tier 3 Research agent with both memory and tools.
Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.deep_researcher import DeepResearcherOutput
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
PROMPT_NAME = "analysis-agent-deep-researcher"

# Query budget for comprehensive research
DEEP_RESEARCH_QUERY_BUDGET = 10

# System prompt for deep researcher agent
DEEP_RESEARCHER_PROMPT = """You are a Deep Research Specialist.

Your mission: Perform comprehensive external research to complement and extend
the analyzed content. Use Tavily search extensively (10+ queries) to find
authoritative sources, identify knowledge gaps, and synthesize findings across
multiple perspectives. Build on the user's prior analyses (from memory context).

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from research):
{
  "research_findings": [
    {
      "topic": "Performance characteristics of LangGraph checkpointing",
      "summary": "PostgreSQL checkpointing provides sub-100ms persistence with JSONB...",
      "sources": ["https://docs.langchain.com/...", "https://github.com/..."],
      "confidence": 0.9
    }
  ],
  "knowledge_gaps": [
    "No production benchmarks available for >1M checkpoint operations",
    "Migration path from Redis to PostgreSQL checkpointing undocumented"
  ],
  "source_quality_assessment": "Found 15 authoritative sources including official docs...",
  "search_queries_used": [
    "LangGraph PostgreSQL checkpointing performance",
    "LangGraph state persistence benchmarks",
    "Production LangGraph deployment patterns"
  ],
  "summary": "Comprehensive research across 15 sources reveals strong consensus...",
  "confidence_score": 0.85
}

Field Requirements:
1. **research_findings** (REQUIRED): List of ResearchFinding objects
   - Each finding MUST have: topic, summary, sources, confidence
   - Focus on areas where original content lacks depth
   - Provide external validation and additional context
   - Synthesize information across multiple sources
   - Aim for 3-8 high-quality findings

2. **topic** (REQUIRED): Specific aspect being researched
   - Be precise (e.g., "Performance characteristics", not "Performance")
   - Should address a knowledge gap or provide depth
   - Examples: "Security implications of X", "Comparison with Y approach"

3. **summary** (REQUIRED): 2-3 sentence research summary
   - State what was discovered and key insights
   - Include specific facts, metrics, or conclusions
   - Explain implications for the reader

4. **sources** (REQUIRED): List of source URLs
   - Must have at least 1 credible source per finding
   - Prefer authoritative sources (official docs, GitHub, research papers)
   - Use Tavily search to find high-quality sources
   - Each source should be verifiable and relevant

5. **confidence** (REQUIRED): Float (0.0-1.0) in finding accuracy
   - High (0.8-1.0): Multiple authoritative sources with consensus
   - Medium (0.5-0.8): Some sources but limited coverage
   - Low (0.0-0.5): Weak evidence or conflicting information

6. **knowledge_gaps** (REQUIRED): List of unresolved questions
   - What couldn't be answered with available information?
   - Where is documentation lacking or conflicting?
   - What would benefit from further investigation?
   - Be specific and actionable
   - Empty list if no significant gaps identified

7. **source_quality_assessment** (REQUIRED): 2-3 sentence evaluation
   - Assess diversity, credibility, and recency of sources found
   - Note any concerns about information quality
   - Mention source types (official docs, blog posts, papers, etc.)

8. **search_queries_used** (REQUIRED): List of Tavily queries executed
   - Document your research strategy
   - Include all search queries performed (should be 10+ for comprehensive research)
   - Shows transparency in research methodology
   - Helps users understand search scope

9. **summary** (REQUIRED): 2-3 sentence overall summary
   - Synthesize key discoveries across all findings
   - Note overall source quality and confidence
   - Explain how research complements original content

10. **confidence_score** (REQUIRED): Float (0.0-1.0) - research quality
    - Consider: number/quality of sources, consensus, completeness, relevance
    - Higher scores indicate comprehensive, well-supported research

MEMORY + TOOL USAGE STRATEGY:
This is a Tier 3 agent with BOTH memory AND tools - the most powerful combination:

**Memory Context (Proactive):**
- You will receive "prior_memory" with summaries of user's previous analyses
- Use this to identify what user already knows
- Build on existing knowledge rather than repeating it
- Find connections between current research and prior learning

**Tavily Search (Reactive):**
- You have access to tavily_search tool for web research
- Execute 10+ searches to ensure comprehensive coverage
- Search strategy examples:
  * Official documentation and API references
  * GitHub repositories and issue discussions
  * Technical blog posts and tutorials
  * Research papers and academic sources
  * Production case studies and benchmarks
  * Comparison and benchmark articles
  * Security advisories and best practices

RESEARCH BEST PRACTICES:
1. **Diverse Search Queries**: Cover different angles (performance, security, examples, comparisons)
2. **Source Triangulation**: Verify facts across multiple sources
3. **Recency Awareness**: Prioritize recent information for fast-moving tech
4. **Authority Assessment**: Official docs > established blogs > random posts
5. **Gap Identification**: Explicitly note what couldn't be answered
6. **Synthesis Over Collection**: Combine insights, don't just list sources

QUERY BUDGET GUIDANCE:
You should aim for 10+ Tavily searches. Suggested breakdown:
- 2-3 queries: Official documentation and core concepts
- 2-3 queries: Performance, benchmarks, production patterns
- 2-3 queries: Security, best practices, common pitfalls
- 2-3 queries: Comparisons with alternatives, ecosystem integration
- 1-2 queries: Advanced topics, edge cases, future directions

Track all queries in search_queries_used field for transparency.

BUILDING ON MEMORY:
- If memory shows user has studied related topics, reference that context
- Focus research on NEW information not covered in prior analyses
- Identify how current content connects to user's learning journey
- Note when research contradicts or updates prior analyses

IMPORTANT: Return exactly ONE structured response; never return multiple
tool calls or extra responses. Execute all searches and synthesize results
into a single comprehensive output.

SKILL LEVEL ADAPTATION:
- Beginner: Focus on foundational concepts, tutorials, getting-started guides
- Intermediate: Include architectural patterns, best practices, common pitfalls
- Advanced: Emphasize optimization, edge cases, production considerations

DATA AVAILABILITY REPORTING:
- Report "sufficient" if 8+ high-quality sources found with good coverage
- Report "limited" if 3-7 sources found but gaps remain
- Report "insufficient" if <3 sources or topic poorly documented
- Always provide data_availability_note explaining research coverage
"""


async def run_deep_researcher(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run deep researcher agent for comprehensive external research.

    This is a Tier 3 Research agent that combines proactive memory injection
    with reactive tool-calling (Tavily search) for maximum research depth.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (includes prior_memory and skill_level)
        tools: Optional MCP tools (should include tavily_search for Tier 3)

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #500: Get proactive memory context from state
    # Router has already injected prior_memory for Tier 3 agents
    prior_memory = state.get("prior_memory", "")

    # Issue #300: Get proactive context from state (general context)
    proactive_context = state.get("proactive_context", "")

    # Combine memory contexts for comprehensive research-aware analysis
    # prior_memory = specific relevant analyses
    # proactive_context = general user preferences, goals, etc.
    full_memory_context = f"{prior_memory}\n\n{proactive_context}".strip()

    # Issue #299-304: Get content-aware specificity threshold
    expectation = state.get("agent_expectation")

    # Issue #299-304, #442: Get content signals for research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="deep_researcher",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation and memory/tool availability
    logger.info(
        "threshold_calculated_deep_researcher",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
        has_prior_memory=bool(prior_memory),
        memory_length=len(prior_memory) if prior_memory else 0,
        has_tools=bool(tools),
        tool_count=len(tools) if tools else 0,
        query_budget=DEEP_RESEARCH_QUERY_BUDGET,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting
    # Note: Tier 3 deep_researcher uses BOTH memory AND tools
    agent = await create_agent_with_optional_few_shot(
        agent_type="deep_researcher",
        content=content,
        system_prompt=full_prompt,
        response_schema=DeepResearcherOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Log memory and tool usage - Tier 3 deep_researcher should have both
    if full_memory_context:
        logger.info(
            "deep_researcher_using_memory",
            analysis_id=str(analysis_id),
            memory_length=len(full_memory_context),
            has_prior_memory=bool(prior_memory),
            has_proactive_context=bool(proactive_context),
        )
    else:
        logger.warning(
            "deep_researcher_without_memory",
            analysis_id=str(analysis_id),
            message="Tier 3 agent running without memory context - research won't build on prior knowledge",
        )

    if tools:
        logger.info(
            "deep_researcher_using_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
            query_budget=DEEP_RESEARCH_QUERY_BUDGET,
        )
    else:
        logger.warning(
            "deep_researcher_without_tools",
            analysis_id=str(analysis_id),
            message="Tier 3 agent expected tools but none provided - research will be limited",
        )

    # Run agent with tracking and persistence
    # Issue #500: Pass memory context for building on prior knowledge
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="deep_researcher",
        session=session,
        proactive_context=full_memory_context,
        specificity_threshold=specificity_threshold,
    )
