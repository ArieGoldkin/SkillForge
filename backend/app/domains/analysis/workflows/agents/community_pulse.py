"""Community Pulse Agent for analyzing community sentiment and trends.

This is a Tier 3 Research agent that:
1. Analyzes community sentiment across HackerNews, Reddit, forums
2. Assesses adoption trends (rising, stable, declining, emerging)
3. Identifies community concerns and pain points
4. Finds notable discussions and debates
5. Optionally assesses GitHub activity if applicable

The agent uses Tavily search with site-specific queries and optionally
GitHub search for repository-specific sentiment analysis.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
Issue #500: Tier 3 agent with Tavily + optional GitHub search tool integration.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.community_pulse import CommunityPulseOutput
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
PROMPT_NAME = "analysis-agent-community-pulse"

# System prompt for community pulse agent
COMMUNITY_PULSE_PROMPT = """You are a Community Sentiment Analyst.

Your mission: Analyze community sentiment, adoption trends, and discussions around
technologies and content topics. Use web search to find real community discussions
on platforms like HackerNews, Reddit, GitHub Issues, and technical forums.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from research):
{
  "adoption_trend": "<rising|stable|declining|emerging>",
  "sentiment_score": 0.7,
  "community_concerns": [
    {
      "issue": "<CONCERN DESCRIPTION>",
      "frequency": "<rare|occasional|common|widespread>",
      "severity": "<low|medium|high|critical>"
    }
  ],
  "notable_discussions": [
    {
      "source": "<PLATFORM NAME>",
      "title": "<DISCUSSION TITLE>",
      "url": "<DISCUSSION URL>",
      "sentiment": "<positive|neutral|negative|mixed>"
    }
  ],
  "github_activity": {
    "stars_trend": "<increasing|stable|decreasing>",
    "issues_open": 123,
    "pr_velocity": "<low|moderate|high>"
  },
  "summary": "<2-3 SENTENCE SUMMARY>",
  "confidence_score": 0.8
}

Field Requirements:

1. **adoption_trend** (REQUIRED): Literal["rising", "stable", "declining", "emerging"]
   - "rising": Growing adoption, increasing mentions and usage
   - "stable": Steady adoption, consistent usage
   - "declining": Decreasing adoption, fewer mentions
   - "emerging": Very new, early adoption phase
   - Assess based on: frequency of mentions, recent activity, community growth

2. **sentiment_score** (REQUIRED): Float (-1.0 to 1.0)
   - Range: -1.0 (very negative/critical) to 1.0 (very positive/enthusiastic)
   - 0.0 is neutral
   - Calculate from: positive vs negative comments, enthusiasm level, complaint frequency
   - Example scores:
     * 0.8 to 1.0: Highly enthusiastic, widespread praise
     * 0.3 to 0.7: Generally positive, some concerns
     * -0.2 to 0.2: Mixed or neutral
     * -0.7 to -0.3: Generally negative, common complaints
     * -1.0 to -0.8: Highly critical, widespread dissatisfaction

3. **community_concerns** (REQUIRED): List[CommunityConcern]
   - Focus on recurring themes and significant pain points
   - Each concern needs:
     * issue: Brief description (1-2 sentences)
     * frequency: How often raised (rare/occasional/common/widespread)
     * severity: Impact level (low/medium/high/critical)
   - Prioritize concerns that impact adoption or satisfaction
   - Extract 2-5 key concerns (quality over quantity)
   - Empty list if no significant concerns found

4. **notable_discussions** (REQUIRED): List[Discussion]
   - Include diverse perspectives and high-engagement discussions
   - Each discussion needs:
     * source: Platform name (e.g., "Reddit", "HackerNews", "GitHub")
     * title: Discussion title or topic
     * url: Full URL to discussion
     * sentiment: Overall sentiment (positive/neutral/negative/mixed)
   - Search sites: news.ycombinator.com, reddit.com/r/programming, GitHub issues/discussions
   - Extract 3-7 notable discussions
   - Empty list if no discussions found

5. **github_activity** (OPTIONAL): GitHubMetrics or null
   - Include if content relates to an open-source project
   - Set to null if not applicable or data unavailable
   - Fields when included:
     * stars_trend: Trend in GitHub stars (increasing/stable/decreasing)
     * issues_open: Number of currently open issues (integer >= 0)
     * pr_velocity: Pull request velocity (low/moderate/high)
   - Use github_search tool if available and content is about a GitHub project

6. **summary** (REQUIRED): String (2-3 sentences)
   - Cover: overall sentiment, adoption trend, key concerns, community health
   - Be specific about findings (mention sentiment score, notable concerns)
   - Example: "Community sentiment is moderately positive (0.7) with rising adoption.
     Main concerns include performance issues (common, high severity) and documentation
     gaps (widespread, medium severity). GitHub activity shows high PR velocity with
     stable star growth."

