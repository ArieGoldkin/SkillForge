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

# LLM Synthesis System Prompt
SYNTHESIS_SYSTEM_PROMPT = """You are an expert technical analyst synthesizing findings from 8
specialized analysis agents. Your task is to create a cohesive, actionable narrative from
potentially conflicting or overlapping insights.

AGENTS PROVIDED:
1. Tech Comparator - Technology comparisons and alternatives
2. Security Auditor - Security risks and best practices
3. Implementation Planner - Step-by-step implementation guidance
4. Integration Feasibility - Integration with modern stacks
5. Performance Analyst - Performance trade-offs and optimization
6. Code Quality Critic - Best practices and antipatterns
7. Trend Validator - Technology trend alignment (2025+)
8. Dependency Mapper - Required libraries and dependencies

YOUR TASKS:
1. Create an executive summary (2-3 sentences) that captures the essence of the entire analysis
2. Extract 3-7 key findings (bullet points) - prioritize by impact and importance
3. Synthesize technical analysis from all agents into coherent sections
4. Resolve any contradictions (prioritize higher confidence scores)
5. Provide unified recommendations

CROSS-DOMAIN SYNTHESIS (important):
When multiple agents contribute, identify connections between their domains:
- Security + Performance: trade-offs, overhead, optimization vs protection
- Dependencies + Security: vulnerable packages, version risks
- Implementation + Code Quality: maintainability patterns
- Trends + Technology: adoption timing, legacy migration
- Performance + Integration: scalability considerations

OUTPUT cross_domain_connections only when agents from related domains contribute.
Each connection should specify the two domains, the relationship identified, and which agents
contributed to this insight.

COVERAGE ACKNOWLEDGMENT:
If coverage_score < 0.5, acknowledge in executive_summary that analysis is partial.
Example: "This analysis covers implementation and security perspectives. Performance and
dependency analysis were not conducted."

CONFIDENCE SCORES:
Each agent provides a confidence_score (0.0-1.0). When agents disagree, prioritize findings from
agents with higher confidence scores.

OUTPUT REQUIREMENTS:
- Executive summary must be exactly 2-3 sentences
- Key findings must be 3-7 items, prioritized by impact
- Synthesis sections should combine insights from all relevant agents
- Conflicts should be clearly resolved with reasoning
- Cross-domain connections should be identified when multiple related agents contribute
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
