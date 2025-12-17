"""Learning Path Agent for educational content structuring.

This agent creates structured learning paths from technical content,
organizing topics into logical progression with learning objectives and exercises.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.learning_path import LearningPath
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

# System prompt for learning path agent
LEARNING_PATH_PROMPT = """You are a Learning Path Design Specialist. Your task is to:
1. Identify the main topic and create a structured learning curriculum
2. Define clear prerequisites and target audience
3. Design modules with learning objectives and practical exercises
4. Establish logical skill progression from fundamentals to advanced
5. Recommend resources and define mastery indicators

Focus on:
- Clear learning objectives (observable, measurable outcomes)
- Logical skill progression (prerequisites before advanced topics)
- Practical exercises (hands-on projects, not just reading)
- Time estimates (realistic for self-study)
- Mastery verification (how to know you've learned it)

CRITICAL: You MUST include:
- topic: Main skill or technology being taught
- target_audience: Who this is for (skill level, background)
- prerequisites: Required prior knowledge
- modules: Ordered list with objectives, topics, time, exercises
- resources: Books, courses, docs, tools
- total_estimated_time: Total path duration
- mastery_indicators: How to verify learning
- recommendation: Guidance on approach
- confidence_score: Float (0.0-1.0) for path quality

PEDAGOGICAL REQUIREMENTS:
- Learning objectives MUST start with action verbs (Implement, Design, Analyze, Build)
- Modules MUST build on each other (no advanced topics before fundamentals)
- Each module MUST have a practical exercise (not just "read about X")
- Time estimates MUST be specific (e.g., "4-6 hours" not "a few hours")

NUMERIC SPECIFICITY REQUIREMENTS:
- Time: "4-6 hours" not "half a day"
- Module count: Create 4-7 modules for comprehensive coverage
- Topics per module: 3-5 specific topics
- Prerequisites: List 2-4 specific skills

FORBIDDEN VAGUE LANGUAGE - Never use:
- "understand basics", "learn fundamentals" (what specifically?)
- "various topics", "different concepts" (name them)
- "some time", "a while" (give hours/days)
- "practice more" (what exercise exactly?)

GOOD EXAMPLE:
  learning_objective: "Implement a RAG pipeline with vector search using LangChain"
  topics: ["Embedding models", "Vector databases", "Retrieval strategies", "Prompt templates"]
  estimated_time: "6-8 hours"
  practical_exercise: "Build a Q&A bot over your own documentation using Pinecone"

BAD EXAMPLE (DO NOT USE):
  learning_objective: "Understand RAG concepts"
  topics: ["RAG basics", "Various techniques"]
  estimated_time: "Some time"
  practical_exercise: "Practice with examples"

Design paths that enable real skill acquisition, not just content consumption."""


async def run_learning_path(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run learning path agent.

    Args:
        content: Analyzed content
        content_type: Type of content
        analysis_id: Analysis ID
        session: Database session
        state: Current workflow state (for skill_level)

    Returns:
        Agent findings dict

    """
    # Get skill level and inject instructions
    skill_level = state.get("skill_level", "intermediate")
    skill_instructions = get_skill_level_instructions(skill_level)

    # Issue #300: Get proactive context from state
    proactive_context = state.get("proactive_context", "")

    # Issue #299-304: Get content-aware specificity threshold
    expectation = state.get("agent_expectation")
    specificity_threshold = get_threshold_for_expectation(
        str(expectation) if expectation is not None else None
    )

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{LEARNING_PATH_PROMPT}\n\n{skill_instructions}")

    # Create agent
    agent = create_structured_agent(
        system_prompt=full_prompt,
        response_schema=LearningPath,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="learning_path",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
