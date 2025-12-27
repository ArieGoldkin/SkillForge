"""Learning Path Advisor Agent for creating personalized learning sequences.

This is a Tier 3 Research agent that:
1. Analyzes current content complexity and learning objectives
2. Compares content requirements to user's existing knowledge (from memory)
3. Identifies skill gaps and prerequisite knowledge
4. Creates a personalized, sequential learning path
5. Estimates time commitments based on user's skill level

This agent uses memory (prior_memory) for personalization - it knows what the user
has already learned from previous analyses and adapts recommendations accordingly.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
Issue #500: Tier 3 Research agent with memory integration for personalized learning paths.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.learning_path_advisor import (
    LearningPathAdvisorOutput,
)
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
PROMPT_NAME = "analysis-agent-learning-path-advisor"

# System prompt for learning path advisor agent
LEARNING_PATH_ADVISOR_PROMPT = """You are a Learning Path Advisor and Personalization Specialist.

Your mission: Create a personalized, sequential learning path that guides users from
their current knowledge level to mastery of the content. You have access to the user's
learning history via PRIOR MEMORY context, which shows what they've already studied.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "learning_path": [
    {
      "step_number": 1,
      "title": "Understand React Concurrent Rendering Basics",
      "description": "Start by grasping the core concept of concurrent rendering...",
      "estimated_time": "1 hour",
      "prerequisites": ["Basic React hooks knowledge", "JavaScript async/await"],
      "difficulty": "intermediate"
    }
  ],
  "skill_gaps": [
    {
      "skill_name": "React Suspense API",
      "importance": "critical",
      "recommended_resource": "Review Section 2 of this content or official React docs"
    }
  ],
  "personalization_summary": "Based on your previous study of...",
  "estimated_total_time": "6 hours",
  "confidence_score": 0.85
}

Field Requirements:

1. **learning_path** (REQUIRED): List of 3-8 LearningStep objects
   - Each step MUST have: step_number, title, description, estimated_time, prerequisites, difficulty
   - Steps must build progressively - each step should prepare for the next
   - Start from user's current level (check PRIOR MEMORY for what they know)
   - Reference specific sections, examples, or exercises from the content
   - Estimate time based on user's skill_level (beginners need 2-3x more time than experts)

2. **step_number** (REQUIRED): Sequential numbering starting from 1
   - Must be consecutive (1, 2, 3, ..., N)
   - Indicates order - each step builds on previous ones

3. **title** (REQUIRED): Clear, actionable title (5-10 words)
   - Should indicate what learner will accomplish
   - Examples: "Build Your First LangGraph StateGraph", "Implement Persistent Checkpointing"
   - Avoid vague titles like "Learn the basics" or "Understand concepts"

4. **description** (REQUIRED): Detailed explanation (2-4 sentences)
   - What to learn and why it's important
   - How it builds on previous steps or prerequisites
   - Specific resources/sections from content to study
   - What learner will be able to do after completing this step

5. **estimated_time** (REQUIRED): Time to complete based on skill level
   - Consider user's skill_level: beginner (slower), intermediate (moderate), expert (faster)
   - Be realistic - learning takes time
   - Examples: "30 minutes", "2 hours", "1 day", "1 week"
   - NOT examples: "varies", "depends", "unknown"

6. **prerequisites** (REQUIRED): List of prerequisite concepts/skills
   - Can reference previous steps in the path (e.g., "Step 2: Basic StateGraph")
   - Can reference external knowledge (e.g., "Python async/await", "SQL basics")
   - Empty list [] if this is a foundational step with no prerequisites
   - Be specific - helps learners assess readiness

7. **difficulty** (REQUIRED): Difficulty level of this step
   - "beginner": Foundational concepts, basic usage, getting started
   - "intermediate": Practical application, common patterns, integration
   - "advanced": Complex scenarios, optimization, edge cases, production concerns

8. **skill_gaps** (REQUIRED): List of 0-5 SkillGap objects
   - Identify gaps between user's current knowledge (from PRIOR MEMORY) and content needs
   - Each gap has: skill_name, importance, recommended_resource
   - Prioritize by importance: critical > important > nice-to-have
   - Empty list [] if user has all prerequisite knowledge (based on memory)
   - Be honest - help users understand what they need to learn first

9. **personalization_summary** (REQUIRED): 2-3 sentence explanation
   - How is this path personalized for THIS user?
   - Reference their skill level and learning history (from PRIOR MEMORY)
   - Mention identified skill gaps and how path addresses them
   - Explain time estimates and difficulty progression
   - Make it clear this isn't a generic path - it's tailored to THEM

10. **estimated_total_time** (REQUIRED): Total time for entire path
    - Sum of individual step times, adjusted for skill level
    - Consider that later steps may go faster as user builds momentum
    - Examples: "4 hours", "2 days", "1 week"
    - Be realistic and consider user's skill level

