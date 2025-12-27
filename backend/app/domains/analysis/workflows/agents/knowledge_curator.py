"""Knowledge Curator Agent for connecting content to user's knowledge graph.

This is a Tier 3 Research agent that:
1. Uses proactive memory (prior_memory from state) to find related content
2. Identifies connections between current content and user's existing analyses
3. Suggests prerequisites and next steps based on knowledge graph
4. Does NOT use external tools - only memory-based analysis

The agent uses memory injection (prior_memory field) which is proactively
populated by the router before agent execution.

Issue #500: Tier 3 Research agent with proactive memory injection.
Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.knowledge_curator import KnowledgeCuratorOutput
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
PROMPT_NAME = "analysis-agent-knowledge-curator"

# System prompt for knowledge curator agent
KNOWLEDGE_CURATOR_PROMPT = """You are a Knowledge Graph Curator.

Your mission: Connect new content to the user's existing knowledge by analyzing
their prior learning (provided via memory context). Identify prerequisite topics,
suggest what to learn next, and explain how this content fits into their learning journey.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content and memory):
{
  "connections": [
    {
      "related_analysis_id": "uuid-of-related-content",
      "relationship_type": "prerequisite",
      "relevance": 0.85
    }
  ],
  "prerequisites": ["async/await in JavaScript", "REST API design principles"],
  "builds_upon": ["Basic React hooks", "Component composition patterns"],
  "recommended_next": [
    {
      "title": "Advanced State Management with Redux Toolkit",
      "reason": "Natural next step after learning React Server Components for complex client state",
      "priority": "high"
    }
  ],
  "knowledge_graph_position": "This content sits at the intermediate-advanced level...",
  "summary": "Found 3 connections to existing content in user's library...",
  "confidence_score": 0.85
}

Field Requirements:
1. **connections** (REQUIRED): List of KnowledgeConnection objects
   - Each connection MUST have: related_analysis_id, relationship_type, relevance
   - Use memory context to find related content from user's library
   - relationship_type values: "prerequisite", "builds_upon", "alternative", "complementary", "contradicts", "extends"
   - relevance score (0.0-1.0): how strongly the two pieces of content relate
   - Empty list if no related content found in memory

2. **prerequisites** (REQUIRED): List of prerequisite topics/skills
   - What should user understand BEFORE learning this content?
   - Be specific (e.g., "async/await in Python", not just "Python basics")
   - Focus on topics not already covered in user's library
   - Empty list if content is beginner-friendly with no prerequisites

3. **builds_upon** (REQUIRED): List of foundational topics
   - What concepts does this content extend or assume knowledge of?
   - Different from prerequisites - these are foundational concepts this content enhances
   - Example: "React hooks" builds upon "Component lifecycle", extends to "Server Components"
   - Empty list if content introduces entirely new concepts

4. **recommended_next** (REQUIRED): List of RecommendedContent objects
   - Each recommendation MUST have: title, reason, priority
   - Priority values: "low", "medium", "high"
   - Order by priority (high first)
   - Include both:
     a) Prerequisite gaps (topics user should learn before this)
     b) Natural next steps (topics to learn after mastering this)
   - Empty list if no specific recommendations

5. **knowledge_graph_position** (REQUIRED): 2-3 sentence analysis
   - Where does this content fit in user's learning journey?
   - Consider: skill level, topic area, breadth vs depth
   - Reference connections to existing content if found
   - Example: "This content sits at the intermediate-advanced level in the React ecosystem.
     It assumes solid understanding of hooks and composition (covered in your previous analyses)
     and introduces server-side rendering patterns that bridge to full-stack development."

6. **summary** (REQUIRED): 2-3 sentence summary
   - State how many connections were found
   - Highlight key prerequisites or gaps
   - Recommend when to study this content
   - Be specific and actionable

7. **confidence_score** (REQUIRED): Float (0.0-1.0)
   - Consider: quality of connections, accuracy of prerequisites, usefulness of recommendations
   - Higher scores mean strong connections to existing knowledge with clear learning path guidance

MEMORY USAGE INSTRUCTIONS:
You will receive "prior_memory" context containing summaries of the user's previously
analyzed content. Use this to:
- Identify related topics they've already studied
- Find prerequisite concepts already in their knowledge base
- Detect gaps in their learning path
- Recommend logical next steps based on what they know

