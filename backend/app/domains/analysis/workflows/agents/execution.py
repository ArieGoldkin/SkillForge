"""Agent execution with tracking and error handling.

This module handles the execution of agents with progress tracking,
streaming support, error handling, and database persistence.

Redis semantic caching is integrated at the model factory level (get_chat_model),
providing automatic caching for all LLM calls without explicit cache management here.

Issue #507: Added self-correction loop with per-agent output validation.
When enabled, agents validate their output quality and can retry with
correction prompts if validation fails.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.runnables import Runnable
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MIN_AGENT_FINDINGS
from app.core.exception_utils import async_exception_context
from app.core.logging import get_logger
from app.core.timeout_config import AGENT_TIMEOUT
from app.core.tracing import update_current_observation
from app.core.types import AnalysisID
from app.domains.analysis.workflows.agents.base import emit_agent_progress
from app.domains.analysis.workflows.agents.invocation import invoke_agent
from app.domains.analysis.workflows.agents.prompt_builders import build_agent_user_prompt
from app.domains.analysis.workflows.agents.response_processing import extract_structured_response
from app.domains.analysis.workflows.agents.result_processing import (
    _count_insights,
    handle_agent_cancellation,
    handle_agent_error,
    process_agent_result,
)
from app.domains.analysis.workflows.agents.validation import (
    ValidationResult,
    get_validator,
    record_self_correction_metadata,
    run_self_correction_loop,
    validate_findings_count,
    validate_specificity_score,
)
from app.domains.analysis.workflows.agents.validation.execution_helpers import (
    ValidationCheckResult,
)

logger = get_logger(__name__)

# Specificity validation configuration
# Can be overridden via environment variable for testing (set to 0.0 to disable)


def get_specificity_min_score() -> float:
    """Get specificity minimum score from environment or default.

    Returns:
        Minimum specificity score (0.0-1.0). 0.0 disables validation.

    """
    return float(os.environ.get("SPECIFICITY_MIN_SCORE", "0.70"))


def get_specificity_max_retries() -> int:
    """Get maximum specificity retries from environment or default.

    Returns:
        Maximum number of retries (default: 1)

    """
    return int(os.environ.get("SPECIFICITY_MAX_RETRIES", "1"))


def get_min_agent_findings() -> int:
    """Get minimum required findings from environment or default.

    Issue #507: Can be set to 0 to disable empty findings validation for tests.

    Returns:
        Minimum findings required (default: MIN_AGENT_FINDINGS)

    """
    return int(os.environ.get("MIN_AGENT_FINDINGS", str(MIN_AGENT_FINDINGS)))


def get_self_correction_enabled() -> bool:
    """Get self-correction enabled flag from environment or default.

    Issue #507: Master switch for per-agent output validation.

    Returns:
        True if self-correction is enabled (default: True)

    """
    return os.environ.get("SELF_CORRECTION_ENABLED", "true").lower() == "true"


def get_self_correction_max_retries() -> int:
    """Get maximum self-correction retries from environment or default.

    Issue #507: Controls how many times an agent can retry after validation failure.

    Returns:
        Maximum retries (default: 2)

    """
    return int(os.environ.get("SELF_CORRECTION_MAX_RETRIES", "2"))


def get_self_correction_compact_prompts() -> bool:
    """Get compact prompts flag from environment or default.

    Issue #507: Use smaller correction prompts to save tokens.

    Returns:
        True if compact prompts should be used (default: False)

    """
    return os.environ.get("SELF_CORRECTION_COMPACT_PROMPTS", "false").lower() == "true"


@dataclass
class AgentExecutionParams:
    """Parameters for agent execution.

    Groups agent execution parameters to reduce function complexity.
    """

    agent: Runnable
    content: str
    content_type: str
    analysis_id: AnalysisID
    agent_type: str
    proactive_context: str = ""  # Issue #300: Proactive memory context


@dataclass
class SelfCorrectionContext:
    """Tracks self-correction state during agent execution.

    Issue #507: Used to track validation attempts and results for observability.
    """

    enabled: bool = True
    max_retries: int = 2
    current_attempt: int = 0
    validation_results: list[ValidationResult] = field(default_factory=list)
    correction_count: int = 0  # Number of corrections actually applied

    def record_validation(self, result: ValidationResult) -> None:
        """Record a validation result."""
        self.validation_results.append(result)
        if not result.is_valid:
            self.correction_count += 1

    def should_retry(self) -> bool:
        """Check if we should retry based on last validation."""
        if not self.validation_results:
            return False
        last_result = self.validation_results[-1]
        return (
            not last_result.is_valid
            and last_result.retry_recommended
            and self.current_attempt < self.max_retries
        )

    def to_metadata(self) -> dict[str, Any]:
        """Convert to metadata dict for Langfuse/observability."""
        return {
            "self_correction_enabled": self.enabled,
            "self_correction_count": self.correction_count,
            "final_attempt_number": self.current_attempt + 1,
            "validation_passed": (
                self.validation_results[-1].is_valid if self.validation_results else True
            ),
            "all_issues": [
                issue
                for result in self.validation_results
                for issue in result.issues[:3]  # First 3 issues per validation
            ],
        }


@dataclass
class AgentExecutionConfig:
    """Configuration for agent execution.

    Groups agent execution configuration to reduce function complexity.

    Issue #299-304: Added specificity_threshold to allow content-aware threshold adjustment.
    Issue #507: Added self_correction_context for tracking validation state.
    """

    session: AsyncSession
    max_content_length: int = 12000
    timeout: float = AGENT_TIMEOUT
    specificity_threshold: float | None = None  # None = use default from env
    self_correction: SelfCorrectionContext = field(default_factory=SelfCorrectionContext)


async def _run_agent_with_tracking_impl(
    params: AgentExecutionParams,
    config: AgentExecutionConfig,
) -> dict[str, object]:
    """Implement agent execution with tracking.

    This function contains the actual logic. The public `run_agent_with_tracking`
    function wraps this with @traceable for Langfuse instrumentation.

    Redis semantic caching is automatically enabled for all agents via the model
    factory (get_chat_model). No explicit cache management needed here.

    Args:
        params: Agent execution parameters
        config: Agent execution configuration

    Returns:
        Dictionary with agent_type, findings, confidence_score, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    start_time = time.time()

    # Emit SSE event: agent started
    await emit_agent_progress(params.analysis_id, params.agent_type, "running")

    logger.info(
        "agent_started",
        agent_type=params.agent_type,
        analysis_id=params.analysis_id,
        content_type=params.content_type,
        content_length=len(params.content),
    )

    try:
        async with async_exception_context(
            operation="execute_agent",
            agent_type=params.agent_type,
            analysis_id=str(params.analysis_id),
            content_type=params.content_type,
        ):
            # Build user prompt and initialize execution context
            user_prompt = build_agent_user_prompt(
                content=params.content,
                content_type=params.content_type,
                max_length=config.max_content_length,
                proactive_context=params.proactive_context,
            )

            input_messages = {"messages": [{"role": "user", "content": user_prompt}]}

            # Initialize validation configuration
            max_retries = get_specificity_max_retries()
            min_score = (
                config.specificity_threshold
                if config.specificity_threshold is not None
                else get_specificity_min_score()
            )
            min_findings = get_min_agent_findings()

            # Issue #507: Initialize self-correction context
            self_correction_enabled = get_self_correction_enabled()
            self_correction_ctx = SelfCorrectionContext(
                enabled=self_correction_enabled,
                max_retries=get_self_correction_max_retries(),
            )
            validator = get_validator(params.agent_type) if self_correction_enabled else None
            use_compact_prompts = get_self_correction_compact_prompts()

            # Execute retry loop with validation
            findings = await _execute_agent_retry_loop(
                params=params,
                config=config,
                input_messages=input_messages,
                max_retries=max_retries,
                min_score=min_score,
                min_findings=min_findings,
                self_correction_ctx=self_correction_ctx,
                validator=validator,
                use_compact_prompts=use_compact_prompts,
            )

            # Issue #507: Record self-correction metadata for Langfuse observability
            record_self_correction_metadata(
                context=self_correction_ctx,
                agent_type=params.agent_type,
                analysis_id=str(params.analysis_id),
                update_observation_fn=update_current_observation,
            )

            # Process and persist result
            return await process_agent_result(
                findings=findings or {},
                analysis_id=params.analysis_id,
                agent_type=params.agent_type,
                session=config.session,
                start_time=start_time,
            )

    except GeneratorExit:
        await handle_agent_cancellation(
            analysis_id=params.analysis_id,
            agent_type=params.agent_type,
            start_time=start_time,
        )
        raise
    except Exception as e:
        await handle_agent_error(
            error=e,
            analysis_id=params.analysis_id,
            agent_type=params.agent_type,
            start_time=start_time,
        )
        raise


