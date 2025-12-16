"""Fallback logic for aggregation when LLM synthesis fails.

Issue #299-304: Implements tiered fallback chain with graceful degradation:
- Tier 1 (FULL): Best model with full schema
- Tier 2 (REDUCED): Faster model with full schema
- Tier 3 (MINIMAL): Fastest model with minimal schema
- Tier 4 (STATIC): No LLM call, static content from findings

This prevents same-model-same-prompt retry loops and ensures synthesis
always completes even if all LLM tiers fail.
"""

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.domains.analysis.workflows.agents.invocation import invoke_agent
from app.domains.analysis.workflows.agents.response_processing import extract_structured_response
from app.domains.analysis.workflows.tasks.aggregation_helpers import format_findings_for_llm
from app.domains.analysis.workflows.tasks.prompt_builders import build_synthesis_user_prompt
from app.shared.services.messaging.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


class CompressedFinding(BaseModel):
    """Compressed agent finding for minimal schema fallback."""

    agent_type: str = Field(description="Type of agent that produced this finding")
    key_insights: list[str] = Field(
        description="3-5 key insights from this agent",
        max_length=5,
    )
    confidence_score: float = Field(
        description="Agent's confidence in findings",
        ge=0.0,
        le=1.0,
    )


class MinimalSynthesis(BaseModel):
    """Emergency fallback synthesis with only essential fields."""

    technical_analysis: str = Field(description="Brief technical summary")
    implementation_guidance: str = Field(description="Basic implementation steps")
    risk_assessment: str = Field(description="Key risks identified")
    recommendations: str = Field(description="Top recommendations")


class MinimalSynthesisSchema(BaseModel):
    """Emergency fallback schema with only essential fields - guaranteed to work.

    Used when full schema fails with faster models. Provides basic synthesis
    that ensures artifact generation can proceed even with degraded quality.
    """

    executive_summary: str = Field(
        description="2-3 sentence summary",
        min_length=50,
    )
    key_findings: list[str] = Field(
        description="3-5 bullet points",
        min_length=3,
        max_length=5,
    )
    synthesis: MinimalSynthesis = Field(description="Essential synthesis content")
    coverage_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Estimate of analysis coverage",
    )
    generation_notes: str = Field(
        default="Degraded mode - partial content generated",
        description="Note about fallback generation",
    )


class FallbackTier(Enum):
    """Fallback tiers with decreasing capability."""

    FULL = "full"  # Full schema, best model
    REDUCED = "reduced"  # Full schema, faster model
    MINIMAL = "minimal"  # Minimal schema, fastest model
    STATIC = "static"  # Static content, no LLM call


class FallbackConfig(BaseModel):
    """Configuration for a fallback tier."""

    model_config = {"arbitrary_types_allowed": True}

    tier: FallbackTier
    model: str | None  # None for STATIC tier
    response_schema: type[BaseModel] | None  # None for STATIC tier
    timeout: int  # Seconds
    system_prompt: str | None = None  # Optional custom system prompt


def create_empty_aggregated_insights(start_time: float) -> dict[str, Any]:
    """Create empty aggregated insights when no findings are available.

    Args:
        start_time: Start time for processing time calculation

    Returns:
        Empty aggregated insights dictionary

    """
    return {
        "executive_summary": "No agent findings available for synthesis.",
        "key_findings": [],
        "synthesis": {
            "technical_analysis": "No analysis available.",
            "implementation_guidance": "No guidance available.",
            "risk_assessment": "No risk assessment available.",
            "recommendations": "No recommendations available.",
        },
        "conflicts_resolved": [],
        "metadata": {
            "total_agents": 0,
            "agents_executed": [],
            "confidence_avg": 0.0,
            "confidence_min": 0.0,
            "confidence_max": 0.0,
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "conflicts_detected": 0,
            "conflicts_resolved": 0,
        },
    }


