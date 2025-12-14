"""LLM synthesis functions for aggregating agent findings.

This module handles LLM-based synthesis of agent findings into
coherent aggregated insights.
"""

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.core.timeout_config import SYNTHESIS_TIMEOUT
from app.core.types import AnalysisID
from app.workflows.agents.base import create_structured_agent
from app.workflows.agents.invocation import invoke_agent
from app.workflows.agents.response_processing import extract_structured_response
from app.workflows.tasks.aggregation_helpers import format_findings_for_llm
from app.workflows.tasks.prompt_builders import build_synthesis_user_prompt
from app.workflows.tasks.schemas.aggregated_insights import AggregatedInsights

if TYPE_CHECKING:
    from langchain_core.runnables import Runnable

logger = get_logger(__name__)

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

**COVERAGE ACKNOWLEDGMENT:**
If coverage_score < 0.5, acknowledge partial analysis in executive_summary.

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


async def synthesize_with_llm(
    validated_findings: list[dict[str, object]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: AnalysisID,
) -> dict[str, object]:
    """Synthesize agent findings using LLM.

    Args:
        validated_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores
        analysis_id: UUID of the analysis

    Returns:
        Dictionary with aggregated insights from LLM synthesis

    Raises:
        TimeoutError: If synthesis exceeds timeout
        Exception: If LLM synthesis fails

    """
    # Format findings for LLM
    formatted_findings = format_findings_for_llm(validated_findings, conflicts, confidence_scores)

    # Create synthesis agent
    synthesis_agent = create_synthesis_agent()

    # Build user prompt using prompt builder
    user_prompt = build_synthesis_user_prompt(formatted_findings=formatted_findings)

    # Invoke agent with timeout from centralized config
    input_messages = {"messages": [{"role": "user", "content": user_prompt}]}
    final_result = await invoke_agent(
        agent=synthesis_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="aggregation",
        timeout=SYNTHESIS_TIMEOUT,
    )

    # Extract structured response (validated Pydantic model)
    structured_response = extract_structured_response(final_result, "aggregation")

    # structured_response is already a dict from extract_structured_response
    return structured_response
