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
