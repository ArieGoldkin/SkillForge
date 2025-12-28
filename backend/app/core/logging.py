"""Configure structured logging with structlog.

Provides structured logging with machine-readable JSON output in production
and human-readable colored output in development. Includes trace ID binding
for correlation with Langfuse/OpenTelemetry traces.
"""

import logging
import sys

import structlog
import structlog.dev
import structlog.stdlib
import structlog.types

from app.core.config import settings


def add_trace_id(
    logger: structlog.types.WrappedLogger,  # noqa: ARG001 - Required by processor signature
    method_name: str,  # noqa: ARG001 - Required by processor signature
    event_dict: structlog.types.EventDict,
) -> structlog.types.EventDict:
    """Add Langfuse/OpenTelemetry trace ID to log entries.

    This enables correlation between logs and Langfuse traces for debugging.
    Fails gracefully if trace ID is unavailable.

    Args:
        logger: The wrapped logger instance
        method_name: The name of the method being logged
        event_dict: The event dictionary being logged

    Returns:
        Updated event dictionary with trace_id if available

    """
    try:
        from app.core.tracing import get_current_trace_id

        trace_id = get_current_trace_id()
        if trace_id:
            event_dict["trace_id"] = trace_id
    except Exception:  # noqa: BLE001, S110 - Graceful degradation for logging
        # Don't fail logging if trace ID unavailable (circular import, etc.)
        pass
    return event_dict


def setup_logging() -> None:
    """Configure structured logging with structlog.

    Sets up structured logging with different renderers for development
    (console with colored tracebacks) and production (JSON with structured
    exceptions) environments. Integrates with Python's standard logging
    library for compatibility with third-party libraries.

    Production features:
        - Machine-readable JSON output
        - Structured exception tracebacks (dict_tracebacks)
        - Trace ID correlation with Langfuse/OpenTelemetry
        - Stack trace rendering

    Development features:
        - Colored console output
        - Rich exception formatting with syntax highlighting
        - Human-readable timestamps

    Raises:
        TypeError: If LOG_LEVEL is invalid

    """
    try:
        # Validate log level
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), None)
        if not isinstance(log_level, int):
            error_msg = (
                f"Invalid LOG_LEVEL: {settings.LOG_LEVEL}. "
                f"Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )
            raise TypeError(error_msg)

        # Configure standard logging first
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=log_level,
            force=True,  # Override any existing configuration
        )

        # Configure structlog processors
        processors: list[object] = [
            structlog.contextvars.merge_contextvars,
            add_trace_id,  # Add Langfuse/OpenTelemetry trace ID
            structlog.processors.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
        ]

        # Different renderer for dev vs prod
        if settings.is_development():
            # Development: Human-readable console output with rich tracebacks
            processors.append(
                structlog.dev.ConsoleRenderer(
                    colors=True,
                    exception_formatter=structlog.dev.RichTracebackFormatter(),
                )
            )
        else:
            # Production: JSON output with structured exceptions
            processors.extend(
                [
                    structlog.processors.dict_tracebacks,  # Machine-readable exceptions
                    structlog.processors.JSONRenderer(),
                ]
            )

        # Configure structlog with stdlib integration
        structlog.configure(
            processors=processors,  # type: ignore[arg-type]
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
            context_class=dict,
        )

    except Exception as e:
        # Fallback to basic logging if structlog setup fails
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        logging.error(f"Failed to setup structlog: {e}", exc_info=True)  # noqa: LOG015 - Fallback before logger setup
        raise


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a configured structlog logger instance.

    Args:
        name: Logger name (typically __name__ of the calling module)

    Returns:
        Configured structlog BoundLogger instance

    """
    logger: structlog.BoundLogger = structlog.get_logger(name)
    return logger


logger = get_logger(__name__)
