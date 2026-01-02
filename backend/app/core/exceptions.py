"""Custom exception hierarchy for SkillForge application.

This module provides a structured exception hierarchy for consistent error
handling across the application. All custom exceptions inherit from
SkillForgeException, allowing for centralized exception handling.

Exception Hierarchy:
    SkillForgeException (base)
    ├── ServiceException (service layer errors)
    │   ├── EmbeddingError (embedding generation failures)
    │   ├── JinaReaderError (content extraction failures)
    │   ├── TavilySearchError (search API failures)
    │   ├── GitHubSearchError (GitHub API failures)
    │   ├── ExternalServiceError (external API failures)
    │   └── CacheError (Redis/cache failures)
    ├── WorkflowError (workflow execution failures)
    │   ├── WorkflowStageError (stage-aware error wrapper)
    │   └── AgentError (individual agent failures)
    ├── DatabaseError (database operation failures)
    ├── ConfigurationError (configuration/setup errors)
    ├── EvaluationError (G-Eval/scoring failures)
    └── RetryableError (marker for retryable errors)
        └── TransientError (transient failures)

    AgentGroupError (PEP 654 ExceptionGroup for parallel agent failures)
"""

from __future__ import annotations

from enum import Enum


class ExtractionErrorCode(str, Enum):
    """Error codes for content extraction failures."""

    HTTP_404 = "HTTP_404"
    HTTP_5XX = "HTTP_5XX"
    TIMEOUT = "TIMEOUT"
    ERROR_PAGE = "ERROR_PAGE"
    REDIRECT_LOOP = "REDIRECT_LOOP"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_URL = "INVALID_URL"
    TRANSCRIPT_DISABLED = "TRANSCRIPT_DISABLED"
    NO_TRANSCRIPT = "NO_TRANSCRIPT"
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


class TavilySearchError(ServiceException):
    """Exception raised when Tavily Search API call fails.

    This exception is raised when:
    - HTTP errors occur during search request
    - Timeout occurs during search
    - API rate limits are exceeded
    - Invalid API key or authentication failures
    - Other search-related errors occur

    Attributes:
        error_code: Categorized error code for programmatic handling

    """

    def __init__(self, message: str, error_code: ExtractionErrorCode | None = None):
        """Initialize TavilySearchError with message and optional error code.

        Args:
            message: Human-readable error message
            error_code: Categorized error code, defaults to UNKNOWN

        """
        super().__init__(message)
        self.error_code = error_code or ExtractionErrorCode.UNKNOWN


