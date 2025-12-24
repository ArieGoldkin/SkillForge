"""Actionable Agent for extracting concrete next steps and learning resources.

This universal agent (Tier 1) analyzes any content type to extract:
- Immediate actions (1-3 quick wins to do now)
- Follow-up actions (up to 5 deeper learning/implementation steps)
- Resources (documentation, tutorials, tools)
- Quick win (single highest-impact 30-minute action)

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.actionable import ActionableOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import create_agent_with_optional_few_shot
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-actionable"

# System prompt for actionable agent (content-agnostic)
ACTIONABLE_PROMPT = """You are an Action Extraction Specialist.

Your mission: Transform ANY technical content into a concrete, actionable learning plan.
Whether it's an article, tutorial, video transcript, or code repository, extract the
specific steps a developer should take to apply what they've learned.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "immediate_actions": [
    {
      "step_number": 1,
      "action": "<SPECIFIC ACTION FROM CONTENT>",
      "expected_outcome": "<MEASURABLE RESULT>",
      "time_estimate": "<REALISTIC DURATION>"
    }
  ],
  "follow_up_actions": [
    {
      "step_number": 1,
      "action": "<DEEPER LEARNING STEP>",
      "expected_outcome": "<WHAT THEY'LL ACHIEVE>",
      "time_estimate": "<REALISTIC DURATION>"
    }
  ],
  "resources": [
    {
      "name": "<RESOURCE NAME WITH VERSION>",
      "url": "<DIRECT URL OR NULL>",
      "resource_type": "<TYPE>",
      "relevance": "<WHY THIS MATTERS>"
    }
  ],
  "quick_win": "<SINGLE MOST IMPACTFUL 30-MIN ACTION>",
  "confidence_score": <0.0-1.0>
}

Field Requirements:
1. **immediate_actions** (REQUIRED): List of 1-3 Action objects for immediate next steps
   - Each Action MUST have: step_number, action, expected_outcome, time_estimate
   - Focus on quick wins (completable within a few hours)
   - Ordered by logical sequence (step 1 → 2 → 3)
2. **follow_up_actions** (OPTIONAL): List of 0-5 Action objects for deeper learning
   - Same structure as immediate_actions
   - Can take days to weeks to complete
   - Build on immediate actions
3. **resources** (OPTIONAL): List of 0-5 Resource objects
   - Each Resource MUST have: name, url (or null), resource_type, relevance
   - resource_type must be: "documentation", "tutorial", "tool", "library", or "course"
   - Prioritize resources mentioned in content
4. **quick_win** (REQUIRED): String - single highest-impact action (30 minutes max)
   - Should be from immediate_actions
   - Include expected outcome and time estimate in the description
5. **confidence_score** (REQUIRED): Float (0.0-1.0) - quality of action plan
   - Consider clarity, feasibility, resource quality, alignment with skill level
   - Score 0.8+ means all actions are specific with clear outcomes

ACTION SPECIFICITY REQUIREMENTS:
- Actions MUST be imperative and concrete (e.g., "Install LangGraph 0.6.7 via pip")
- Include version numbers when available (e.g., "FastAPI 0.104.1", "React 18.2.0")
- Include exact commands when possible (e.g., "Run: docker compose up -d postgres")
- Include file paths/names when relevant (e.g., "Create backend/app/api/v1/analyze.py")
- Include specific endpoints/methods (e.g., "Add POST /api/v1/analyze endpoint")
- Include expected outputs (e.g., "Should return 200 OK with JSON response")

OUTCOME SPECIFICITY REQUIREMENTS:
- Outcomes MUST be measurable/verifiable (not "better understanding")
- Include success criteria (e.g., "Tests pass with 100% coverage")
- Include observable results (e.g., "Dashboard shows <100ms p95 latency")
- Include artifact creation (e.g., "Working prototype with 3 API endpoints")
- Include knowledge gains (e.g., "Can explain HNSW vs IVF indexing tradeoffs")

