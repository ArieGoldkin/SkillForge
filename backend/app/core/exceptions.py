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


class SkillForgeException(Exception):  # noqa: N818
    """Base exception for all SkillForge application errors.

    All custom exceptions should inherit from this class to enable
    centralized exception handling in middleware and error handlers.
    """

    pass


class ServiceException(SkillForgeException):
    """Base exception for service layer errors.

    Used for errors that occur in business logic services (extraction,
    embedding, etc.). Specific service errors should inherit from this.
    """

    pass


class EmbeddingError(ServiceException):
    """Exception raised when embedding generation fails.

    This exception is raised when:
    - HTTP errors occur during embedding API calls
    - Invalid responses are received from embedding service
    - Timeout occurs during embedding generation
    - Other embedding-related errors occur
    """

    pass


class JinaReaderError(ServiceException):
    """Exception raised when Jina Reader content extraction fails.

    This exception is raised when:
    - URL is not found (404)
    - HTTP errors occur during extraction
    - Timeout occurs during extraction
    - Other extraction-related errors occur
    """

    pass


class WorkflowError(SkillForgeException):
    """Exception raised when workflow execution fails.

    This exception is raised when:
    - Workflow tasks fail
    - Workflow state is invalid
    - Workflow orchestration errors occur
    """

    pass


class DatabaseError(SkillForgeException):
    """Exception raised when database operations fail.

    This exception is raised when:
    - Database connection fails
    - Query execution fails
    - Transaction errors occur
    - Other database-related errors occur
    """

    pass