class GitHubSearchError(ServiceException):
    """Exception raised when GitHub Search API call fails.

    This exception is raised when:
    - HTTP errors occur during search request
    - Timeout occurs during search
    - API rate limits are exceeded
    - Invalid API token or authentication failures
    - Repository not found errors
    - Other search-related errors occur

    Attributes:
        error_code: Categorized error code for programmatic handling

    """

    def __init__(self, message: str, error_code: ExtractionErrorCode | None = None):
        """Initialize GitHubSearchError with message and optional error code.

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
                stage="embedding", original_exception=e, message=f"Embedding generation failed: {e}"
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


class AgentError(WorkflowError):
    """Exception raised when an individual agent fails during workflow execution.

    This exception is raised when:
    - Agent execution fails due to LLM errors
    - Agent raises unhandled exceptions
    - Agent timeout occurs
    - Agent produces invalid output

    Attributes:
        agent_name: Name of the agent that failed (e.g., "key_insights", "security_auditor")
        analysis_id: The analysis ID being processed when failure occurred
        original_exception: The underlying exception that caused the failure

    Example:
        ```python
        try:
            result = await key_insights_agent.ainvoke(state)
        except Exception as e:
            raise AgentError(
                agent_name="key_insights",
                original_exception=e,
                analysis_id=state["analysis_id"],
                message=f"Key insights agent failed: {e}",
            )
        ```

    """

    def __init__(
        self,
        agent_name: str,
        original_exception: BaseException,
        analysis_id: str | None = None,
        message: str | None = None,
    ):
        """Initialize AgentError with agent context.

        Args:
            agent_name: Name of the agent that failed
            original_exception: The underlying exception that caused the failure
            analysis_id: The analysis ID being processed (optional)
            message: Optional custom error message (defaults to original exception message)

        """
        error_message = message or f"Agent '{agent_name}' failed: {original_exception}"
        super().__init__(error_message)
        self.agent_name = agent_name
        self.analysis_id = analysis_id
        self.original_exception = original_exception
        # Preserve exception chain for debugging (__cause__)
        self.__cause__ = original_exception


class AgentGroupError(ExceptionGroup):
    """Exception group for multiple agent failures during parallel execution.

    Uses PEP 654 ExceptionGroup to collect errors from 16 parallel agents.
    Can be handled with except* syntax in Python 3.11+.

    This exception is raised when:
    - Multiple agents fail during parallel execution
    - Need to preserve individual agent error context
    - Want to handle different agent errors separately

    Attributes:
        message: Description of the group error
        exceptions: List of AgentError instances from failed agents

    Example:
        ```python
        # Collecting agent errors
        agent_errors: list[AgentError] = []
        for agent_name, task in parallel_tasks.items():
            try:
                await task
            except Exception as e:
                agent_errors.append(AgentError(agent_name, e))

        if agent_errors:
            raise AgentGroupError("Multiple agents failed", agent_errors)

        # Handling with except* (Python 3.11+)
        try:
            await run_parallel_agents()
        except* AgentError as eg:
            for exc in eg.exceptions:
                logger.error(f"Agent {exc.agent_name} failed: {exc}")
        ```

    """

    def __init__(self, message: str, exceptions: list[AgentError]):
        """Initialize AgentGroupError with agent errors.

        Args:
            message: Description of the group error
            exceptions: List of AgentError instances from failed agents

        """
        super().__init__(message, exceptions)


class ConfigurationError(SkillForgeException):
    """Exception raised when configuration or setup errors occur.

    This exception is raised when:
    - Required environment variables are missing
    - Configuration files are invalid
    - Service initialization fails due to config
    - API keys or credentials are invalid

    Example:
        ```python
        if not settings.OPENAI_API_KEY:
            raise ConfigurationError("OPENAI_API_KEY environment variable not set")
        ```

    """


class ExternalServiceError(ServiceException):
    """Exception raised when external API or service calls fail.

    This exception is raised when:
    - External API returns error response
    - Network timeout to external service
    - Authentication failure with external service
    - External service unavailable

    Attributes:
        service_name: Name of the external service that failed

    Example:
        ```python
        try:
            response = await external_api.get(url)
        except httpx.HTTPError as e:
            raise ExternalServiceError(
                service_name="external_api", message=f"Failed to fetch data: {e}"
            )
        ```

    """

    def __init__(self, service_name: str, message: str):
        """Initialize ExternalServiceError with service context.

        Args:
            service_name: Name of the external service that failed
            message: Error message describing the failure

        """
        super().__init__(message)
        self.service_name = service_name


class CacheError(ServiceException):
    """Exception raised when Redis or cache operations fail.

    This exception is raised when:
    - Redis connection fails
    - Cache get/set operations fail
    - Cache serialization/deserialization errors
    - Cache eviction failures

    Example:
        ```python
        try:
            await redis_client.set(key, value)
        except redis.RedisError as e:
            raise CacheError(f"Failed to cache result: {e}")
        ```

    """


class EvaluationError(SkillForgeException):
    """Exception raised when G-Eval or quality scoring fails.

    This exception is raised when:
    - G-Eval LLM calls fail
    - Score parsing errors occur
    - Evaluation criteria validation fails
    - Quality gate evaluation errors

    Example:
        ```python
        try:
            score = await g_eval_scorer.score(criteria, output)
        except Exception as e:
            raise EvaluationError(f"G-Eval scoring failed: {e}")
        ```

    """


class RetryableError(SkillForgeException):
    """Base marker class for errors that may succeed on retry.

    Inherit from this class to indicate that an operation may succeed
    if retried with exponential backoff or circuit breaker patterns.

    This is a marker base class - specific retryable errors should
    inherit from both RetryableError and the appropriate error type.

    Example:
        ```python
        class TransientDatabaseError(RetryableError, DatabaseError):
            \"\"\"Database error that may succeed on retry.\"\"\"
            pass

        # Retry logic
        if isinstance(exc, RetryableError):
            await retry_with_backoff(operation)
        ```

    """


class TransientError(RetryableError):
    """Exception raised for transient failures that may succeed on retry.

    This exception is raised when:
    - Network timeouts occur
    - Rate limits are temporarily exceeded
    - Service temporarily unavailable
    - Transient database connection issues

    Example:
        ```python
        try:
            response = await api_call()
        except httpx.TimeoutException as e:
            raise TransientError(f"API timeout, retry recommended: {e}")
        ```

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