async def _execute_agent_retry_loop(  # noqa: PLR0913
    params: AgentExecutionParams,
    config: AgentExecutionConfig,
    input_messages: dict[str, Any],
    max_retries: int,
    min_score: float,
    min_findings: int,
    self_correction_ctx: SelfCorrectionContext,
    validator: Any | None,
    use_compact_prompts: bool,
) -> dict[str, Any]:
    """Execute agent with retry loop for validation failures.

    Extracted from _run_agent_with_tracking_impl to reduce function complexity.

    Args:
        params: Agent execution parameters
        config: Agent execution configuration
        input_messages: Initial conversation messages
        max_retries: Maximum retry attempts for specificity/findings validation
        min_score: Minimum specificity score threshold
        min_findings: Minimum required findings count
        self_correction_ctx: Self-correction state tracking
        validator: Agent-specific output validator
        use_compact_prompts: Whether to use compact correction prompts

    Returns:
        Validated agent findings dictionary

    Raises:
        ValueError: If validation fails after all retries
        TimeoutError: If agent execution times out

    """
    attempts = 0
    findings: dict[str, Any] = {}
    current_messages = input_messages

    while attempts <= max_retries:
        # Invoke agent
        final_result = await _invoke_agent_with_timeout(params, config, current_messages)

        # Issue #610: Handle circuit breaker open - agent was skipped
        if isinstance(final_result, dict) and final_result.get("status") == "skipped":
            logger.info(
                "agent_skipped_due_to_circuit_breaker",
                agent_type=params.agent_type,
                analysis_id=str(params.analysis_id),
                skipped_reason=final_result.get("skipped_reason", "Circuit breaker open"),
            )
            # Return findings with skipped status - will be handled by aggregation
            return final_result

        findings = extract_structured_response(
            final_result, params.agent_type, analysis_id=str(params.analysis_id)
        )

        # Validate findings count
        insights_count = _count_insights(findings, params.agent_type)
        findings_check = validate_findings_count(
            agent_type=params.agent_type,
            analysis_id=str(params.analysis_id),
            insights_count=insights_count,
            min_findings=min_findings,
            current_attempt=attempts,
            max_retries=max_retries,
        )

        # Special case for trend_validator: Allow empty trend_assessments when other insights exist
        # This handles meta-content articles that have no technologies to validate
        if (
            params.agent_type == "trend_validator"
            and insights_count == 0
            and findings_check.should_fail
        ):
            # Check if other fields have valuable content
            has_other_insights = any(
                [
                    findings.get("future_outlook"),
                    findings.get("recommendation"),
                    findings.get("modern_alternatives"),
                ]
            )
            if has_other_insights:
                # Legitimately empty - no technologies to validate
                logger.info(
                    "trend_validator_empty_but_has_insights",
                    analysis_id=str(params.analysis_id),
                    future_outlook=bool(findings.get("future_outlook")),
                    recommendation=bool(findings.get("recommendation")),
                    modern_alternatives=bool(findings.get("modern_alternatives")),
                )
                # Override validation result - mark as passed but will be "no_data" in aggregation
                findings_check = ValidationCheckResult(
                    passed=True,
                    should_retry=False,
                    should_fail=False,
                )
                # Mark findings as "no_data" for aggregation processing
                findings["status"] = "no_data"
                findings["no_data_reason"] = (
                    "No technologies to validate (expected for meta-content)"
                )

        if findings_check.should_fail:
            raise ValueError(findings_check.error_message)
        if findings_check.should_retry:
            attempts += 1
            continue

        # Validate specificity score
        specificity_check = validate_specificity_score(
            findings=findings,
            agent_type=params.agent_type,
            analysis_id=str(params.analysis_id),
            min_score=min_score,
            current_attempt=attempts,
            max_retries=max_retries,
        )

        if specificity_check.should_fail:
            raise ValueError(specificity_check.error_message)
        if specificity_check.should_retry:
            attempts += 1
            continue

        # Issue #507: Self-correction validation
        correction_result = await run_self_correction_loop(
            input_messages=current_messages,
            current_output=findings,
            agent_type=params.agent_type,
            analysis_id=str(params.analysis_id),
            context=self_correction_ctx,
            validator=validator,
            use_compact_prompts=use_compact_prompts,
            emit_progress_fn=emit_agent_progress,
        )

        if correction_result.should_continue_loop and correction_result.updated_messages:
            current_messages = correction_result.updated_messages
            continue

        findings = correction_result.final_output
        break

    return findings


