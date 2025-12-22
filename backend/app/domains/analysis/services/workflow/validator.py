"""Workflow result validation service."""

from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_workflow_result(workflow_result: dict) -> list[str]:
    """Validate required workflow result fields and return missing ones.

    Args:
        workflow_result: Dictionary containing workflow execution result

    Returns:
        List of missing required field names. Empty list if all fields present.

    """
    required_fields = ["raw_content", "extraction_metadata", "content_embedding"]
    missing_fields: list[str] = []

    for field in required_fields:
        value = workflow_result.get(field)
        if not value:
            missing_fields.append(field)

    return missing_fields

