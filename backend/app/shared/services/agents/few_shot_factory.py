"""Few-Shot Agent Factory for Phase 1, Week 2.1.

This factory wraps agent creation with few-shot example injection capabilities,
supporting A/B testing between control (no examples) and treatment (with examples).

Architecture:
- Control variant: Returns base agent without modification
- Treatment variant: Retrieves relevant examples via semantic search, formats them
  into the agent prompt, and creates an enhanced agent
- Graceful degradation: Falls back to control variant on any errors

Example:
    >>> async with AsyncSessionLocal() as session:
    ...     agent = await create_few_shot_agent(
    ...         agent_type="tech_comparator",
    ...         content="Comparing React vs Vue performance",
    ...         base_agent_factory=create_base_agent,
    ...         session=session,
    ...         embedding_service=embedding_service,
    ...         variant="treatment",
    ...     )

"""

import time
from collections.abc import Callable
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.examples import ExampleSelectionResult, SemanticExampleSelector

logger = get_logger(__name__)

# Token budget for few-shot examples (adjusted for formatting overhead)
MAX_EXAMPLE_TOKENS = 1500
# Estimated tokens per example (rough approximation)
AVG_TOKENS_PER_EXAMPLE = 400
# Content preview length for example formatting
CONTENT_PREVIEW_MAX_CHARS = 200


def _format_examples_for_prompt(result: ExampleSelectionResult) -> str:
    """Format selected examples into a prompt template.

    Creates a structured prompt section with examples showing input → output patterns.

    Args:
        result: Selection result with examples and metadata

    Returns:
        Formatted string for injection into agent prompt

    Example:
        >>> formatted = _format_examples_for_prompt(result)
        >>> "EXAMPLE 1" in formatted
        True

    """
    if not result.examples:
        return ""

    lines = [
        "=== FEW-SHOT EXAMPLES ===",
        "",
        "Below are high-quality examples from similar analyses to guide your response:",
        "",
    ]

    for i, example in enumerate(result.examples, 1):
        lines.append(f"EXAMPLE {i}:")
        lines.append(f"Input: {example.input_summary}")

        if example.input_content_preview:
            preview = (
                example.input_content_preview[:CONTENT_PREVIEW_MAX_CHARS] + "..."
                if len(example.input_content_preview) > CONTENT_PREVIEW_MAX_CHARS
                else example.input_content_preview
            )
            lines.append(f"Content Preview: {preview}")

        lines.append(f"Output: {example.output_example}")

        if example.context_note:
            lines.append(f"Note: {example.context_note}")

        if example.quality_score:
            lines.append(f"Quality Score: {example.quality_score:.2f}")

        if example.similarity_distance is not None:
            lines.append(f"Relevance: {1 - example.similarity_distance:.2f}")

        lines.append("")  # Blank line between examples

    lines.append("=== END OF EXAMPLES ===")
    lines.append("")
    lines.append(
        "Use these examples as guidance for structure and quality. "
        "Adapt the pattern to the current content."
    )
    lines.append("")

    return "\n".join(lines)


def _estimate_token_count(text: str) -> int:
    """Estimate token count for text.

    Uses simple character-based approximation (4 chars ≈ 1 token).
    This is a rough estimate; actual tokenization may differ.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count

    """
    return len(text) // 4


def _truncate_examples_to_budget(
    result: ExampleSelectionResult,
    max_tokens: int = MAX_EXAMPLE_TOKENS,
) -> ExampleSelectionResult:
    """Truncate examples to fit within token budget.

    Args:
        result: Selection result with examples
        max_tokens: Maximum allowed tokens for examples

    Returns:
        New result with truncated examples list

    """
    if not result.examples:
        return result

    # Try including examples one by one until budget exceeded
    included_examples = []
    total_tokens = 0

    for example in result.examples:
        # Estimate tokens for this example
        example_text = (
            f"{example.input_summary} {example.output_example}{example.context_note or ''}"
        )
        example_tokens = _estimate_token_count(example_text)

        if total_tokens + example_tokens > max_tokens:
            break

        included_examples.append(example)
        total_tokens += example_tokens

    logger.info(
        "few_shot_examples_truncated",
        original_count=len(result.examples),
        included_count=len(included_examples),
        estimated_tokens=total_tokens,
        max_tokens=max_tokens,
    )

    return ExampleSelectionResult(
        examples=included_examples,
        total_candidates=result.total_candidates,
        selection_strategy=result.selection_strategy,
        avg_quality_score=result.avg_quality_score,
        avg_similarity_distance=result.avg_similarity_distance,
    )