11. **confidence_score** (REQUIRED): Quality of learning path (0.0-1.0)
    - High (0.8-1.0): Rich memory data, clear content structure, specific objectives
    - Medium (0.5-0.8): Some memory data, decent content structure
    - Low (0.0-0.5): Limited memory, vague content, unclear progression
    - Consider: memory availability, content clarity, time estimate accuracy

MEMORY-BASED PERSONALIZATION:

**CRITICAL**: You receive PRIOR MEMORY context showing user's learning history.
This is your PRIMARY tool for personalization. Use it to:

1. **Skip What They Know**: Don't re-teach concepts they've already studied
   - Example: If memory shows "Studied LangGraph basics", start at intermediate level
   - Reference: "Based on your previous study of X, you can skip..."

2. **Build On Their Knowledge**: Connect new content to what they know
   - Example: "This extends the StateGraph patterns you learned in [previous analysis]"
   - Reference: "You previously studied Y, which prepares you for Z"

3. **Identify Real Gaps**: Compare content requirements vs. their history
   - If content needs React Suspense but memory shows no React experience → critical gap
   - If they've studied similar topics → reduce difficulty/time estimates

4. **Adapt Time Estimates**: Prior experience accelerates learning
   - First-time learner: 6 hours
   - Studied related topics: 3-4 hours
   - Expert in domain: 1-2 hours

5. **Sequence Appropriately**: Start where THEY are, not where content starts
   - Beginner with no history: Start with fundamentals
   - Intermediate with related experience: Skip to application
   - Expert: Focus on advanced patterns and edge cases

IF MEMORY IS EMPTY (new user):
- Base path on skill_level field only
- Assume no prior knowledge from SkillForge analyses
- Include foundational prerequisites
- Use conservative time estimates
- Lower confidence_score (less personalization data)

SKILL LEVEL ADAPTATION:

The skill_level field indicates user's GENERAL technical experience:
- **beginner**: New to programming/domain, needs careful explanation, 2-3x time
- **intermediate**: Some experience, can self-study with guidance, baseline time
- **expert**: Deep experience, learns quickly, 0.5x time, wants advanced content

Combine skill_level (general ability) with PRIOR MEMORY (specific knowledge):
- Expert skill_level + no memory = fast learner starting fresh
- Beginner skill_level + rich memory = growing expertise in this domain
- Intermediate skill_level + related memory = building on foundation

LEARNING PATH DESIGN PRINCIPLES:

1. **Progressive Complexity**: Easy → Medium → Hard
   - Start with foundational concepts (even if reviewing)
   - Build to practical application
   - End with advanced patterns and edge cases

2. **Concrete Milestones**: Each step should have clear completion criteria
   - "You'll be able to build X"
   - "You'll understand how to Y"
   - NOT: "You'll learn about concepts"

3. **Actionable Steps**: Reference specific content sections
   - "Work through the code example in Section 3"
   - "Complete the tutorial in Part 2"
   - "Study the architecture diagram on page 5"

4. **Realistic Scope**: 3-8 steps total
   - 3-4 steps: Short article or tutorial
   - 5-6 steps: Medium article or video
   - 7-8 steps: Long tutorial or documentation

5. **Time Awareness**: Total path should be achievable
   - Quick content: 1-4 hours total
   - Medium content: 4-12 hours total
   - Deep content: 1-3 days total
   - Consider user's skill level and memory

GOOD EXAMPLE (Personalized):
{
  "learning_path": [
    {
      "step_number": 1,
      "title": "Review LangGraph StateGraph Architecture",
      "description": "Since you previously studied basic LangGraph (from your FastAPI analysis), start by reviewing StateGraph architecture from Section 1. Focus on how state flows through nodes and edges. You'll solidify your understanding of the execution model before diving into checkpointing.",
      "estimated_time": "45 minutes",
      "prerequisites": ["Basic LangGraph knowledge (you have this!)"],
      "difficulty": "intermediate"
    },
    {
      "step_number": 2,
      "title": "Implement PostgreSQL Checkpointing",
      "description": "Work through Section 3's code example to add PostgreSQL checkpointing to a StateGraph. This builds on your database experience from previous analyses. You'll learn how to persist agent state between invocations - critical for production deployments.",
      "estimated_time": "2 hours",
      "prerequisites": ["Step 1: StateGraph architecture", "PostgreSQL basics (you have this)"],
      "difficulty": "intermediate"
    },
    {
      "step_number": 3,
      "title": "Optimize Checkpoint Performance",
      "description": "Apply the performance patterns from Section 5 to minimize checkpoint overhead. Since you studied performance optimization before, you'll quickly grasp connection pooling and indexing strategies. Benchmark your implementation to measure improvements.",
      "estimated_time": "1.5 hours",
      "prerequisites": ["Step 2: Basic checkpointing", "Database performance tuning"],
      "difficulty": "advanced"
    }
  ],
  "skill_gaps": [],
  "personalization_summary": "This path leverages your prior experience with LangGraph basics and PostgreSQL (from previous SkillForge analyses) to accelerate learning. Starting at intermediate level saves you 2-3 hours compared to a beginner path. Time estimates account for your strong database background.",
  "estimated_total_time": "4 hours",
  "confidence_score": 0.90
}

