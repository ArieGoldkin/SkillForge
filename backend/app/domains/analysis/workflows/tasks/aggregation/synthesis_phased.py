"""Multi-phase parallel synthesis implementation.

Issue #299-304: Splits monolithic 50-80K token synthesis into 3 parallel phases
to prevent timeouts and improve reliability.

Architecture:
- Phase 0: Compress findings (8-16K tokens, fast LLM, parallel per agent)
- Phase 1 (Core): REQUIRED - executive_summary, key_findings, synthesis
- Phase 2 (Learning): OPTIONAL - core_concepts, exercises, self_assessment
- Phase 3 (Docs): OPTIONAL - tldr, ai_assistant_prompt, diagrams, glossary

Phases 1-3 run in parallel after compression. Phase 1 failure fails synthesis.
Phases 2-3 failures result in graceful degradation (empty but valid structures).
"""

import asyncio
import time
from typing import Any

from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import SYNTHESIS_TIMEOUT
from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.base import create_structured_agent
from app.domains.analysis.workflows.agents.invocation import invoke_agent
from app.domains.analysis.workflows.agents.response_processing import extract_structured_response
from app.shared.services.messaging.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


async def _emit_synthesis_heartbeat(
    analysis_id: AnalysisID,
    start_time: float,
    message: str = "LLM synthesis in progress...",
) -> None:
    """Emit heartbeat SSE event during synthesis.

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


async def synthesize_with_llm_phased(
    validated_findings: list[dict[str, object]],
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: AnalysisID,
) -> dict[str, object]:  # Returns AggregatedInsights-compatible dict
    """Synthesize agent findings using multi-phase parallel execution.

    Issue #299-304: Replaces monolithic 50-80K token synthesis with 3 parallel phases.

    Flow:
    1. Phase 0: Compress findings (parallel, ~2K tokens each)
    2. Phases 1-3: Run in parallel:
       - Phase 1 (Core): REQUIRED - fails whole synthesis if fails
       - Phase 2 (Learning): OPTIONAL - returns empty on failure
       - Phase 3 (Docs): OPTIONAL - returns empty on failure
    3. Merge results into final AggregatedInsights dict

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
    start_time = time.time()

    logger.info(
        "synthesis_multi_phase_starting",
        analysis_id=str(analysis_id),
        findings_count=len(validated_findings),
        conflicts_count=len(conflicts),
    )

    # Emit initial heartbeat
    await _emit_synthesis_heartbeat(analysis_id, start_time, "Starting multi-phase synthesis...")

    # Convert validated_findings list to dict for compression
    agent_findings_dict: dict[str, Any] = {}
    for finding in validated_findings:
        agent_type = finding.get("agent_type")
        if agent_type:
            agent_findings_dict[str(agent_type)] = finding  # type: ignore[arg-type]

    try:
        # Import compression and phase functions
        from app.domains.analysis.workflows.tasks.aggregation.compress_findings import (
            compress_all_findings,
        )

        # Phase 0: Compress findings (fast LLM, parallel for all agents)
        await _emit_synthesis_heartbeat(analysis_id, start_time, "Phase 0: Compressing findings...")

        compressed_findings = await compress_all_findings(
            agent_findings=agent_findings_dict,
            analysis_id=str(analysis_id),
        )

        phase0_elapsed = time.time() - start_time
        logger.info(
            "synthesis_phase0_complete",
            analysis_id=str(analysis_id),
            compressed_count=len(compressed_findings),
            phase_elapsed=round(phase0_elapsed, 2),
        )

        # Emit heartbeat for parallel phases
        await _emit_synthesis_heartbeat(
            analysis_id, start_time, "Running parallel synthesis phases (1-3)..."
        )

        # Create phase tasks
        core_task = _synthesize_core(
            compressed_findings=compressed_findings,
            conflicts=conflicts,
            confidence_scores=confidence_scores,
            analysis_id=str(analysis_id),
        )

        learning_task = _synthesize_learning(
            compressed_findings=compressed_findings,
            analysis_id=str(analysis_id),
        )

        docs_task = _synthesize_docs(
            compressed_findings=compressed_findings,
            analysis_id=str(analysis_id),
        )

        # Run phases 1-3 in parallel with exception handling
        results = await asyncio.gather(
            core_task,
            learning_task,
            docs_task,
            return_exceptions=True,  # Don't fail all if one fails
        )

        core_result, learning_result, docs_result = results

        # Phase 1 is REQUIRED - if it fails, raise the exception
        if isinstance(core_result, Exception):
            logger.error(
                "synthesis_phase1_core_failed",
                analysis_id=str(analysis_id),
                error=str(core_result),
                error_type=type(core_result).__name__,
            )
            raise core_result

        # Log phase completion
        phases_elapsed = time.time() - start_time
        logger.info(
            "synthesis_phases_1_3_complete",
            analysis_id=str(analysis_id),
            phase1_success=True,
            phase2_success=not isinstance(learning_result, Exception),
            phase3_success=not isinstance(docs_result, Exception),
            phases_elapsed=round(phases_elapsed, 2),
        )

        # Merge results with graceful degradation for failures
        result = _merge_phase_results(core_result, learning_result, docs_result)

        # Add metadata about synthesis method (typed)
        from app.shared.types import SynthesisMetadata

        synthesis_meta: SynthesisMetadata = {
            "synthesis_method": "multi_phase_parallel",
            "phase0_compressed_count": len(compressed_findings),
            "phase1_core_success": True,
            "phase2_learning_success": not isinstance(learning_result, Exception),
            "phase3_docs_success": not isinstance(docs_result, Exception),
        }
        result["metadata"] = synthesis_meta  # type: ignore[assignment]

        elapsed = time.time() - start_time
        logger.info(
            "synthesis_multi_phase_complete",
            analysis_id=str(analysis_id),
            total_elapsed=round(elapsed, 2),
        )

        # Emit completion heartbeat
        await _emit_synthesis_heartbeat(
            analysis_id,
            start_time,
            "Multi-phase synthesis complete",
        )

        return result

    except Exception as e:
        # Log failure and re-raise
        elapsed = time.time() - start_time
        logger.exception(
            "synthesis_multi_phase_failed",
            analysis_id=str(analysis_id),
            elapsed_seconds=round(elapsed, 2),
            error=str(e),
            error_type=type(e).__name__,
        )
        # Emit failure heartbeat
        await _emit_synthesis_heartbeat(
            analysis_id, start_time, f"Multi-phase synthesis failed: {type(e).__name__}"
        )
        raise