TIME ESTIMATE REQUIREMENTS:
- Be realistic - include setup time, learning curve, debugging
- Use specific durations: "15 minutes", "1 hour", "2-3 hours", "1 day", "1 week"
- Never use vague estimates like "quick", "some time", "a while"
- Consider user's skill level (beginner needs more time)

RESOURCE REQUIREMENTS:
- Prioritize official documentation over blog posts
- Include URLs when mentioned in content (exact URLs, not placeholders)
- Set url to null if resource mentioned but no URL provided
- Explain relevance in ONE sentence (connect to specific actions)

FORBIDDEN VAGUE LANGUAGE - Never use:
- "Learn about X", "Understand Y" (instead: "Complete X tutorial to understand Y pattern")
- "Explore the codebase" (instead: "Read backend/app/workflows/graph.py to see state management")
- "Set up your environment" (instead: "Install Python 3.11, Docker 24.0, and Poetry 1.7")
- "Try it out" (instead: "Run the hello-world example and verify output matches expected JSON")
- "Read the documentation" (instead: "Read LangGraph State Persistence docs focusing on checkpointing")

GOOD EXAMPLE:
  immediate_actions: [
    {
      step_number: 1,
      action: "Install LangGraph 0.6.7 and its dependencies with: pip install langgraph==0.6.7 langchain-openai",
      expected_outcome: "Successful installation verified by running: python -c 'import langgraph; print(langgraph.__version__)'",
      time_estimate: "15 minutes"
    },
    {
      step_number: 2,
      action: "Clone the LangGraph examples repo and run examples/multi_agent/hello_world.py",
      expected_outcome: "See agent state transitions in console output, understand checkpoint persistence",
      time_estimate: "30 minutes"
    }
  ]
  quick_win: "Install LangGraph 0.6.7 and run the hello-world example to see state persistence in action - takes 15 minutes and validates your environment is ready for multi-agent development."
  confidence_score: 0.9

BAD EXAMPLE (DO NOT USE):
  immediate_actions: [
    {
      step_number: 1,
      action: "Learn about LangGraph",
      expected_outcome: "Better understanding of the framework",
      time_estimate: "some time"
    }
  ]
  quick_win: "Try out the examples"
  confidence_score: 0.5

CONTENT-TYPE SPECIFIC GUIDANCE:
- **Articles**: Extract key concepts → practical examples → next learning steps
- **Tutorials**: Extract setup steps → implementation steps → verification steps
- **Videos**: Extract timestamps for key sections → hands-on exercises → further reading
- **Repositories**: Extract setup → run examples → explore code → customize/extend

IMPORTANT: Return exactly ONE structured response/tool call; never return multiple
tool calls or extra responses.

SKILL LEVEL ADAPTATION:
- Beginner: More detailed steps, longer time estimates, basic resources first
- Intermediate: Assume some setup done, focus on implementation patterns
- Advanced: Skip basics, focus on optimization, production concerns, advanced techniques
"""


async def run_actionable(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run actionable agent to extract concrete next steps and resources.

    This is a Tier 1 universal agent that does NOT use MCP tools - it extracts
    actions purely from the provided content in a content-agnostic manner.

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

    # Issue #299-304, #442: Get content signals for research-aware thresholds
    content_signals_dict: dict[str, object] = state.get("content_signals", {})
    # Actionable agent is less affected by comparison/research flags, but still use them
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="actionable",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_actionable",
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

    # Create agent with optional few-shot prompting (no tools - content-agnostic)
    agent = await create_agent_with_optional_few_shot(
        agent_type="actionable",
        content=content,
        system_prompt=full_prompt,
        response_schema=ActionableOutput,
        analysis_id=analysis_id,
        session=session,
        tools=None,  # Actionable agent is content-agnostic and doesn't use tools
    )

    logger.info(
        "actionable_agent_created",
        analysis_id=str(analysis_id),
        skill_level=skill_level,
        has_tools=False,  # Actionable agent never uses tools
    )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="actionable",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