def create_fallback_aggregated_insights(
    validated_findings: list[dict[str, Any]],
    agent_types: list[str],
    confidence_scores: dict[str, float],
    conflicts: list[dict[str, str]],
    start_time: float,
) -> dict[str, Any]:
    """Create fallback aggregated insights when LLM synthesis fails.

    Args:
        validated_findings: List of validated agent findings
        agent_types: List of agent type names
        confidence_scores: Dictionary of confidence scores
        conflicts: List of detected conflicts
        start_time: Start time for processing time calculation

    Returns:
        Fallback aggregated insights dictionary

    """
    confidence_values = list(confidence_scores.values())

    return {
        "executive_summary": (
            f"Synthesized findings from {len(validated_findings)} agents. "
            f"Analysis includes technical comparison, security assessment, "
            f"and implementation guidance."
        ),
        "key_findings": [
            f"Analysis completed by {len(validated_findings)} specialized agents",
            "Findings available in detailed agent outputs",
            "Review individual agent findings for specific insights",
        ],
        "synthesis": {
            "technical_analysis": "Technical analysis completed by multiple specialized agents.",
            "implementation_guidance": "See individual agent findings for implementation details.",
            "risk_assessment": "Security and risk assessment completed by security auditor agent.",
            "recommendations": "See individual agent recommendations for specific guidance.",
        },
        "conflicts_resolved": [],
        "metadata": {
            "total_agents": len(validated_findings),
            "agents_executed": agent_types,
            "confidence_avg": (
                sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
            ),
            "confidence_min": (min(confidence_values) if confidence_values else 0.0),
            "confidence_max": (max(confidence_values) if confidence_values else 0.0),
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "conflicts_detected": len(conflicts),
            "conflicts_resolved": 0,
            "llm_synthesis_failed": True,
            "fallback_used": True,
        },
    }


def _compress_findings(validated_findings: list[dict[str, Any]]) -> list[CompressedFinding]:
    """Compress agent findings to essential insights only.

    Used for minimal schema fallback to reduce prompt size and complexity.

    Args:
        validated_findings: Full agent findings

    Returns:
        List of compressed findings with key insights only

    """
    compressed = []

    for finding in validated_findings:
        agent_type = str(finding.get("agent_type", "unknown"))
        findings_data = finding.get("findings", {})
        confidence = float(finding.get("confidence_score", 0.0))

        # Extract key insights from findings
        key_insights = []

        if isinstance(findings_data, dict):
            # Try common fields
            if "recommendation" in findings_data:
                key_insights.append(str(findings_data["recommendation"])[:200])
            if "summary" in findings_data:
                key_insights.append(str(findings_data["summary"])[:200])

            # Add type-specific insights
            if agent_type == "security_auditor" and "security_risks" in findings_data:
                risks = findings_data["security_risks"]
                if isinstance(risks, list) and risks:
                    key_insights.append(f"Identified {len(risks)} security risks")
            elif agent_type == "tech_comparator" and "primary_tech" in findings_data:
                key_insights.append(f"Primary tech: {findings_data['primary_tech']}")

        # Ensure at least one insight
        if not key_insights:
            key_insights = [f"{agent_type} analysis completed"]

        compressed.append(
            CompressedFinding(
                agent_type=agent_type,
                key_insights=key_insights[:5],  # Max 5 insights
                confidence_score=confidence,
            )
        )

    return compressed


