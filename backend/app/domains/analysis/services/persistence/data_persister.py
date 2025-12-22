"""Data persistence service for analysis records.

Production-grade persister with validation before write and fail-fast error handling.
"""

import uuid

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal
from app.domains.analysis.schemas.workflow_result import WorkflowResult
from app.domains.analysis.services.workflow.validator import WorkflowResultValidator

logger = get_logger(__name__)


class DataPersister:
    """Service for persisting workflow results to analysis records.

    Validates data before persistence and fails fast on invalid data.
    No silent degradation - exceptions raised for invalid data.
    """

    def __init__(self) -> None:
        """Initialize persister with validator."""
        self.validator = WorkflowResultValidator()

    async def persist(
        self,
        analysis_id: uuid.UUID,
        workflow_result: dict | WorkflowResult,
        validate: bool = True,
    ) -> bool:
        """Persist workflow results to the analysis record.

        Validates data before persistence and fails fast on invalid data.
        Accepts either dict (validated) or WorkflowResult (used directly).

        Args:
            analysis_id: UUID of the analysis to update
            workflow_result: Dictionary or WorkflowResult containing workflow state
            validate: Whether to validate dict before persistence (default: True)

        Returns:
            bool: True if data was persisted successfully

        Raises:
            ValueError: If validation fails or analysis not found
            RuntimeError: If persistence fails due to database error

        """
        # Validate dict if provided, use WorkflowResult directly
        validated_workflow_result: WorkflowResult
        if isinstance(workflow_result, dict):
            if validate:
                validated, errors = self.validator.validate(workflow_result, "completed")
                if errors:
                    error_msg = f"Invalid workflow result: {errors}"
                    raise ValueError(error_msg)
                if validated is None:
                    error_msg = "Validation returned None unexpectedly"
                    raise ValueError(error_msg)
                validated_workflow_result = validated
            else:
                # If validation disabled, still need to convert to WorkflowResult
                # This is for edge cases where caller knows data is valid
                try:
                    validated_workflow_result = WorkflowResult.model_validate(workflow_result)
                except Exception as e:
                    error_msg = (
                        f"Invalid workflow result (validation disabled but conversion failed): {e}"
                    )
                    raise ValueError(error_msg) from e
        elif isinstance(workflow_result, WorkflowResult):
            validated_workflow_result = workflow_result
        else:
            type_error_msg = (
                f"workflow_result must be dict or WorkflowResult, got {type(workflow_result)}"
            )
            raise TypeError(type_error_msg)

        try:
            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(Analysis).where(Analysis.id == analysis_id).with_for_update()
                )
                analysis = result.scalar_one_or_none()

                if not analysis:
                    error_msg = f"Analysis {analysis_id} not found"
                    raise ValueError(error_msg)

                # Persist validated data (type-safe)
                analysis.raw_content = validated_workflow_result.raw_content
                analysis.extraction_metadata = (
                    validated_workflow_result.extraction_metadata.model_dump()
                )
                analysis.content_embedding = validated_workflow_result.content_embedding

                # Extract title from validated metadata
                if validated_workflow_result.extraction_metadata.title:
                    analysis.title = validated_workflow_result.extraction_metadata.title
                else:
                    # This should not happen if validation passed, but handle gracefully
                    from app.core.constants import DEFAULT_TITLE

                    analysis.title = DEFAULT_TITLE
                    logger.warning(
                        "persist_default_title_used",
                        analysis_id=str(analysis_id),
                        message="Title missing in validated metadata, using default",
                    )

                await db_session.commit()

                logger.info(
                    "persist_analysis_data_success",
                    analysis_id=str(analysis_id),
                    has_raw_content=validated_workflow_result.raw_content is not None,
                    has_title=analysis.title is not None,
                    has_embedding=validated_workflow_result.content_embedding is not None,
                    raw_content_length=len(validated_workflow_result.raw_content),
                )
                return True

        except ValueError:
            # Re-raise ValueError (validation errors, missing analysis)
            raise
        except Exception as db_error:
            logger.error(
                "persist_analysis_data_failed",
                analysis_id=str(analysis_id),
                error=str(db_error),
                exc_info=True,
            )
            error_message = f"Failed to persist analysis data: {db_error}"
            raise RuntimeError(error_message) from db_error
