"""Key Insights Agent for extracting critical takeaways from any content type.

This is a Tier 1 agent that runs on ALL content types (article, video, repo, news).
It identifies the most important insights, learnings, and actionable takeaways
regardless of content format or domain.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.key_insights import KeyInsightsOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import (
    create_agent_with_optional_few_shot,
)
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-key-insights"

# System prompt for key insights agent
KEY_INSIGHTS_PROMPT = """You are a Key Insights Extraction Specialist.

Your mission: Extract the 3-5 MOST IMPORTANT takeaways from ANY type of content
(article, video, repo, news) that would help a learner or implementer succeed.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "insights": [
    {
      "title": "<SPECIFIC INSIGHT TITLE>",
      "description": "<DETAILED EXPLANATION WITH CONTEXT>",
      "importance": "high",
      "novelty_score": 0.8
    }
  ],
  "summary": "<2-3 SENTENCE SYNTHESIS>",
  "confidence_score": 0.85
}

Field Requirements:
1. **insights** (REQUIRED): List of 3-5 KeyInsight objects, each containing:
   - title: Specific, actionable title (5-10 words)
   - description: Evidence-based explanation (2-4 sentences)
   - importance: "high", "medium", or "low"
   - novelty_score: Float 0.0-1.0 (how unexpected/unique)
2. **summary** (REQUIRED): 2-3 sentence synthesis connecting insights to application
3. **confidence_score** (REQUIRED): Float 0.0-1.0 - confidence in insight quality

INSIGHT EXTRACTION RULES:

1. PRIORITIZE ACTIONABLE INSIGHTS
   - Prefer: "Use Redis caching to reduce API calls by 70% (benchmark: 100ms vs 300ms)"
   - Avoid: "Caching is important for performance"

2. QUANTIFY WHEN POSSIBLE
   - Include metrics, percentages, time savings, cost reductions
   - Cite specific examples or case studies from content
   - Reference concrete numbers, versions, benchmarks

3. IMPORTANCE LEVELS
   - HIGH: Changes how you build/think, critical trade-offs, major risks
   - MEDIUM: Improves quality/efficiency, useful patterns, good practices
   - LOW: Minor optimizations, nice-to-know details, optional enhancements

4. NOVELTY SCORING
   - 0.9-1.0: Counter-intuitive findings, breakthrough techniques
   - 0.7-0.8: Fresh perspectives, non-obvious solutions
   - 0.4-0.6: Useful clarifications, solid best practices
   - 0.0-0.3: Common knowledge, standard approaches

5. EVIDENCE-BASED EXTRACTION
   - Quote specific statements, code examples, or data from content
   - Link insights to source sections (e.g., "In Section 3, author demonstrates...")
   - Never hallucinate or add external knowledge not in content

6. CONTENT-TYPE AWARENESS
   - Article: Extract main arguments, case studies, recommendations
   - Video: Focus on demos, walkthroughs, expert commentary
   - Repo: Highlight architecture decisions, code patterns, trade-offs
   - News: Emphasize impact, trends, actionable implications

GOOD EXAMPLE:
{
  "insights": [
    {
      "title": "LangGraph reduces agent orchestration code by 50%",
      "description": "Author's case study shows 200 lines of custom LangChain code replaced by 100 lines of LangGraph StateGraph. Key benefit: built-in checkpointing eliminates manual state management. Applicable to multi-step agentic workflows processing 1K-50K tasks/day.",
      "importance": "high",
      "novelty_score": 0.75
    },
    {
      "title": "PostgreSQL checkpointer handles 10K concurrent agents",
      "description": "Benchmark in Section 4 demonstrates PostgreSQL checkpointing scales to 10,000 concurrent LangGraph agents with <100ms state persistence. Critical for production deployments. Requires connection pooling (100-500 connections) and proper indexing on checkpoint tables.",
      "importance": "high",
      "novelty_score": 0.65
    },
    {
      "title": "StateGraph's conditional edges prevent infinite loops",
      "description": "Unlike traditional agent loops, LangGraph's conditional edges provide explicit exit conditions. Author shows how this prevents runaway tool calling (Section 5 example: max 10 iterations). Reduces debugging time by 30% in production.",
      "importance": "medium",
      "novelty_score": 0.55
    }
  ],
  "summary": "LangGraph significantly simplifies multi-agent orchestration through built-in state management and conditional flow control. Key advantage is production scalability with PostgreSQL checkpointing handling 10K+ concurrent agents. These patterns reduce boilerplate by 50% while improving reliability.",
  "confidence_score": 0.85
}

BAD EXAMPLE (DO NOT USE):
{
  "insights": [
    {
      "title": "LangGraph is good",
      "description": "It's a useful framework",
      "importance": "high",
      "novelty_score": 0.5
    }
  ],
  "summary": "LangGraph is recommended",
  "confidence_score": 0.7
}

FORBIDDEN PATTERNS - Never use:
- Generic titles: "Important concept", "Key feature", "Good practice"
- Vague descriptions: "Helps with performance", "Makes things easier"
- No evidence: Insights not grounded in actual content
- Missing metrics: "Faster", "better", "more efficient" without numbers
- Hallucinated details: Adding information not present in content

CONTENT-AGNOSTIC EXTRACTION:
This agent must work on ANY content type. Adapt extraction strategy:
- Technical content: Focus on implementation details, architecture, trade-offs
- Conceptual content: Extract mental models, frameworks, decision criteria
- News content: Highlight impact, trends, actionable implications
- Tutorial content: Capture critical steps, gotchas, best practices

IMPORTANT: Return exactly ONE structured response. Do not return multiple tool calls
or extra responses. All insights must be directly extracted from provided content."""


async def run_key_insights(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run key insights agent to extract critical takeaways from content.

    This is a Tier 1 agent that runs on ALL content types. It identifies the most
    important insights regardless of content format (article, video, repo, news).

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo, news)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools (Tier 1 agents typically don't use tools)

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
        agent_name="key_insights",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation (Issue #299-304, #442)
    logger.info(
        "threshold_calculated_key_insights",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    # Issue #564: Use get_prompt_with_langfuse_client() for prompt observation linkage
    prompt_manager = get_prompt_manager()
    base_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        PROMPT_NAME
    )

    # Build prompt with skill level instructions and grounding
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent with optional few-shot prompting (Phase 1, Week 2.3)
    # Tier 1 agents typically don't use tools, but we support them for flexibility
    agent = await create_agent_with_optional_few_shot(
        agent_type="key_insights",
        content=content,
        system_prompt=full_prompt,
        response_schema=KeyInsightsOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    if tools:
        logger.info(
            "key_insights_using_mcp_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="key_insights",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