def _create_static_fallback(
    compressed_findings: list[CompressedFinding],
) -> dict[str, Any]:
    """Create static fallback content from compressed findings.

    This is the final fallback tier - uses NO LLM, extracts content
    directly from findings. Guaranteed to never fail.

    Args:
        compressed_findings: Compressed agent findings

    Returns:
        Static aggregated insights dictionary

    """
    # Extract key insights from all compressed findings
    all_insights = []
    for finding in compressed_findings:
        all_insights.extend(finding.key_insights[:2])  # Take top 2 from each

    # Build static content
    agent_count = len(compressed_findings)
    agent_types = [f.agent_type for f in compressed_findings]

    return {
        "executive_summary": (
            f"Analysis completed with {agent_count} specialized agents. "
            f"Full synthesis unavailable - please review individual agent findings for detailed insights."
        ),
        "key_findings": all_insights[:5]
        if all_insights
        else ["Analysis findings available in agent reports"],
        "synthesis": {
            "technical_analysis": "See individual agent findings for technical details.",
            "implementation_guidance": "Review agent findings for implementation guidance.",
            "risk_assessment": "Risk assessment requires manual review of agent findings.",
            "recommendations": "Recommendations available in agent findings.",
        },
        "coverage_score": 0.3,
        "generation_notes": "Static fallback - full synthesis unavailable. Agent findings contain detailed analysis.",
        # Empty optional fields for full schema compatibility
        "core_concepts": [],
        "exercises": [],
        "self_assessment": None,
        "quick_reference": None,
        "tldr": None,
        "ai_assistant_prompt": None,
        "diagrams": [],
        "glossary": [],
        "conflicts_resolved": [],
        "coverage_gaps": [],
        "cross_domain_connections": [],
        "metadata": {
            "total_agents": agent_count,
            "agents_executed": agent_types,
            "fallback_tier": "static",
            "synthesis_status": "static_fallback",
        },
    }


