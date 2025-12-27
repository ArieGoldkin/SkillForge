"""Response processing and validation for agent execution.

This module handles extraction and validation of structured responses
from agent execution results.

Issue #586: Multi-provider structured output compatibility.
- Anthropic/OpenAI: Return wrapped format {"structured_response": PydanticModel}
- Gemini 2.5+: Return PydanticModel directly via `with_structured_output(strict=True)`

2025 Best Practice: Use duck typing (`hasattr(x, "model_dump")`) to detect Pydantic
models instead of isinstance() checks, as this works across all Pydantic versions.
"""

from typing import Any, Protocol, cast, runtime_checkable

from app.core.logging import get_logger


@runtime_checkable
class PydanticModel(Protocol):
    """Protocol for Pydantic model duck typing.

    Allows type checker to understand objects with model_dump() method.
    """

    def model_dump(self) -> dict[str, Any]:
        """Convert model to dictionary."""
        ...


logger = get_logger(__name__)


def extract_structured_response(
    final_result: dict[str, object] | Any | None,
    agent_type: str,
) -> dict[str, object]:
    """Extract and validate structured response from agent result.

    Handles multiple LLM provider response formats:
    1. Direct Pydantic model (Gemini 2.5+ pattern)
    2. Wrapped format {"structured_response": PydanticModel} (Anthropic/OpenAI)

    Args:
        final_result: Result from agent execution - either a Pydantic model
            (Gemini) or a dict with "structured_response" key (Anthropic/OpenAI)
        agent_type: Type of agent for error messages

    Returns:
        Dictionary of findings from structured response

    Raises:
        RuntimeError: If no result or no structured_response found
        TypeError: If result is invalid type or not a Pydantic model

    """
    if final_result is None:
        msg = f"Agent {agent_type} returned no result"
        raise RuntimeError(msg)

    # Case 1: Direct Pydantic model (Gemini 2.5+ pattern)
    # Gemini's with_structured_output(strict=True) returns the model directly
    # Use Protocol-based isinstance() for type-safe duck typing (2025 best practice)
    if isinstance(final_result, PydanticModel):
        logger.debug(
            "extracted_direct_pydantic_model",
            agent_type=agent_type,
            model_type=type(final_result).__name__,
        )
        return cast("dict[str, object]", final_result.model_dump())

    # Case 2: Wrapped format (Anthropic/OpenAI pattern)
    # These providers wrap the model in {"structured_response": model}
    if isinstance(final_result, dict):
        structured_response = final_result.get("structured_response")
        if structured_response is None:
            msg = f"Agent {agent_type} did not return structured_response"
            raise RuntimeError(msg)

        # Validate wrapped value is a Pydantic model using Protocol
        if not isinstance(structured_response, PydanticModel):
            msg = f"Agent {agent_type} structured_response is not a Pydantic model"
            raise TypeError(msg)

        logger.debug(
            "extracted_wrapped_pydantic_model",
            agent_type=agent_type,
            model_type=type(structured_response).__name__,
        )
        return cast("dict[str, object]", structured_response.model_dump())

    # Case 3: Unsupported format
    msg = f"Agent {agent_type} returned invalid result type: {type(final_result)}"
    raise TypeError(msg)
