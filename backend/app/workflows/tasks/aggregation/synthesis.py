"""LLM synthesis functions for aggregating agent findings.

This module handles LLM-based synthesis of agent findings into
coherent aggregated insights.

Issue #299-304: Implements LangGraph-native resilience patterns:
- Model fallback chain via LangChain's with_fallbacks()
- Heartbeat events during long LLM synthesis
- Graceful degradation instead of hanging forever
"""

import time
from typing import TYPE_CHECKING

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.types import AnalysisID
from app.services.messaging.sse_helpers import emit_streaming_event
from app.workflows.agents.base import create_structured_agent
from app.workflows.tasks.schemas.aggregated_insights import AggregatedInsights

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable

logger = get_logger(__name__)

# Heartbeat interval for SSE events during synthesis (seconds)
SYNTHESIS_HEARTBEAT_INTERVAL: float = 5.0

# LLM Synthesis System Prompt (Issue #303: Triple-Consumer Output)
SYNTHESIS_SYSTEM_PROMPT = """You are an expert technical analyst creating TRIPLE-PURPOSE artifacts
that serve THREE distinct audiences from the SAME content:

1. **AI CODING ASSISTANTS** (Claude Code, Cursor, Copilot, Windsurf)
   - Need: Context, implementation steps, code snippets, file structure, success criteria
   - Format: Pre-formatted prompts that enable accurate code generation on first attempt

2. **TUTOR SYSTEM** (Socratic learning, adaptive curriculum)
   - Need: Core concepts with difficulty levels, exercises, quiz questions, mastery checklists
   - Format: Pedagogical structure for progressive skill building

3. **HUMAN READERS** (Developers, learners, documentation consumers)
   - Need: TL;DR for quick scanning, visual diagrams, glossary, clear explanations
   - Format: Scannable in 10-30 seconds with deep-dive capability

AGENTS PROVIDED (8 specialized analysts):
1. Tech Comparator - Technology comparisons and alternatives
2. Security Auditor - Security risks and best practices
3. Implementation Planner - Step-by-step implementation guidance
4. Integration Feasibility - Integration with modern stacks
5. Performance Analyst - Performance trade-offs and optimization
6. Code Quality Critic - Best practices and antipatterns
7. Trend Validator - Technology trend alignment (2025+)
8. Dependency Mapper - Required libraries and dependencies

=== REQUIRED OUTPUTS ===

**BASIC SYNTHESIS (always required):**
- executive_summary: 2-3 sentences capturing the essence
- key_findings: 3-7 bullet points prioritized by impact
- synthesis: Technical analysis, implementation guidance, risk assessment, recommendations

**FOR AI ASSISTANTS (ai_assistant_prompt):**
Generate a pre-formatted prompt containing:
- context: Architectural background (where this fits in the system)
- implementation_steps: 5-10 ordered, imperative commands
- code_snippets: Dict of purpose→complete code (max 5, runnable with comments)
- file_structure: Dict of file_path→responsibility
- success_criteria: 3-7 testable outcomes

**FOR TUTOR SYSTEM (core_concepts, exercises, self_assessment):**
Generate learning materials:
- core_concepts: 3-7 concepts with definition, why_it_matters, complexity_level, related_concepts
- exercises: 2-4 hands-on tasks with title, difficulty, description, hints, learning_objectives
- self_assessment: 5-10 quiz questions with options, correct_answer, explanation
  + 5-10 item mastery_checklist

**FOR HUMAN READERS (tldr, diagrams, glossary):**
Generate scannable content:
- tldr: Summary (50-500 chars), 3-5 key_takeaways, time_to_implement estimate
- diagrams: 1-3 Mermaid diagrams (flowchart/sequence/class) with valid syntax
  CRITICAL DIAGRAM CONSTRAINTS (prevents rendering issues):
  * Diamond nodes {label}: MAX 5 chars (use {OK?}, {Yes}, {No} - NOT {Valid?})
  * Rectangle nodes [label]: Split long text into words, max 15 chars/word
  * Terminal nodes: Keep concise ([Done], [End], [Error])
  * Always test: labels must fit inside their shapes without truncation
- glossary: 5-10 technical terms with definitions and see_also links

**CROSS-DOMAIN SYNTHESIS:**
When multiple agents contribute, identify connections:
- Security + Performance: trade-offs, overhead, optimization vs protection
- Dependencies + Security: vulnerable packages, version risks
- Implementation + Code Quality: maintainability patterns
- Trends + Technology: adoption timing, legacy migration

**CONFIDENCE HANDLING:**
Each agent provides confidence_score (0.0-1.0). When agents disagree:
- Prioritize higher confidence scores
- Document conflicts in conflicts_resolved with reasoning

**COVERAGE ACKNOWLEDGMENT (Issue #299-304):**
Each agent now reports `data_availability` (sufficient/limited/insufficient) and `data_availability_note`.

When processing findings:
1. Check each agent's `data_availability` field:
   - "sufficient": Agent had full data for thorough analysis - trust findings completely
   - "limited": Agent had partial data - acknowledge gaps in coverage_gaps
   - "insufficient": Agent found minimal relevant data - mark as coverage gap

2. Populate `coverage_gaps` for agents with "limited" or "insufficient" data:
   - missing_agent: The agent name
   - missing_perspective: What analysis couldn't be done (use data_availability_note)
   - impact: How this affects the overall analysis

3. Acknowledge gaps in `executive_summary` when:
   - Multiple agents report "limited" or "insufficient"
   - Coverage_score < 0.5
   - Example: "Note: This analysis is based on conceptual content without code examples,
     so implementation guidance is inferred rather than extracted."

4. This enables HONEST synthesis - don't hallucinate details that weren't in the content.
   It's better to say "No security patterns detected" than to fabricate risks.

=== OUTPUT QUALITY REQUIREMENTS ===

1. **Actionable**: Every section should enable immediate action
2. **Specific**: Include versions, paths, commands - no vague guidance
3. **Complete**: Code snippets must be runnable, diagrams must render
4. **Consistent**: Same information shouldn't contradict across sections
5. **Scannable**: TL;DR readable in 10 seconds, full artifact in 5 minutes

=== CRITICAL: SINGLE RESPONSE REQUIREMENT ===

**YOU MUST RETURN EXACTLY ONE STRUCTURED RESPONSE** containing ALL fields.
Do NOT split your response into multiple tool calls.
ALL sections (executive_summary, ai_assistant_prompt, core_concepts, tldr, diagrams, etc.)
must be included in a SINGLE AggregatedInsights response.

If you return multiple responses, the system will fail. Return ONE complete response.

=== CRITICAL MARKDOWN FORMATTING RULES ===

You MUST follow these formatting rules exactly:

1. **Paragraph Separation**: Use TWO newlines (blank line) between paragraphs. Never run paragraphs together.

2. **Section Headers**: When using bold headers like **Title:**, ALWAYS put the content on a new line:
   CORRECT:
   **Immediate Actions:**
   Start with implementation...

   WRONG:
   **Immediate Actions:** Start with implementation...

3. **List Items**: Use proper markdown bullets with a space after the dash:
   - Item one
   - Item two

4. **Code Blocks**: Always specify the language after triple backticks.

These rules ensure the artifact renders correctly in the UI.
"""