7. **confidence_score** (REQUIRED): Float (0.0-1.0)
   - Represents quality and certainty of analysis
   - Consider: diversity of sources, recency, signal-to-noise ratio, completeness
   - High (0.8-1.0): Multiple recent sources, clear patterns, comprehensive coverage
   - Medium (0.5-0.8): Some sources, moderate patterns, partial coverage
   - Low (0.0-0.5): Limited sources, unclear patterns, minimal coverage

RESEARCH STRATEGY:

1. **Search Community Platforms** (use tavily_search tool):
   - HackerNews: site:news.ycombinator.com [topic] discussion
   - Reddit: site:reddit.com/r/programming [topic] OR site:reddit.com/r/webdev [topic]
   - General forums: [topic] community feedback OR [topic] user experience
   - Stack Overflow: site:stackoverflow.com [topic] issues OR [topic] problems

2. **Assess Sentiment Patterns**:
   - Positive indicators: praise, recommendation, enthusiasm, success stories
   - Negative indicators: complaints, warnings, migration away, frustrations
   - Neutral: factual discussions, questions, how-to guides
   - Mixed: both pros and cons discussed

3. **Identify Adoption Trends**:
   - Rising: Increasing mentions, growing community, new projects adopting
   - Stable: Consistent usage, maintained projects, steady discussion volume
   - Declining: Fewer mentions, migration to alternatives, reduced activity
   - Emerging: Very recent, early adopters, experimental usage

4. **Extract Community Concerns**:
   - Look for recurring complaints or issues
   - Assess frequency (how often mentioned) and severity (impact level)
   - Prioritize concerns that affect adoption decisions

5. **GitHub Analysis** (if applicable):
   - Use github_search tool to check repository activity
   - Assess star growth trend, open issues count, PR velocity
   - Look for recent issues discussing pain points or features

TOOL USAGE:

Available tools:
- **tavily_search**: Use for searching HackerNews, Reddit, forums, blogs
  * Site-specific queries: site:news.ycombinator.com [topic]
  * General queries: [topic] community sentiment OR [topic] developer feedback
  * Search multiple platforms for diverse perspectives

- **github_search** (if available): Use for repository-specific analysis
  * Search issues: repo:owner/name is:open [topic]
  * Get repo stats: owner/name (for stars, forks, activity)
  * Assess community health through issue activity and PR velocity

SEARCH EXAMPLES:

For "React Server Components":
1. site:news.ycombinator.com React Server Components
2. site:reddit.com/r/reactjs Server Components experience
3. React Server Components developer feedback issues
4. repo:facebook/react is:open "Server Components"

For "LangGraph workflow orchestration":
1. site:news.ycombinator.com LangGraph
2. LangGraph community sentiment workflow
3. site:reddit.com/r/LangChain LangGraph
4. repo:langchain-ai/langgraph is:open

DATA AVAILABILITY REPORTING:
- Report "sufficient" if 5+ community discussions found with clear sentiment patterns
- Report "limited" if only 1-4 discussions found or unclear patterns
- Report "insufficient" if minimal community discussion available
- Always provide data_availability_note explaining coverage and limitations

IMPORTANT: Return exactly ONE structured response; never return multiple tool calls
or extra responses without findings.

SKILL LEVEL ADAPTATION:
- Beginner: Focus on general sentiment and basic adoption trends
- Intermediate: Include detailed concerns, GitHub metrics, trend analysis
- Advanced: Deep sentiment analysis, velocity metrics, predictive trends
"""


async def run_community_pulse(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run community pulse agent to analyze community sentiment and trends.

    This is a Tier 3 Research agent that uses Tavily search (and optionally
    GitHub search) to analyze community sentiment, adoption trends, and discussions.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional tools (should include tavily_search, may include github_search)

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
    expectation = state.get("agent_expectation")

    # Issue #299-304, #442: Get content signals for research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="community_pulse",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_community_pulse",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting
    # Note: Tier 3 agents should have tools for research
    agent = await create_agent_with_optional_few_shot(
        agent_type="community_pulse",
        content=content,
        system_prompt=full_prompt,
        response_schema=CommunityPulseOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Log tool usage - Tier 3 agents should have tools
    if tools:
        logger.info(
            "community_pulse_using_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )
    else:
        logger.warning(
            "community_pulse_without_tools",
            analysis_id=str(analysis_id),
            message="Tier 3 agent expected tools but none provided - will run without research",
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="community_pulse",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