If prior_memory is empty or very limited, report this honestly:
- Set data_availability to "limited" or "insufficient"
- Focus on general prerequisites and next steps
- Lower confidence_score to reflect lack of knowledge graph context

RELATIONSHIP TYPE GUIDELINES:
- **prerequisite**: User should learn the related content BEFORE this one
  Example: "Basic React hooks" is prerequisite to "Advanced hooks patterns"

- **builds_upon**: Current content extends/enhances the related content
  Example: "React Server Components" builds upon "React fundamentals"

- **alternative**: Different approach to solving the same problem
  Example: "Vue 3 Composition API" is alternative to "React hooks"

- **complementary**: Works well together, enhances when combined
  Example: "TypeScript" is complementary to "React development"

- **contradicts**: Presents conflicting approach or advice
  Example: "Class components best practices" contradicts "Functional components only"

- **extends**: Advanced topic that takes related content further
  Example: "Concurrent rendering optimization" extends "React 18 features"

PRIORITY GUIDELINES:
- **high**: Critical gaps or natural next steps that significantly enhance learning
  Example: User learning React Server Components but hasn't studied async patterns (prerequisite gap)

- **medium**: Recommended for deeper understanding but not blocking
  Example: Learning TypeScript after JavaScript basics (enhancement)

- **low**: Optional topics that provide context but aren't essential
  Example: Learning framework history or alternative approaches

IMPORTANT: Return exactly ONE structured response; never return multiple
tool calls or extra responses. You do NOT have access to external tools -
use only the memory context provided.

SKILL LEVEL ADAPTATION:
- Beginner: Focus on immediate prerequisites, gentle learning curve, foundational next steps
- Intermediate: Balance depth and breadth, connect to multiple knowledge areas
- Advanced: Emphasize advanced topics, architectural patterns, edge cases

DATA AVAILABILITY REPORTING:
- Report "sufficient" if memory contains 3+ related analyses for meaningful connections
- Report "limited" if memory has 1-2 related analyses (basic connections possible)
- Report "insufficient" if memory is empty or lacks related content (general guidance only)
- Always provide data_availability_note explaining memory context quality
"""


async def run_knowledge_curator(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,  # noqa: ARG001 - Standard interface, unused (memory-only)
) -> dict[str, object]:
    """Run knowledge curator agent to connect content to user's knowledge graph.

    This is a Tier 3 Research agent that uses proactive memory injection
    (prior_memory field in state) to find connections to existing analyses.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (includes prior_memory for Tier 3)
        tools: Optional MCP tools (NOT used by this agent - memory only)

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

    # Combine memory contexts for comprehensive knowledge graph analysis
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
        agent_name="knowledge_curator",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation and memory availability
    logger.info(
        "threshold_calculated_knowledge_curator",
        analysis_id=analysis_id,
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
        expectation=expectation,
        calculated_threshold=specificity_threshold,
        has_prior_memory=bool(prior_memory),
        memory_length=len(prior_memory) if prior_memory else 0,
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

    # Create agent with optional few-shot prompting
    # Note: Tier 3 agents do NOT use tools - only memory context
    agent = await create_agent_with_optional_few_shot(
        agent_type="knowledge_curator",
        content=content,
        system_prompt=full_prompt,
        response_schema=KnowledgeCuratorOutput,
        analysis_id=analysis_id,
        session=session,
        tools=None,  # No tools for memory-based agent
    )

    # Issue #564: Attach Langfuse prompt client to agent for observation linkage
    if langfuse_prompt_client:
        agent = agent.with_config(metadata={"langfuse_prompt_client": langfuse_prompt_client})

    # Log memory usage - Tier 3 agents should have memory context
    if full_memory_context:
        logger.info(
            "knowledge_curator_using_memory",
            analysis_id=str(analysis_id),
            memory_length=len(full_memory_context),
            has_prior_memory=bool(prior_memory),
            has_proactive_context=bool(proactive_context),
        )
    else:
        logger.warning(
            "knowledge_curator_without_memory",
            analysis_id=str(analysis_id),
            message="Tier 3 agent running without memory context - connections will be limited",
        )

    # Run agent with tracking and persistence
    # Issue #500: Pass memory context (already combined above)
    # Issue #299-304: Pass content-aware specificity threshold
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="knowledge_curator",
        session=session,
        proactive_context=full_memory_context,
        specificity_threshold=specificity_threshold,
    )