async def create_few_shot_agent(  # noqa: PLR0913 - Factory function needs multiple deps
    agent_type: str,
    content: str,
    base_agent_factory: Callable[..., Any],
    session: AsyncSession,
    embedding_service: EmbeddingService,
    variant: Literal["control", "treatment"] = "treatment",
    max_examples: int = 5,
    min_quality_score: float = 0.8,
    **factory_kwargs: Any,
) -> Any:
    """Create agent with optional few-shot example injection.

    This factory function wraps agent creation with A/B testing support for
    few-shot prompting. The control variant creates a standard agent, while
    the treatment variant retrieves relevant examples and injects them into
    the agent's system prompt.

    Args:
        agent_type: Type of agent (e.g., 'tech_comparator', 'security_auditor')
        content: Input content for analysis (used for semantic search)
        base_agent_factory: Factory function that creates the base agent.
            Should accept (system_prompt, **kwargs) and return agent instance.
        session: Database session for example retrieval
        embedding_service: Service for generating embeddings
        variant: A/B test variant ('control' or 'treatment')
        max_examples: Maximum examples to retrieve (default: 5)
        min_quality_score: Minimum quality threshold (default: 0.8)
        **factory_kwargs: Additional kwargs passed to base_agent_factory

    Returns:
        Agent instance (control returns base agent, treatment adds examples)

    Raises:
        ValueError: If required parameters are invalid
        Exception: Re-raises if base_agent_factory fails (after logging)

    Example:
        >>> # Control variant (no examples)
        >>> agent = await create_few_shot_agent(
        ...     agent_type="tech_comparator",
        ...     content="React hooks vs class components",
        ...     base_agent_factory=create_structured_agent,
        ...     session=session,
        ...     embedding_service=embedding_service,
        ...     variant="control",
        ...     system_prompt="You are a tech comparator",
        ...     response_schema=TechComparison,
        ... )
        >>>
        >>> # Treatment variant (with examples)
        >>> agent = await create_few_shot_agent(
        ...     agent_type="tech_comparator",
        ...     content="React hooks vs class components",
        ...     base_agent_factory=create_structured_agent,
        ...     session=session,
        ...     embedding_service=embedding_service,
        ...     variant="treatment",
        ...     max_examples=3,
        ...     system_prompt="You are a tech comparator",
        ...     response_schema=TechComparison,
        ... )

    """
    # Validate inputs
    if not agent_type or not agent_type.strip():
        msg = "agent_type cannot be empty"
        logger.error("few_shot_factory_invalid_agent_type")
        raise ValueError(msg)

    if not content or not content.strip():
        msg = "content cannot be empty"
        logger.error("few_shot_factory_invalid_content")
        raise ValueError(msg)

    if not callable(base_agent_factory):
        msg = "base_agent_factory must be callable"
        logger.error("few_shot_factory_invalid_factory")
        raise TypeError(msg)

    # Control variant: return base agent without modification
    if variant == "control":
        logger.info(
            "few_shot_factory_control_variant",
            agent_type=agent_type,
            variant=variant,
        )
        try:
            return base_agent_factory(**factory_kwargs)
        except Exception as e:
            logger.error(
                "few_shot_factory_base_agent_creation_failed",
                agent_type=agent_type,
                variant=variant,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise

    # Treatment variant: retrieve examples and inject into prompt
    start_time = time.perf_counter()

    try:
        # Retrieve relevant examples via semantic search
        selector = SemanticExampleSelector(session, embedding_service)

        selection_result = await selector.select_examples(
            content=content,
            agent_type=agent_type,
            max_examples=max_examples,
            min_quality_score=min_quality_score,
        )

        retrieval_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "few_shot_examples_retrieved",
            agent_type=agent_type,
            num_examples=len(selection_result.examples),
            total_candidates=selection_result.total_candidates,
            avg_quality_score=selection_result.avg_quality_score,
            avg_similarity_distance=selection_result.avg_similarity_distance,
            retrieval_time_ms=retrieval_time_ms,
        )

        # If no examples found, fall back to control variant
        if not selection_result.examples:
            logger.warning(
                "few_shot_no_examples_found",
                agent_type=agent_type,
                total_candidates=selection_result.total_candidates,
                fallback="control_variant",
            )
            return base_agent_factory(**factory_kwargs)

        # Truncate examples to fit token budget
        truncated_result = _truncate_examples_to_budget(selection_result)

        # Format examples for prompt injection
        examples_text = _format_examples_for_prompt(truncated_result)
        estimated_tokens = _estimate_token_count(examples_text)

        # Inject examples into system prompt
        # Assumes factory_kwargs contains 'system_prompt' key
        original_prompt = factory_kwargs.get("system_prompt", "")
        if not original_prompt:
            logger.warning(
                "few_shot_no_system_prompt",
                agent_type=agent_type,
                fallback="control_variant",
            )
            return base_agent_factory(**factory_kwargs)

        # Prepend examples to system prompt (examples come first for context)
        enhanced_prompt = f"{examples_text}\n\n{original_prompt}"

        # Update factory_kwargs with enhanced prompt
        enhanced_kwargs = {**factory_kwargs, "system_prompt": enhanced_prompt}

        # Create agent with enhanced prompt
        agent = base_agent_factory(**enhanced_kwargs)

        total_time_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "few_shot_agent_created",
            agent_type=agent_type,
            variant=variant,
            num_examples_used=len(truncated_result.examples),
            estimated_tokens=estimated_tokens,
            retrieval_time_ms=retrieval_time_ms,
            total_time_ms=total_time_ms,
        )

        return agent

    except Exception as e:  # noqa: BLE001 - Intentional catch-all for graceful degradation
        # Graceful degradation: fall back to control variant on any error
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.warning(
            "few_shot_factory_error_fallback",
            agent_type=agent_type,
            error=str(e),
            error_type=type(e).__name__,
            elapsed_ms=elapsed_ms,
            fallback="control_variant",
            exc_info=True,
        )

        # Return base agent without examples
        try:
            return base_agent_factory(**factory_kwargs)
        except Exception as base_error:
            logger.error(
                "few_shot_factory_fallback_failed",
                agent_type=agent_type,
                error=str(base_error),
                error_type=type(base_error).__name__,
                exc_info=True,
            )
            raise
