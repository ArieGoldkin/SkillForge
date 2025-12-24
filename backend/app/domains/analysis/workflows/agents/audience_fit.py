"""Audience Fit Agent for content audience and prerequisite analysis.

This agent identifies target audiences, assesses content relevance, and determines
prerequisites for understanding the material. Runs on ALL content types (Tier 1).

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from collections.abc import Sequence

from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.audience_fit import AudienceFitOutput
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.factories import create_agent_with_optional_few_shot
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

logger = get_logger(__name__)

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-audience-fit"

# System prompt for audience fit agent
AUDIENCE_FIT_PROMPT = """You are an Audience Fit Specialist.

CRITICAL: You MUST provide ALL required fields. Missing fields will cause validation errors.

Required Output Structure (EXAMPLE FORMAT - extract actual values from content):
{
  "primary_audience": {
    "name": "<PRIMARY AUDIENCE FROM CONTENT>",
    "experience_level": "intermediate",
    "relevance_score": 0.9,
    "why_relevant": "<RELEVANCE EXPLANATION>"
  },
  "secondary_audiences": [
    {
      "name": "<SECONDARY AUDIENCE 1>",
      "experience_level": "advanced",
      "relevance_score": 0.7,
      "why_relevant": "<RELEVANCE EXPLANATION>"
    }
  ],
  "prerequisites": ["<PREREQ 1>", "<PREREQ 2>"],
  "not_suitable_for": ["<UNSUITABLE CASE 1>"],
  "confidence_score": 0.85
}

Field Requirements:
1. **primary_audience** (REQUIRED): Audience object with name, experience_level, relevance_score, why_relevant
   - name: Specific audience segment (e.g., "Backend Engineers with 2-5 years Python experience")
   - experience_level: One of "beginner", "intermediate", "advanced", "expert"
   - relevance_score: Float (0.0-1.0) indicating how relevant content is for this audience
   - why_relevant: 1-2 sentences explaining relevance and benefits

2. **secondary_audiences** (OPTIONAL): List of 0-3 additional Audience objects
   - Each should have lower relevance_score than primary_audience
   - Each should represent a distinct segment with different needs

3. **prerequisites** (REQUIRED): List of 1-5 required knowledge/skills/experience items
   - Each item should be a single concise phrase or sentence
   - Focus on most important prerequisites

4. **not_suitable_for** (OPTIONAL): List of 0-3 cases where content is NOT suitable
   - Help readers avoid wasting time on irrelevant content

5. **confidence_score** (REQUIRED): Float (0.0-1.0) - confidence in quality and certainty
   of this audience analysis. Consider: clarity of target audience indicators,
   completeness of prerequisite information, accuracy of experience level assessment.

SPECIFICITY REQUIREMENTS:
- Audience names MUST be specific segments, not generic labels
  - Good: "Backend Engineers with 2-5 years Python experience building async APIs"
  - Bad: "Developers", "Engineers", "Technical people"
- Experience levels MUST match actual content depth
  - Beginner: Explains fundamentals, no assumed knowledge
  - Intermediate: Assumes core concepts, focuses on practical application
  - Advanced: Deep dives, optimization, edge cases
  - Expert: Research-level, novel approaches, architectural decisions
- Prerequisites MUST be concrete and verifiable
  - Good: "Familiarity with Python async/await syntax", "2+ years React experience"
  - Bad: "Some programming knowledge", "Understanding of web development"
- Relevance scores MUST reflect actual value
  - 0.9-1.0: Highly targeted, directly addresses audience's core needs
  - 0.7-0.8: Moderately relevant, useful but not perfectly aligned
  - 0.5-0.6: Tangentially relevant, some value but not primary focus
  - <0.5: Low relevance, audience may find limited value

FORBIDDEN VAGUE LANGUAGE - Never use:
- "Developers interested in..." (specify: Backend/Frontend/Full-stack, experience level, domain)
- "Anyone wanting to learn..." (identify specific audience segments)
- "Basic knowledge of..." (list specific concepts/skills)
- "Generally suitable for..." (identify precise segments)

