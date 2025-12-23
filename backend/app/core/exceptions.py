"""Custom exception hierarchy for SkillForge application.

This module provides a structured exception hierarchy for consistent error
handling across the application. All custom exceptions inherit from
SkillForgeException, allowing for centralized exception handling.

Exception Hierarchy:
    SkillForgeException (base)
    ├── ServiceException (service layer errors)
    │   ├── EmbeddingError (embedding generation failures)
    │   └── JinaReaderError (content extraction failures)
    ├── WorkflowError (workflow execution failures)
    └── DatabaseError (database operation failures)
"""

from enum import Enum


class ExtractionErrorCode(str, Enum):
    """Error codes for content extraction failures."""

    HTTP_404 = "HTTP_404"
    HTTP_5XX = "HTTP_5XX"
    TIMEOUT = "TIMEOUT"
    ERROR_PAGE = "ERROR_PAGE"
    REDIRECT_LOOP = "REDIRECT_LOOP"
    NETWORK_ERROR = "NETWORK_ERROR"
    UNKNOWN = "UNKNOWN"


class SkillForgeException(Exception):  # noqa: N818
    """Base exception for all SkillForge application errors.

    All custom exceptions should inherit from this class to enable
    centralized exception handling in middleware and error handlers.
    """


class ServiceException(SkillForgeException):
    """Base exception for service layer errors.

    Used for errors that occur in business logic services (extraction,
    embedding, etc.). Specific service errors should inherit from this.
    """


class EmbeddingError(ServiceException):
    """Exception raised when embedding generation fails.

    This exception is raised when:
    - HTTP errors occur during embedding API calls
    - Invalid responses are received from embedding service
    - Timeout occurs during embedding generation
    - Other embedding-related errors occur
    """


class JinaReaderError(ServiceException):
    """Exception raised when Jina Reader content extraction fails.

    This exception is raised when:
    - URL is not found (404)
    - HTTP errors occur during extraction
    - Timeout occurs during extraction
    - Other extraction-related errors occur

    Attributes:
        error_code: Categorized error code for programmatic handling

    """

    def __init__(self, message: str, error_code: ExtractionErrorCode | None = None):
        """Initialize JinaReaderError with message and optional error code.

        Args:
            message: Human-readable error message
            error_code: Categorized error code, defaults to UNKNOWN

        """
        super().__init__(message)
        self.error_code = error_code or ExtractionErrorCode.UNKNOWN


class WorkflowError(SkillForgeException):
    """Exception raised when workflow execution fails.

    This exception is raised when:
    - Workflow tasks fail
    - Workflow state is invalid
    - Workflow orchestration errors occur
    """


class WorkflowStageError(SkillForgeException):
    """Exception that preserves workflow stage context for error handling.

    This exception wraps other exceptions to preserve the stage/node context
    where the error occurred, allowing the orchestrator to emit stage-specific
    error events instead of generic "workflow" stage errors.

    Attributes:
        stage: The workflow stage where the error occurred (e.g., "embedding", "supervisor_routing")
        original_exception: The original exception that was wrapped

    Example:
        ```python
        try:
            result = await generate_embedding(content, analysis_id)
        except Exception as e:
            raise WorkflowStageError(
                stage="embedding",
                original_exception=e,
                message=f"Embedding generation failed: {e}"
            )
        ```

    """

    def __init__(
        self,
        stage: str,
        original_exception: BaseException | Exception,
        message: str | None = None,
    ):
        """Initialize WorkflowStageError with stage context.

        Args:
            stage: The workflow stage where the error occurred
            original_exception: The original exception that was wrapped
            message: Optional custom error message (defaults to original exception message)

        """
        error_message = message or str(original_exception)
        super().__init__(error_message)
        self.stage = stage
        self.original_exception = original_exception
        # Preserve exception chain for debugging (__cause__)
        self.__cause__ = original_exception


class DatabaseError(SkillForgeException):
    """Exception raised when database operations fail.

    This exception is raised when:
    - Database connection fails
    - Query execution fails
    - Transaction errors occur
    - Other database-related errors occur
    """


def is_cleanup_generator_exit(
    exc: BaseException,
    workflow_completed: bool = False,
) -> bool:
    """Detect if GeneratorExit is from cleanup (normal) or execution (error).

    Python's async runtime converts GeneratorExit to RuntimeError in async functions.
    This function detects both the original GeneratorExit and the converted RuntimeError.

    GeneratorExit during cleanup after successful workflow completion is normal
    generator lifecycle behavior when LangGraph's pregel module closes async generators.
    GeneratorExit during execution indicates workflow interruption/cancellation.

    Args:
        exc: BaseException to check (GeneratorExit, RuntimeError, or other)
        workflow_completed: Whether workflow completed successfully before the exception

    Returns:
        True if cleanup GeneratorExit (normal, should be suppressed)
        False if execution GeneratorExit (error, should be handled) or not a GeneratorExit

    Examples:
        >>> is_cleanup_generator_exit(GeneratorExit(), workflow_completed=True)
        True
        >>> is_cleanup_generator_exit(GeneratorExit(), workflow_completed=False)
        False
        >>> is_cleanup_generator_exit(
        ...     RuntimeError("coroutine ignored GeneratorExit"), workflow_completed=True
        ... )
        True
        >>> is_cleanup_generator_exit(ValueError("other error"), workflow_completed=True)
        False

    """
    # Check if this is a GeneratorExit or converted RuntimeError
    is_generator_exit = isinstance(exc, GeneratorExit)
    is_converted_generator_exit = isinstance(
        exc, RuntimeError
    ) and "coroutine ignored GeneratorExit" in str(exc)

    if not (is_generator_exit or is_converted_generator_exit):
        # Not a GeneratorExit
        return False

    # If workflow completed, GeneratorExit is cleanup (normal)
    # If workflow didn't complete, GeneratorExit is execution (error)
    return workflow_completed


def is_generator_exit_type(exc: BaseException) -> bool:
    """Check if exception is a GeneratorExit or converted RuntimeError.

    This is a helper to check the type without needing workflow_completed context.
    Use is_cleanup_generator_exit() when you have workflow_completed information.

    Args:
        exc: BaseException to check

    Returns:
        True if GeneratorExit or converted RuntimeError, False otherwise

    """
    is_generator_exit = isinstance(exc, GeneratorExit)
    is_converted_generator_exit = isinstance(
        exc, RuntimeError
    ) and "coroutine ignored GeneratorExit" in str(exc)
    return is_generator_exit or is_converted_generator_exit
