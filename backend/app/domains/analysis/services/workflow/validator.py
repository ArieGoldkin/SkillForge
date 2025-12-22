"""Workflow result validation service.

Production-grade validator using Pydantic v2 for type-safe validation
with status-aware validation rules.
"""

from pydantic import ValidationError

from app.core.logging import get_logger
from app.domains.analysis.schemas.workflow_result import WorkflowResult

logger = get_logger(__name__)


class WorkflowResultValidator:
    """Production-grade workflow result validator using Pydantic v2.

    Validates workflow results with type safety, field constraints, and
    status-aware validation rules.
    """

    def validate(
        self,
        workflow_result: dict,
        expected_status: str = "completed",
    ) -> tuple[WorkflowResult | None, list[str]]:
        """Validate workflow result and return validated object.

        Args:
            workflow_result: Raw workflow result dict
            expected_status: Expected workflow status ('completed', 'failed', etc.)

        Returns:
            Tuple of (validated_result, validation_errors)
            - validated_result: Pydantic model if valid, None if invalid
            - validation_errors: List of error messages

        """
        try:
            # Parse and validate with Pydantic
            validated = WorkflowResult.model_validate(workflow_result)

            # Status-specific validation
            missing = validated.validate_for_status(expected_status)
            if missing:
                return (
                    None,
                    [f"Missing required fields for {expected_status}: {', '.join(missing)}"],
                )

            return (validated, [])

        except ValidationError as e:
            # Extract Pydantic validation errors
            errors = self._extract_validation_errors(e)
            return (None, errors)

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(
                "validation_unexpected_error",
                error=str(e),
                exc_info=True,
            )
            return (None, [f"Validation error: {e!s}"])

    def _extract_validation_errors(self, e: ValidationError) -> list[str]:
        """Extract structured error messages from Pydantic ValidationError.

        Args:
            e: Pydantic ValidationError

        Returns:
            List of formatted error messages with field paths

        """
        errors = []
        for err in e.errors():
            field_path = ".".join(str(loc) for loc in err["loc"])
            error_msg = err["msg"]
            errors.append(f"{field_path}: {error_msg}")
        return errors


# Backward compatibility: Keep function for existing code
# Will be removed in Phase 4 when orchestrator is updated
def validate_workflow_result(workflow_result: dict) -> list[str]:
    """Legacy validator function - returns missing fields only.

    DEPRECATED: Use WorkflowResultValidator.validate() instead.
    This function is kept for backward compatibility during migration.

    Args:
        workflow_result: Dictionary containing workflow execution result

    Returns:
        List of missing required field names. Empty list if all fields present.

    """
    validator = WorkflowResultValidator()
    _validated, errors = validator.validate(workflow_result, "completed")
    if errors:
        # Extract field names from error messages for backward compatibility
        missing_fields: list[str] = []
        for error in errors:
            # Try to extract field name from error message
            if "Missing required fields" in error:
                # Extract from "Missing required fields for completed: field1, field2"
                parts = error.split(": ")
                if len(parts) > 1:
                    fields = parts[1].split(", ")
                    missing_fields.extend(fields)
            elif ":" in error:
                # Extract field name from "field_name: error message"
                field_name = error.split(":")[0]
                if field_name not in missing_fields:
                    missing_fields.append(field_name)
        return missing_fields
    return []