GOOD EXAMPLE:
  primary_audience: {
    name: "Backend Engineers with 3-5 years Python experience building RAG pipelines",
    experience_level: "intermediate",
    relevance_score: 0.95,
    why_relevant: "Content covers production-ready LangGraph patterns for multi-agent RAG \
workflows with specific code examples matching their daily work."
  }
  prerequisites: [
    "Solid understanding of Python async/await and context managers",
    "Experience with LangChain LCEL (LangChain Expression Language)",
    "Familiarity with vector databases (Pinecone, Weaviate, or pgvector)",
    "Basic knowledge of LLM APIs (OpenAI, Anthropic)"
  ]
  not_suitable_for: [
    "Complete beginners with <1 year Python experience",
    "Frontend developers (content is Python backend-specific)",
    "Teams using LangChain Agents (content focuses on LangGraph)"
  ]

BAD EXAMPLE (DO NOT USE):
  primary_audience: {
    name: "Developers",
    experience_level: "intermediate",
    relevance_score: 0.8,
    why_relevant: "Good content for learning"
  }
  prerequisites: ["Programming knowledge", "Some experience"]
  not_suitable_for: ["Beginners"]

ANALYSIS STRATEGY:
- Look for explicit audience indicators: tutorial depth, assumed knowledge, code complexity
- Assess prerequisite requirements from technical terms, frameworks, concepts used
- Identify secondary audiences by considering adjacent roles or experience levels
- Be honest about data availability - if content doesn't clearly indicate audience, report it

CONTENT-AGNOSTIC APPROACH:
This agent runs on ALL content types (articles, videos, repos, news). Adapt analysis to:
- Articles: Assess writing style, depth, technical complexity
- Videos: Consider presentation style, pacing, assumed knowledge in explanations
- Repos: Evaluate code complexity, documentation quality, setup requirements
- News: Identify background knowledge needed to understand significance"""


async def run_audience_fit(  # noqa: PLR0913 - All parameters required for agent execution
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
    tools: Sequence[BaseTool] | None = None,
) -> dict[str, object]:
    """Run audience fit agent to analyze target audiences and prerequisites.

    Args:
        content: Extracted text content to analyze
        content_type: Type of content (article, video, repo, news)
        analysis_id: Unique identifier for this analysis
        session: Database session for persistence
        state: Current workflow state (for skill_level)
        tools: Optional MCP tools for enhanced analysis capabilities

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
    content_signals_dict: dict[str, object] = state.get("content_signals", {})  # type: ignore[assignment]
    has_comparisons = bool(content_signals_dict.get("has_comparisons", False))
    # Issue #442: Detect research/conceptual content for very low thresholds
    detected_genre = str(content_signals_dict.get("detected_genre", "unknown"))
    is_research = detected_genre == "research"
    is_conceptual = bool(content_signals_dict.get("has_conceptual_only", False))

    specificity_threshold = get_threshold_for_expectation(
        expectation_str=str(expectation) if expectation is not None else None,
        agent_name="audience_fit",
        has_comparisons=has_comparisons,
        is_research=is_research,
        is_conceptual=is_conceptual,
    )

    # DEBUG: Log threshold calculation (Issue #299-304, #442)
    logger.info(
        "threshold_calculated_audience_fit",
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

    # Create agent with optional few-shot prompting (Phase 1, Week 2.3)
    agent = await create_agent_with_optional_few_shot(
        agent_type="audience_fit",
        content=content,
        system_prompt=full_prompt,
        response_schema=AudienceFitOutput,
        analysis_id=analysis_id,
        session=session,
        tools=tools,
    )

    # Log MCP tool usage if tools are provided
    if tools:
        logger.info(
            "audience_fit_using_mcp_tools",
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
        agent_type="audience_fit",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