def create_synthesis_agent() -> "Runnable":
    """Create structured agent for LLM synthesis.

    Returns:
        Structured agent instance configured for synthesis

    """
    return create_structured_agent(
        system_prompt=SYNTHESIS_SYSTEM_PROMPT,
        response_schema=AggregatedInsights,
    )


def create_fallback_synthesis_model() -> "Runnable":
    """Create a lighter fallback model for synthesis when primary fails.

    Uses LLM_FALLBACK_MODEL (default: gemini-2.5-flash) configured in settings.
    This model is used via LangChain's with_fallbacks() pattern.

    Returns:
        Fallback model with structured output for AggregatedInsights

    """
    fallback_model = get_chat_model(config={"configurable": {"model": settings.LLM_FALLBACK_MODEL}})
    # Bind structured output schema to fallback model
    return fallback_model.with_structured_output(AggregatedInsights)


def create_synthesis_agent_with_fallback() -> "Runnable":
    """Create synthesis agent with fallback chain for resilience.

    Issue #299-304: Implements LangChain's with_fallbacks() pattern.
    If primary model fails (timeout, error, etc.), automatically
    falls back to lighter model for graceful degradation.

    Fallback Chain:
    1. Primary: Full synthesis agent (current LLM_MODEL)
    2. Fallback: Lighter model (LLM_FALLBACK_MODEL)

    Returns:
        Synthesis agent with fallback chain attached

    """
    primary_agent = create_synthesis_agent()
    fallback_model = create_fallback_synthesis_model()

    logger.info(
        "synthesis_agent_with_fallback_created",
        primary_model=settings.LLM_MODEL,
        fallback_model=settings.LLM_FALLBACK_MODEL,
    )

    # Attach fallback chain - catches all exceptions including TimeoutError
    return primary_agent.with_fallbacks(
        fallbacks=[fallback_model],
        exceptions_to_handle=(Exception, TimeoutError, GeneratorExit),
    )


