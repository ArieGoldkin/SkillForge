"""Research Analyst Agent for technical content analysis.

This agent analyzes research papers, technical articles, and documentation
to extract key findings, methodology, limitations, and practical implications.

Issue #418: Uses PromptManager for Langfuse prompt fetching with multi-level caching.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import AnalysisID
from app.domains.analysis.schemas.agents.research_analyst import ResearchAnalysis
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.domains.analysis.workflows.agents.execution import run_agent_with_tracking
from app.domains.analysis.workflows.agents.grounding import apply_grounding
from app.domains.analysis.workflows.agents.skill_level_prompts import get_skill_level_instructions
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.prompts.prompt_manager import get_prompt_manager
from app.shared.workflows.utils.content_signals import get_threshold_for_expectation

# Prompt is fetched from Langfuse via PromptManager (with hardcoded fallback)
PROMPT_NAME = "analysis-agent-research-analyst"

# Fallback prompt (used when Langfuse unavailable)
RESEARCH_ANALYST_PROMPT = """You are a Research Analysis Specialist. Your task is to:
1. Identify the main research question or problem being addressed
2. Summarize the methodology and approach used
3. Extract key findings with evidence strength assessment
4. Identify limitations, caveats, and potential biases
5. Synthesize themes and patterns into actionable insights

Focus on:
- Research question clarity and scope
- Methodology rigor (data sources, sample size, analysis approach)
- Evidence strength (replicated, single study, anecdotal)
- Practical implications and applications
- Limitations and generalizability
- Connections to related work

CRITICAL: You MUST include:
- research_question: Clear statement of what's being investigated
- methodology_summary: 2-3 sentences on methods, data, analysis approach
- key_findings: List with finding, evidence_strength, practical_implication
- limitations: List of caveats and biases
- related_work: References to connected research/concepts
- synthesis: 2-3 sentences revealing patterns and novel connections
- recommendation: 2-3 sentences of actionable guidance
- confidence_score: Float (0.0-1.0) for analysis quality

EVIDENCE STRENGTH GUIDELINES:
- "strong": Replicated results, large samples (n>1000), peer-reviewed, multiple studies
- "moderate": Single well-designed study, reasonable methodology, cited work
- "weak": Anecdotal evidence, small samples, blog post claims, unverified

NUMERIC SPECIFICITY REQUIREMENTS:
- Sample sizes: "study with n=2,847 participants" not "large study"
- Effect sizes: "improved accuracy by 23%" not "significantly improved"
- Confidence: "95% CI [0.12, 0.34]" when available
- Dates: "published March 2024" not "recent research"

FORBIDDEN VAGUE LANGUAGE - Never use:
- "interesting findings", "notable results" (state the finding)
- "various methods", "several approaches" (name them)
- "suggests", "indicates" without specifics
- "future work needed" without saying what kind

GOOD EXAMPLE:
  finding: "RAG retrieval accuracy improved 34% using hybrid search (BM25 + dense vectors)"
  evidence_strength: "strong"
  practical_implication: "Implement hybrid retrieval for production RAG systems"

BAD EXAMPLE (DO NOT USE):
  finding: "The approach shows interesting improvements"
  evidence_strength: "moderate"
  practical_implication: "Consider using this method"

Provide critical analysis with actionable synthesis."""


async def run_research_analyst(
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    session: AsyncSession,
    state: AnalysisState,
) -> dict[str, object]:
    """Run research analyst agent.

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

    # Issue #418: Fetch prompt from Langfuse via PromptManager
    # This will check L1 (memory) → L2 (Redis) → L3 (Langfuse API) → Hardcoded fallback
    prompt_manager = get_prompt_manager()
    base_prompt = await prompt_manager.get_prompt(PROMPT_NAME)

    # Build prompt with skill level instructions
    full_prompt = apply_grounding(f"{base_prompt}\n\n{skill_instructions}")

    # Create agent
    agent = create_structured_agent(
        system_prompt=full_prompt,
        response_schema=ResearchAnalysis,
    )

    # Run agent with tracking and persistence
    return await run_agent_with_tracking(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type="research_analyst",
        session=session,
        proactive_context=proactive_context,
        specificity_threshold=specificity_threshold,
    )
