"""Self-correction loop execution for agent outputs.

Issue #507: Handles the retry loop when agent output fails validation.
This module extracts the self-correction logic from execution.py to reduce
function complexity and improve maintainability.

Usage:
    from app.domains.analysis.workflows.agents.validation.self_correction import (
        run_self_correction_loop,
        SelfCorrectionResult,
    )

    result = await run_self_correction_loop(
        input_messages=messages,
        current_output=findings,
        agent_type="key_insights",
        analysis_id=str(analysis_id),
        context=self_correction_ctx,
        validator=validator,
        use_compact_prompts=False,
        emit_progress_fn=emit_agent_progress,
    )
"""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from app.core.logging import get_logger
from app.core.tracing import traced_tool, update_current_observation
from app.domains.analysis.workflows.agents.validation.correction_prompts import (
    build_correction_prompt,
)
from app.domains.analysis.workflows.agents.validation.output_validators import (
    AgentOutputValidator,
)

logger = get_logger(__name__)


@dataclass
class SelfCorrectionResult:
    """Result of self-correction loop execution.

    Attributes:
        final_output: The final agent output (may be corrected or original)
        validation_passed: Whether the final output passed validation
        corrections_applied: Number of correction attempts made
        should_continue_loop: Whether the outer retry loop should continue

    """

    final_output: dict[str, Any]
    validation_passed: bool
    corrections_applied: int
    should_continue_loop: bool
    updated_messages: dict[str, Any] | None = None  # For retry with correction prompt


@traced_tool("run_self_correction_loop", tags=["self_correction", "retry"])
async def run_self_correction_loop(  # noqa: PLR0913
    input_messages: dict[str, Any],
    current_output: dict[str, Any],
    agent_type: str,
    analysis_id: str,
    context: Any,  # SelfCorrectionContext from execution.py
    validator: AgentOutputValidator | None,
    use_compact_prompts: bool,
    emit_progress_fn: Callable[..., Coroutine[Any, Any, None]] | None = None,
) -> SelfCorrectionResult:
    """Execute self-correction validation loop.

    This function handles the validation and retry logic for agent outputs.
    If validation fails and retry is recommended, it builds a correction prompt
    and returns updated messages for the next invocation.

    Args:
        input_messages: Current conversation messages
        current_output: Agent output to validate
        agent_type: Type of agent for logging
        analysis_id: Analysis ID for logging
        context: SelfCorrectionContext tracking validation state
        validator: Agent-specific validator (or None if disabled)
        use_compact_prompts: Whether to use compact correction prompts
        emit_progress_fn: Optional async function to emit SSE progress events

    Returns:
        SelfCorrectionResult with validation outcome and next steps

    """
    # If validation is disabled, return immediately
    if not validator or not context.enabled:
        return SelfCorrectionResult(
            final_output=current_output,
            validation_passed=True,
            corrections_applied=0,
            should_continue_loop=False,
        )

    # Validate the current output
    validation_result = validator.validate(current_output)
    context.record_validation(validation_result)

    # If valid, we're done
    if validation_result.is_valid:
        return SelfCorrectionResult(
            final_output=current_output,
            validation_passed=True,
            corrections_applied=context.correction_count,
            should_continue_loop=False,
        )

    # Validation failed - log the issues
    logger.warning(
        "agent_self_correction_validation_failed",
        agent_type=agent_type,
        analysis_id=analysis_id,
        attempt=context.current_attempt + 1,
        issues=validation_result.issues[:5],  # First 5 issues
        retry_recommended=validation_result.retry_recommended,
    )

    # Update Langfuse observation with validation failure details
    update_current_observation(
        metadata={
            "validation_passed": False,
            "issues_count": len(validation_result.issues),
            "retry_recommended": validation_result.retry_recommended,
            "attempt": context.current_attempt + 1,
        }
    )

    # Check if we should retry with correction prompt
    if context.should_retry():
        context.current_attempt += 1

        # Build correction prompt with issues and hints
        correction_prompt = build_correction_prompt(
            issues=validation_result.issues,
            correction_hints=validator.get_correction_hints(),
            attempt_number=context.current_attempt + 1,
            compact=use_compact_prompts,
        )

        # Augment input with previous output and correction guidance
        # This creates a conversation: user -> assistant (failed) -> user (fix)
        updated_messages = {
            "messages": [
                *input_messages["messages"],
                {
                    "role": "assistant",
                    "content": str(current_output),
                },
                {
                    "role": "user",
                    "content": correction_prompt,
                },
            ]
        }

        logger.info(
            "agent_self_correction_retry",
            agent_type=agent_type,
            analysis_id=analysis_id,
            attempt=context.current_attempt + 1,
            issues_count=len(validation_result.issues),
        )

        # Emit SSE event for self-correction if callback provided
        if emit_progress_fn:
            await emit_progress_fn(analysis_id, agent_type, "correcting")

        return SelfCorrectionResult(
            final_output=current_output,
            validation_passed=False,
            corrections_applied=context.correction_count,
            should_continue_loop=True,
            updated_messages=updated_messages,
        )

    # Max retries exhausted or retry not recommended
    logger.warning(
        "agent_self_correction_exhausted",
        agent_type=agent_type,
        analysis_id=analysis_id,
        correction_count=context.correction_count,
        issues=validation_result.issues[:3],
    )

    # Continue with degraded output (don't fail entirely)
    return SelfCorrectionResult(
        final_output=current_output,
        validation_passed=False,
        corrections_applied=context.correction_count,
        should_continue_loop=False,
    )


def record_self_correction_metadata(
    context: Any,  # SelfCorrectionContext
    agent_type: str,
    analysis_id: str,
    update_observation_fn: Callable[..., None],
) -> None:
    """Record self-correction metadata for Langfuse observability.

    Args:
        context: SelfCorrectionContext with validation state
        agent_type: Type of agent
        analysis_id: Analysis ID for logging
        update_observation_fn: Function to update Langfuse observation

    """
    if not context.enabled:
        return

    self_correction_metadata = context.to_metadata()
    update_observation_fn(
        metadata={
            **self_correction_metadata,
            "agent_type": agent_type,
        },
    )

    # Log self-correction summary if corrections were applied
    if context.correction_count > 0:
        logger.info(
            "agent_self_correction_summary",
            agent_type=agent_type,
            analysis_id=analysis_id,
            correction_count=context.correction_count,
            final_attempt=context.current_attempt + 1,
            validation_passed=self_correction_metadata["validation_passed"],
        )