# ============================================================================
# PHASE-SPECIFIC SYNTHESIS FUNCTIONS
# ============================================================================


async def _synthesize_core(
    compressed_findings: list,  # CompressedFinding from compress_findings
    conflicts: list[dict[str, str]],
    confidence_scores: dict[str, float],
    analysis_id: str,
) -> dict:  # CoreSynthesisSchema dict
    """Phase 1: Generate core synthesis (REQUIRED).

    Uses CORE_SYNTHESIS_PROMPT with compressed findings to generate:
    - executive_summary
    - key_findings
    - synthesis (technical_analysis, implementation_guidance, etc.)
    - conflicts_resolved
    - coverage_gaps
    - cross_domain_connections
    - coverage_score

    Args:
        compressed_findings: List of compressed agent findings
        conflicts: List of detected conflicts
        confidence_scores: Agent confidence scores
        analysis_id: UUID of the analysis

    Returns:
        CoreSynthesisSchema as dict

    Raises:
        Exception: If core synthesis fails (phase is required)

    """
    logger.info(
        "synthesis_phase1_core_starting",
        analysis_id=analysis_id,
        compressed_count=len(compressed_findings),
    )

    phase_start = time.time()

    try:
        # Import phase schema and prompts
        from app.domains.analysis.schemas.tasks.core_synthesis import CoreSynthesisSchema
        from app.domains.analysis.workflows.tasks.aggregation.synthesis_prompts import (
            build_core_prompt,
        )

        # Convert compressed findings to dicts for prompt building
        findings_dicts = [f.model_dump() for f in compressed_findings]

        # Build phase prompt
        user_prompt = build_core_prompt(
            compressed_findings=findings_dicts,
            conflicts=conflicts,
        )

        # Create synthesis agent with CoreSynthesisSchema
        synthesis_agent = create_structured_agent(
            system_prompt="You are synthesizing technical analysis findings into a core synthesis.",
            response_schema=CoreSynthesisSchema,
        )

        # Create fallback model with strict output (LangChain 1.2.x)
        fallback_model = get_chat_model(
            config={"configurable": {"model": settings.LLM_FALLBACK_MODEL}}
        )
        # LangChain 1.2.x: Use strict mode for exact schema compliance
        fallback_with_structure = fallback_model.with_structured_output(
            CoreSynthesisSchema, strict=True
        )

        # Attach fallback chain
        synthesis_agent_with_fallback = synthesis_agent.with_fallbacks(
            fallbacks=[fallback_with_structure],
            exceptions_to_handle=(Exception, TimeoutError, GeneratorExit),
        )

        # Invoke agent
        input_messages = {"messages": [{"role": "user", "content": user_prompt}]}

        final_result = await invoke_agent(
            agent=synthesis_agent_with_fallback,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="synthesis_phase1_core",
            timeout=SYNTHESIS_TIMEOUT // 3,  # Each phase gets 1/3 of total timeout
        )

        # Extract structured response
        structured_response = extract_structured_response(final_result, "synthesis_phase1_core")

        phase_elapsed = time.time() - phase_start
        logger.info(
            "synthesis_phase1_core_complete",
            analysis_id=analysis_id,
            phase_elapsed=round(phase_elapsed, 2),
        )

        return structured_response

    except Exception as e:
        phase_elapsed = time.time() - phase_start
        logger.exception(
            "synthesis_phase1_core_failed",
            analysis_id=analysis_id,
            phase_elapsed=round(phase_elapsed, 2),
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def _synthesize_learning(
    compressed_findings: list,  # CompressedFinding from compress_findings
    analysis_id: str,
) -> dict | None:  # LearningSynthesisSchema dict or None
    """Phase 2: Generate learning content (OPTIONAL).

    Uses LEARNING_SYNTHESIS_PROMPT with compressed findings to generate:
    - core_concepts
    - exercises
    - self_assessment

    Args:
        compressed_findings: List of compressed agent findings
        analysis_id: UUID of the analysis

    Returns:
        LearningSynthesisSchema as dict, or None on failure

    """
    logger.info(
        "synthesis_phase2_learning_starting",
        analysis_id=analysis_id,
    )

    phase_start = time.time()

    try:
        # Import phase schema and prompts
        from app.domains.analysis.schemas.tasks.learning_synthesis import LearningSynthesisSchema
        from app.domains.analysis.workflows.tasks.aggregation.synthesis_prompts import (
            build_learning_prompt,
        )

        # Convert compressed findings to dicts for prompt building
        findings_dicts = [f.model_dump() for f in compressed_findings]

        # Build phase prompt
        user_prompt = build_learning_prompt(compressed_findings=findings_dicts)

        # Create synthesis agent with LearningSynthesisSchema
        synthesis_agent = create_structured_agent(
            system_prompt="You are creating educational content from technical analysis.",
            response_schema=LearningSynthesisSchema,
        )

        # Create fallback model with strict output (LangChain 1.2.x)
        fallback_model = get_chat_model(
            config={"configurable": {"model": settings.LLM_FALLBACK_MODEL}}
        )
        # LangChain 1.2.x: Use strict mode for exact schema compliance
        fallback_with_structure = fallback_model.with_structured_output(
            LearningSynthesisSchema, strict=True
        )

        # Attach fallback chain
        synthesis_agent_with_fallback = synthesis_agent.with_fallbacks(
            fallbacks=[fallback_with_structure],
            exceptions_to_handle=(Exception, TimeoutError, GeneratorExit),
        )

        # Invoke agent
        input_messages = {"messages": [{"role": "user", "content": user_prompt}]}

        final_result = await invoke_agent(
            agent=synthesis_agent_with_fallback,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="synthesis_phase2_learning",
            timeout=SYNTHESIS_TIMEOUT // 3,  # Each phase gets 1/3 of total timeout
        )

        # Extract structured response
        structured_response = extract_structured_response(final_result, "synthesis_phase2_learning")

        phase_elapsed = time.time() - phase_start
        logger.info(
            "synthesis_phase2_learning_complete",
            analysis_id=analysis_id,
            phase_elapsed=round(phase_elapsed, 2),
        )

        return structured_response

    except (ValidationError, TimeoutError, ValueError, KeyError, TypeError) as e:
        phase_elapsed = time.time() - phase_start
        logger.warning(
            "synthesis_phase2_learning_failed_graceful_degradation",
            analysis_id=analysis_id,
            phase_elapsed=round(phase_elapsed, 2),
            error=str(e),
            error_type=type(e).__name__,
            fallback="returning_none_for_graceful_merge",
        )
        return None


async def _synthesize_docs(
    compressed_findings: list,  # CompressedFinding from compress_findings
    analysis_id: str,
) -> dict | None:  # DocsSynthesisSchema dict or None
    """Phase 3: Generate documentation content (OPTIONAL).

    Uses DOCS_SYNTHESIS_PROMPT with compressed findings to generate:
    - tldr
    - ai_assistant_prompt
    - diagrams
    - glossary

    Note: quick_reference is handled separately in aggregate_findings.py,
    not in this phase.

    Args:
        compressed_findings: List of compressed agent findings
        analysis_id: UUID of the analysis

    Returns:
        DocsSynthesisSchema as dict, or None on failure

    """
    logger.info(
        "synthesis_phase3_docs_starting",
        analysis_id=analysis_id,
    )

    phase_start = time.time()

    try:
        # Import phase schema and prompts
        from app.domains.analysis.schemas.tasks.docs_synthesis import DocsSynthesisSchema
        from app.domains.analysis.workflows.tasks.aggregation.synthesis_prompts import (
            build_docs_prompt,
        )

        # Convert compressed findings to dicts for prompt building
        findings_dicts = [f.model_dump() for f in compressed_findings]

        # Build phase prompt
        user_prompt = build_docs_prompt(compressed_findings=findings_dicts)

        # Create synthesis agent with DocsSynthesisSchema
        synthesis_agent = create_structured_agent(
            system_prompt="You are creating documentation for developers and AI assistants.",
            response_schema=DocsSynthesisSchema,
        )

        # Create fallback model with strict output (LangChain 1.2.x)
        fallback_model = get_chat_model(
            config={"configurable": {"model": settings.LLM_FALLBACK_MODEL}}
        )
        # LangChain 1.2.x: Use strict mode for exact schema compliance
        fallback_with_structure = fallback_model.with_structured_output(
            DocsSynthesisSchema, strict=True
        )

        # Attach fallback chain
        synthesis_agent_with_fallback = synthesis_agent.with_fallbacks(
            fallbacks=[fallback_with_structure],
            exceptions_to_handle=(Exception, TimeoutError, GeneratorExit),
        )

        # Invoke agent
        input_messages = {"messages": [{"role": "user", "content": user_prompt}]}

        final_result = await invoke_agent(
            agent=synthesis_agent_with_fallback,
            input_messages=input_messages,
            analysis_id=analysis_id,
            agent_type="synthesis_phase3_docs",
            timeout=SYNTHESIS_TIMEOUT // 3,  # Each phase gets 1/3 of total timeout
        )

        # Extract structured response
        structured_response = extract_structured_response(final_result, "synthesis_phase3_docs")

        phase_elapsed = time.time() - phase_start
        logger.info(
            "synthesis_phase3_docs_complete",
            analysis_id=analysis_id,
            phase_elapsed=round(phase_elapsed, 2),
        )

        return structured_response

    except (ValidationError, TimeoutError, ValueError, KeyError, TypeError) as e:
        phase_elapsed = time.time() - phase_start
        logger.warning(
            "synthesis_phase3_docs_failed_graceful_degradation",
            analysis_id=analysis_id,
            phase_elapsed=round(phase_elapsed, 2),
            error=str(e),
            error_type=type(e).__name__,
            fallback="returning_none_for_graceful_merge",
        )
        return None


# ============================================================================
# RESULT MERGING
# ============================================================================


def _merge_phase_results(
    core: dict,  # CoreSynthesisSchema dict
    learning: dict | Exception | None,  # LearningSynthesisSchema dict or failure
    docs: dict | Exception | None,  # DocsSynthesisSchema dict or failure
) -> dict[str, object]:
    """Merge phase results with graceful degradation for failures.

    Args:
        core: Core synthesis result (required, already validated as dict)
        learning: Learning synthesis result or None/Exception
        docs: Docs synthesis result or None/Exception

    Returns:
        Merged AggregatedInsights dict with all fields

    """
    # Start with core result
    result = dict(core)

    # Add learning content if available
    if isinstance(learning, dict):
        result.update(learning)
        logger.debug("merge_phase_results_learning_added")
    else:
        # Graceful degradation - empty but valid
        result["core_concepts"] = []
        result["exercises"] = []
        result["self_assessment"] = None
        logger.debug(
            "merge_phase_results_learning_graceful_degradation",
            learning_type=type(learning).__name__ if learning else "None",
        )

    # Add docs content if available
    if isinstance(docs, dict):
        result.update(docs)
        logger.debug("merge_phase_results_docs_added")
    else:
        # Graceful degradation - empty but valid
        # Note: quick_reference is handled separately in aggregate_findings.py
        result["tldr"] = None
        result["ai_assistant_prompt"] = None
        result["diagrams"] = []
        result["glossary"] = []
        logger.debug(
            "merge_phase_results_docs_graceful_degradation",
            docs_type=type(docs).__name__ if docs else "None",
        )

    logger.info(
        "merge_phase_results_complete",
        has_core=True,
        has_learning=isinstance(learning, dict),
        has_docs=isinstance(docs, dict),
    )

    return result