async def _invoke_agent_with_timeout(
    params: AgentExecutionParams,
    config: AgentExecutionConfig,
    input_messages: dict[str, Any],
) -> Any:
    """Invoke agent with timeout handling.

    Extracted to reduce complexity in retry loop.

    Args:
        params: Agent execution parameters
        config: Agent execution configuration
        input_messages: Conversation messages for agent

    Returns:
        Raw agent response

    Raises:
        TimeoutError: If agent execution exceeds timeout

    """
    try:
        return await invoke_agent(
            agent=params.agent,
            input_messages=input_messages,
            analysis_id=params.analysis_id,
            agent_type=params.agent_type,
            timeout=config.timeout,
        )
    except TimeoutError as exc:
        logger.exception(
            "timeout_error",
            context=f"Agent {params.agent_type} execution",
            timeout=config.timeout,
            agent_type=params.agent_type,
            analysis_id=params.analysis_id,
        )
        msg = f"Agent {params.agent_type} execution exceeded timeout of {config.timeout}s"
        raise TimeoutError(msg) from exc


async def run_agent_with_tracking(  # noqa: PLR0913
    agent: Runnable,
    content: str,
    content_type: str,
    analysis_id: AnalysisID,
    agent_type: str,
    session: AsyncSession,
    max_content_length: int = 12000,
    proactive_context: str = "",
    specificity_threshold: float | None = None,
) -> dict[str, object]:
    """Run an agent with progress tracking, error handling, and database persistence.

    Note: This function is NOT traced with @robust_traceable because the calling
    node (e.g., tech_comparator_node) is already traced. Adding tracing here would
    create duplicate traces in Langfuse.

    Note: This function accepts 9 parameters for backward compatibility with existing callers.
    Internally, parameters are grouped into AgentExecutionParams and AgentExecutionConfig
    dataclasses to reduce complexity. Future refactoring could change the signature to accept
    dataclasses directly.

    Args:
        agent: Agent instance to run
        content: Content to analyze
        content_type: Type of content (article, video, repo)
        analysis_id: UUID of the analysis
        agent_type: Type of agent for logging and storage
        session: Database session for persistence
        max_content_length: Maximum content length to send to agent
        proactive_context: Formatted memory context from past analyses (Issue #300)
        specificity_threshold: Optional threshold override (Issue #299-304).
            If None, uses default from SPECIFICITY_MIN_SCORE env var (0.70).
            Lower thresholds (e.g., 0.55) for conceptual-only content.

    Returns:
        Dictionary with agent_type, findings, confidence_score, processing_time_ms

    Raises:
        Exception: If agent execution fails

    """
    # Group parameters into dataclasses to reduce function complexity
    params = AgentExecutionParams(
        agent=agent,
        content=content,
        content_type=content_type,
        analysis_id=analysis_id,
        agent_type=agent_type,
        proactive_context=proactive_context,
    )
    config = AgentExecutionConfig(
        session=session,
        max_content_length=max_content_length,
        specificity_threshold=specificity_threshold,
    )

    # Call implementation directly - no tracing here since the node wrapper already traces
    return await _run_agent_with_tracking_impl(params=params, config=config)