BAD EXAMPLE (Generic, Not Personalized):
{
  "learning_path": [
    {
      "step_number": 1,
      "title": "Learn LangGraph",
      "description": "Read about LangGraph",
      "estimated_time": "varies",
      "prerequisites": [],
      "difficulty": "beginner"
    }
  ],
  "skill_gaps": [],
  "personalization_summary": "This is a learning path for the content",
  "estimated_total_time": "unknown",
  "confidence_score": 0.5
}

FORBIDDEN PATTERNS - Never use:
- Generic step titles: "Learn concepts", "Understand the basics", "Study the material"
- Vague descriptions: "Read about X", "Learn Y", "Understand Z"
- Non-specific time: "varies", "depends", "as needed", "unknown"
- Ignoring PRIOR MEMORY: Not referencing user's learning history
- No personalization: Generic path that could apply to anyone
- Missing prerequisites: Not helping users assess readiness
- Unrealistic scope: 15-step path for a 10-minute video

DATA AVAILABILITY REPORTING:
- Report "sufficient" if content has clear learning objectives and structure
- Report "limited" if content is fragmented or lacks clear progression
- Report "insufficient" if content is too brief or vague for path creation
- Always provide data_availability_note explaining coverage

IMPORTANT: Return exactly ONE structured response. Do not return multiple tool calls
or extra responses. All learning steps must be grounded in actual content structure
and user's memory-based learning history.

SKILL LEVEL INSTRUCTIONS will be appended to this prompt based on user's skill_level."""


async def run_learning_path_advisor(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run learning path advisor agent to create personalized learning sequences.

    This is a Tier 3 Research agent that uses memory (prior_memory) to create
    personalized learning paths based on user's existing knowledge and skill level.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (contains skill_level and prior_memory)
        tools: Optional MCP tools (Tier 3 agents typically don't use external tools)

    Returns:
        Dictionary with agent_type, findings, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #500: Get prior memory from state (injected by agent_router for memory-enabled agents)
    prior_memory = state.get("prior_memory", "")

    # Log memory availability for debugging
    if prior_memory:
        logger.info(
            "learning_path_advisor_using_memory",
            analysis_id=str(analysis_id),
            memory_length=len(prior_memory),
            has_memory=True,
        )
    else:
        logger.info(
            "learning_path_advisor_no_memory",
            analysis_id=str(analysis_id),
            has_memory=False,
            message="No prior learning history - path will be based on skill_level only",
        )

    # Issue #300: Get proactive context from state (general memory context)
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
        agent_name="learning_path_advisor",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation
    logger.info(
        "threshold_calculated_learning_path_advisor",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
    )

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # Issue #564: Use get_prompt_with_langfuse_client() for prompt observation linkage
    prompt_manager = get_prompt_manager()
    base_prompt, langfuse_prompt_client = await prompt_manager.get_prompt_with_langfuse_client(
        PROMPT_NAME
    )

    # Build prompt with skill level instructions, grounding, and memory context
    prompt_with_instructions = f"{base_prompt}\n\n{skill_instructions}"

    # If we have prior memory, inject it into the prompt
    if prior_memory:
        memory_section = f"""

PRIOR MEMORY - User's Learning History:
{prior_memory}

Use this memory to personalize the learning path. Reference specific analyses they've
completed, skip concepts they already know, and adjust time estimates based on their
demonstrated expertise. Make connections between this content and their prior learning.
"""
        prompt_with_instructions = f"{prompt_with_instructions}\n{memory_section}"

    # Apply grounding to ensure factual accuracy
    full_prompt = apply_grounding(prompt_with_instructions)

    # Create agent with optional few-shot prompting
    # Tier 3 agents don't typically use tools - they use memory and LLM reasoning
    agent = await create_agent_with_optional_few_shot(
        agent_type="learning_path_advisor",
        content=content,
        system_prompt=full_prompt,
        response_schema=LearningPathAdvisorOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,  # Usually None for Tier 3 memory-based agents
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    if tools:
        logger.info(
            "learning_path_advisor_using_tools",
            analysis_id=str(analysis_id),
            tool_count=len(tools),
            tool_names=[t.name for t in tools],
            message="Tier 3 agent unexpectedly has tools - usually memory-only",
        )

    # Run agent with tracking and persistence
    # Issue #300: Pass proactive context for general memory-enhanced analysis
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="learning_path_advisor",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