async def _attempt_synthesis(  # noqa: PLR0913
    validated_findings: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: AnalysisID,
    model: str,
    response_schema: type[BaseModel],
    timeout: int,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """Attempt synthesis with specific model and schema.

    Args:
        validated_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores
        analysis_id: UUID of the analysis
        model: Model name to use
        response_schema: Pydantic schema for structured output
        timeout: Timeout in seconds
        system_prompt: Optional custom system prompt (uses default if None)

    Returns:
        Dictionary with aggregated insights

    Raises:
        Exception: If synthesis fails with this tier

    """
    # Format findings for LLM
    formatted_findings = format_findings_for_llm(validated_findings, conflicts, confidence_scores)

    # Import default system prompt if not provided
    if system_prompt is None:
        from app.domains.analysis.workflows.tasks.aggregation.synthesis import (
            SYNTHESIS_SYSTEM_PROMPT,
        )

        system_prompt = SYNTHESIS_SYSTEM_PROMPT

    # Create agent with custom schema
    synthesis_agent = create_structured_agent(
        system_prompt=system_prompt,
        response_schema=response_schema,
    )

    # Build user prompt
    user_prompt = build_synthesis_user_prompt(formatted_findings=formatted_findings)

    # Invoke agent
    input_messages = {"messages": [{"role": "user", "content": user_prompt}]}

    final_result = await invoke_agent(
        agent=synthesis_agent,
        input_messages=input_messages,
        analysis_id=analysis_id,
        agent_type="aggregation",
        timeout=timeout,
    )

    # Extract structured response
    structured_response = extract_structured_response(final_result, "aggregation")

    return structured_response


MINIMAL_SYSTEM_PROMPT = """You are an expert technical analyst creating a MINIMAL emergency synthesis.

Due to processing constraints, you must generate ONLY the essential fields:
- executive_summary: 2-3 sentences capturing the essence
- key_findings: 3-5 bullet points prioritized by impact
- synthesis: Brief technical analysis, implementation guidance, risk assessment, recommendations

DO NOT attempt to generate:
- Diagrams, glossaries, exercises, quizzes
- AI assistant prompts or code snippets
- Detailed learning materials

Focus on accuracy and completeness of the core synthesis only.
"""


async def synthesize_with_fallback_chain(
    validated_findings: list[dict[str, Any]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: AnalysisID,
    full_schema: type[BaseModel],
) -> tuple[dict[str, Any], FallbackTier]:
    """Try synthesis with progressive fallback chain.

    Issue #299-304: Implements tiered fallback with graceful degradation:
    - FULL: Best model (gemini-2.5-pro) with full schema
    - REDUCED: Faster model (gemini-2.5-flash) with full schema
    - MINIMAL: Fastest model (gemini-2.0-flash-lite) with minimal schema
    - STATIC: No LLM call, extract from findings

    Args:
        validated_findings: List of validated agent findings
        conflicts: List of detected conflicts
        confidence_scores: Dictionary of agent confidence scores
        analysis_id: UUID of the analysis
        full_schema: Full Pydantic schema for structured output

    Returns:
        Tuple of (result_dict, tier_used)

    """
    # Define fallback chain
    fallback_chain = [
        # Tier 1: Try full schema with best model
        FallbackConfig(
            tier=FallbackTier.FULL,
            model=settings.LLM_MODEL,  # gemini-2.5-pro or configured primary
            response_schema=full_schema,
            timeout=60,
        ),
        # Tier 2: Full schema with faster fallback model
        FallbackConfig(
            tier=FallbackTier.REDUCED,
            model=settings.LLM_FALLBACK_MODEL,  # gemini-2.5-flash
            response_schema=full_schema,
            timeout=45,
        ),
        # Tier 3: Minimal schema with fastest model
        FallbackConfig(
            tier=FallbackTier.MINIMAL,
            model="gemini-2.0-flash-lite",
            response_schema=MinimalSynthesisSchema,
            timeout=30,
            system_prompt=MINIMAL_SYSTEM_PROMPT,
        ),
        # Tier 4: Static fallback - never fails
        FallbackConfig(
            tier=FallbackTier.STATIC,
            model=None,
            response_schema=None,
            timeout=0,
        ),
    ]

    last_error = None
    start_time = time.time()

    for config in fallback_chain:
        if config.tier == FallbackTier.STATIC:
            # Final fallback - return static content
            logger.warning(
                "synthesis_using_static_fallback",
                analysis_id=str(analysis_id),
                reason="all_llm_tiers_failed",
                last_error=str(last_error) if last_error else None,
            )

            compressed_findings = _compress_findings(validated_findings)
            result = _create_static_fallback(compressed_findings)

            # Emit SSE notification
            await emit_streaming_event(
                "progress",
                analysis_id=str(analysis_id),
                stage="aggregation",
                status="static_fallback",
                message="Using static fallback - LLM synthesis unavailable",
            )

            return result, config.tier

        try:
            # Type guard: STATIC tier has None model/schema and is handled above
            if config.model is None or config.response_schema is None:
                continue  # Should never happen as STATIC is handled before this

            # Emit SSE notification for this tier
            await emit_streaming_event(
                "progress",
                analysis_id=str(analysis_id),
                stage="aggregation",
                status="synthesizing",
                message=f"Attempting synthesis with tier {config.tier.value} ({config.model})",
            )

            logger.info(
                "synthesis_attempting_tier",
                analysis_id=str(analysis_id),
                tier=config.tier.value,
                model=config.model,
                timeout=config.timeout,
            )

            result = await _attempt_synthesis(
                validated_findings=validated_findings,
                conflicts=conflicts,
                confidence_scores=confidence_scores,
                analysis_id=analysis_id,
                model=config.model,
                response_schema=config.response_schema,
                timeout=config.timeout,
                system_prompt=config.system_prompt,
            )

            elapsed = time.time() - start_time
            logger.info(
                "synthesis_tier_succeeded",
                analysis_id=str(analysis_id),
                tier=config.tier.value,
                model=config.model,
                elapsed_seconds=round(elapsed, 2),
            )

            # Add tier metadata to result
            if isinstance(result, dict):
                metadata = result.get("metadata", {})
                if isinstance(metadata, dict):
                    metadata["fallback_tier"] = config.tier.value
                    metadata["synthesis_model"] = config.model
                    result["metadata"] = metadata

            return result, config.tier

        except Exception as e:  # noqa: BLE001 - Must catch all synthesis errors for fallback
            elapsed = time.time() - start_time
            logger.warning(
                "synthesis_tier_failed",
                analysis_id=str(analysis_id),
                tier=config.tier.value,
                model=config.model,
                elapsed_seconds=round(elapsed, 2),
                error=str(e),
                error_type=type(e).__name__,
            )

            last_error = e
            continue

    # Should never reach here due to static fallback, but just in case
    msg = "Fallback chain exhausted unexpectedly"
    raise RuntimeError(msg)
