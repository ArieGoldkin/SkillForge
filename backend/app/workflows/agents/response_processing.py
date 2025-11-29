"""Response processing and validation for agent execution.

This module handles extraction and validation of structured responses
from agent execution results.
"""

from typing import cast

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_structured_response(
    final_result: dict[str, object] | None,
    agent_type: str,
) -> dict[str, object]:
    """Extract and validate structured response from agent result.

    Args:
        final_result: Result dictionary from agent execution
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
    if not isinstance(final_result, dict):
        msg = f"Agent {agent_type} returned invalid result type: {type(final_result)}"
        raise TypeError(msg)
    structured_response = final_result.get("structured_response")
    if structured_response is None:
        msg = f"Agent {agent_type} did not return structured_response"
        raise RuntimeError(msg)

    # Convert Pydantic model to dict for storage
    # structured_response is a Pydantic BaseModel, which has model_dump()
    if not hasattr(structured_response, "model_dump"):
        msg = f"Agent {agent_type} structured_response is not a Pydantic model"
        raise TypeError(msg)
    # Pydantic's model_dump() returns dict[str, Any] but we know it's dict[str, object]
    findings = cast(dict[str, object], structured_response.model_dump())  # type: ignore[attr-defined]

    return findings