async def _emit_synthesis_heartbeat(
    analysis_id: AnalysisID,
    start_time: float,
    message: str = "LLM synthesis in progress...",
) -> None:
    """Emit heartbeat SSE event during synthesis.

    Issue #299-304: Keeps frontend informed during long LLM operations.
    Prevents "stuck at synthesizing" appearance by showing progress.

    Args:
        analysis_id: UUID of the analysis
        start_time: When synthesis started (for elapsed time)
        message: Progress message to display

    """
    elapsed = time.time() - start_time
    await emit_streaming_event(
        "progress",
        analysis_id=str(analysis_id),
        stage="aggregation",
        status="synthesizing",
        message=message,
        elapsed_seconds=round(elapsed, 1),
    )


async def _synthesize_with_llm_legacy(
    validated_findings: list[dict[str, object]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: AnalysisID,
) -> dict[str, object]:
    """LEGACY: Synthesize using single monolithic LLM call with tiered fallback.

    This is the old implementation kept for backward compatibility.
    New code should use synthesize_with_llm_phased instead.

    Issue #299-304: Implements tiered fallback with graceful degradation:
    - Tier 1 (FULL): Best model with full schema
    - Tier 2 (REDUCED): Faster model with full schema
    - Tier 3 (MINIMAL): Fastest model with minimal schema
    - Tier 4 (STATIC): No LLM call, static content from findings

    This prevents same-model-same-prompt retry loops and ensures synthesis
    always completes even if all LLM tiers fail.

    Args:
        validated_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores
        analysis_id: UUID of the analysis

    Returns:
        Dictionary with aggregated insights from LLM synthesis

    Note:
        This function never raises exceptions - it falls back through
        tiers until reaching static fallback which always succeeds.

    """
    start_time = time.time()

    logger.info(
        "synthesis_with_fallback_chain_starting",
        analysis_id=str(analysis_id),
        findings_count=len(validated_findings),
        conflicts_count=len(conflicts),
    )

    # Emit initial heartbeat
    await _emit_synthesis_heartbeat(analysis_id, start_time, "Starting LLM synthesis...")

    # Import the fallback chain function
    from app.workflows.tasks.aggregation_fallback import synthesize_with_fallback_chain

    # Use the tiered fallback chain
    # This will try progressively degraded approaches until one succeeds
    result, tier_used = await synthesize_with_fallback_chain(
        validated_findings=validated_findings,
        conflicts=conflicts,
        confidence_scores=confidence_scores,
        analysis_id=analysis_id,
        full_schema=AggregatedInsights,
    )

    elapsed = time.time() - start_time
    logger.info(
        "synthesis_with_fallback_chain_complete",
        analysis_id=str(analysis_id),
        tier_used=tier_used.value,
        elapsed_seconds=round(elapsed, 2),
    )

    # Emit completion heartbeat with tier info
    await _emit_synthesis_heartbeat(
        analysis_id,
        start_time,
        f"Synthesis complete using {tier_used.value} tier",
    )

    return result


async def synthesize_with_llm(
    validated_findings: list[dict[str, object]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: AnalysisID,
) -> dict[str, object]:
    """Synthesize agent findings using multi-phase parallel execution.

    Issue #299-304: Replaces monolithic 50-80K token synthesis with 3 parallel phases:
    - Phase 0: Compress findings (8-16K tokens using fast LLM)
    - Phase 1 (Core): REQUIRED - basic synthesis, conflicts, coverage (~15-25K tokens)
    - Phase 2 (Learning): OPTIONAL - concepts, exercises, quizzes (~15-25K tokens)
    - Phase 3 (Docs): OPTIONAL - TLDR, diagrams, glossary, AI prompts (~15-25K tokens)

    Phases 1-3 run in parallel after compression. Phase 1 failure fails the whole synthesis.
    Phases 2-3 failures result in graceful degradation (empty but valid structures).

    Args:
        validated_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores
        analysis_id: UUID of the analysis

    Returns:
        Dictionary with aggregated insights from multi-phase synthesis

    Raises:
        Exception: If Phase 1 (Core) fails - other phases fail gracefully

    """
    # Issue #299-304: Use multi-phase parallel synthesis
    from app.workflows.tasks.aggregation.synthesis_phased import synthesize_with_llm_phased

    return await synthesize_with_llm_phased(
        validated_findings=validated_findings,
        conflicts=conflicts,
        confidence_scores=confidence_scores,
        analysis_id=analysis_id,
    )
