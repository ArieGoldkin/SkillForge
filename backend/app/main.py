"""FastAPI application initialization and middleware."""

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from dotenv import dotenv_values, load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, ORJSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

# CRITICAL: Load .env and override system env vars BEFORE any LangChain imports
# This ensures SkillForge uses the correct Langfuse project configuration
load_dotenv(override=True)

# Force override system environment variables from .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    env_values = dotenv_values(env_file)
    # Get project from .env file (this takes absolute precedence)
    project_from_env = env_values.get("LANGCHAIN_PROJECT")
    if project_from_env:
        # Force override - this happens BEFORE any LangChain imports
        os.environ["LANGCHAIN_PROJECT"] = project_from_env

from app.api.v1 import annotations, health  # noqa: E402
from app.api.v1.analysis import router as analysis_router  # noqa: E402
from app.api.v1.tutor import router as tutor_router  # noqa: E402
from app.core.api_key_validation import log_api_key_configuration  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.exceptions import ConfigurationError, SkillForgeException  # noqa: E402
from app.core.langfuse_service import (  # noqa: E402
    configure_langfuse_service,
    get_langfuse_service,
    shutdown_langfuse_service,
)
from app.core.logging import get_logger, setup_logging  # noqa: E402
from app.middleware.rate_limit import limiter  # noqa: E402

# Setup logging first
setup_logging()
logger = get_logger(__name__)


def _background_task_exception_handler(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Global exception handler for unhandled exceptions in background tasks.

    This catches exceptions (including GeneratorExit) that occur in background tasks
    and escape all other exception handlers. This is a safety net for cleanup exceptions.
    """
    from app.core.exceptions import is_cleanup_generator_exit

    exception = context.get("exception")
    task = context.get("task")
    message = context.get("message", "")

    if exception is not None:
        # Use unified GeneratorExit detection
        # Note: We can't determine workflow_completed from here, so we assume cleanup
        # (GeneratorExit in global handler is typically cleanup after successful completion)
        if is_cleanup_generator_exit(exception, workflow_completed=True):
            # GeneratorExit during cleanup is normal generator lifecycle behavior
            # Log at DEBUG level to avoid false error indicators
            logger.debug(
                "unhandled_background_task_generator_exit",
                error_type="GeneratorExit",
                error_message=str(exception),
                task_name=task.get_name() if task else "unknown",
                message=message,
                context="global_background_task_handler",
                note=(
                    "GeneratorExit caught by global background task exception handler. "
                    "This typically occurs when LangGraph's pregel module closes async generators "
                    "during cleanup and the exception escapes all other handlers. "
                    "This is normal generator lifecycle behavior and does not indicate an error. "
                    "If the workflow completed successfully, this is expected cleanup behavior."
                ),
            )
        else:
            # Other exceptions are real errors - log at ERROR level
            logger.error(
                "unhandled_background_task_exception",
                error_type=type(exception).__name__,
                error_message=str(exception),
                task_name=task.get_name() if task else "unknown",
                message=message,
                context="global_background_task_handler",
            )
    else:
        # Log context even if no exception (might be a warning or other event)
        logger.warning(
            "background_task_event",
            message=message,
            task_name=task.get_name() if task else "unknown",
            context=context,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: PLR0912, PLR0915 - Lifespan needs many branches/statements for initialization
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    # Initialize app.state for background task tracking
    app.state.background_tasks = set()

    # Set up global exception handler for background tasks
    # This catches exceptions (including GeneratorExit) that escape other handlers
    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(_background_task_exception_handler)
        logger.debug("background_task_exception_handler_installed")
    except RuntimeError:
        # No running loop yet, will be set up later
        logger.debug("background_task_exception_handler_deferred")

    # Configure Langfuse for observability
    # Langfuse handles async generators natively - no workarounds needed!
    configure_langfuse_service()

    # Check Langfuse configuration (Issue #432 - Fail-fast validation)
    langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
    langfuse_host = os.getenv("LANGFUSE_HOST", "http://localhost:3000")

    if langfuse_enabled:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")

        if not public_key or not secret_key:
            error_msg = (
                "Langfuse is enabled but credentials are missing. "
                "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY or disable with "
                "LANGFUSE_ENABLED=false"
            )
            logger.error(
                "langfuse_credentials_missing",
                message=error_msg,
                public_key_set=bool(public_key),
                secret_key_set=bool(secret_key),
            )
            raise ConfigurationError(error_msg)
        else:
            logger.info(
                "langfuse_configured",
                langfuse_enabled=True,
                langfuse_host=langfuse_host,
                public_key_set=True,
                secret_key_set=True,
            )
    else:
        logger.info(
            "langfuse_disabled",
            message="Langfuse observability is disabled. Set LANGFUSE_ENABLED=true to enable.",
        )

    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        langfuse_enabled=langfuse_enabled,
        langfuse_host=langfuse_host if langfuse_enabled else None,
    )

    # Log API key configuration status (Issue #295)
    # This helps developers quickly identify which providers are configured
    # and whether the selected LLM_MODEL has its required API key
    log_api_key_configuration()

    # Issue #624: Initialize AsyncPostgresSaver for LangGraph checkpointing
    # Uses 2025 best practice AsyncConnectionPool pattern with lifespan integration
    app.state.checkpointer = None
    if settings.DATABASE_URL and not os.environ.get("PYTEST_CURRENT_TEST"):
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from psycopg_pool import AsyncConnectionPool

            from app.core.constants import DB_MAX_OVERFLOW, DB_POOL_SIZE

            # Convert DATABASE_URL from postgresql+asyncpg:// to postgresql:// for psycopg
            db_uri = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

            # Create connection pool with 2025 best practices
            # - autocommit=True: Required for AsyncPostgresSaver
            # - prepare_threshold=0: Disables prepared statements (recommended for checkpointing)
            # - open=False: Prevents auto-open in constructor (we open explicitly with await pool.open())
            pool = AsyncConnectionPool(
                conninfo=db_uri,
                max_size=DB_POOL_SIZE,
                kwargs={"autocommit": True, "prepare_threshold": 0},
                open=False,  # Open explicitly with await pool.open() to avoid deprecation warning
            )

            # AsyncPostgresSaver requires pool to be opened before setup
            # Use explicit await pool.open() instead of auto-open in constructor
            await pool.open()

            saver = AsyncPostgresSaver(pool)
            await saver.setup()
            app.state.checkpointer = saver

            logger.info(
                "langgraph_checkpointer_initialized",
                type="AsyncPostgresSaver",
                pool_size=DB_POOL_SIZE,
                max_overflow=DB_MAX_OVERFLOW,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "langgraph_checkpointer_fallback",
                error=str(e),
                fallback="MemorySaver",
                message="Failed to initialize AsyncPostgresSaver, workflows will use MemorySaver",
            )
            app.state.checkpointer = None

    yield
    # Shutdown
    logger.info("application_shutdown")

    # Close AsyncPostgresSaver connection pool
    if app.state.checkpointer is not None:
        try:
            # AsyncPostgresSaver has a connection pool that needs to be closed
            if hasattr(app.state.checkpointer, "conn"):
                await app.state.checkpointer.conn.close()
                logger.info("langgraph_checkpointer_pool_closed")
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "langgraph_checkpointer_close_error",
                error=str(e),
                message="Error closing AsyncPostgresSaver pool",
            )

    # Flush and shutdown Langfuse with timeout protection
    try:
        # Give Langfuse 10 seconds to flush remaining events
        service = get_langfuse_service()
        if service:
            await asyncio.wait_for(
                asyncio.to_thread(service.flush),
                timeout=10.0,
            )
    except TimeoutError:
        logger.warning(
            "langfuse_flush_timeout",
            message="Langfuse flush timed out after 10 seconds",
        )

    try:
        # Give Langfuse 10 seconds to complete shutdown
        await asyncio.wait_for(
            shutdown_langfuse_service(),
            timeout=10.0,
        )
    except TimeoutError:
        logger.warning(
            "langfuse_shutdown_timeout",
            message="Langfuse shutdown timed out after 10 seconds",
        )

    # Remove global exception handler on shutdown
    try:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(None)
        logger.debug("background_task_exception_handler_removed")
    except RuntimeError:
        pass


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request for tracing.

    Generates or extracts request ID from X-Request-ID header for distributed
    tracing support. Binds request ID to logging context and adds it to response
    headers. Properly cleans up context variables to prevent context leakage.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request with request ID tracking.

        Args:
            request: FastAPI request object
            call_next: Next middleware/route handler

        Returns:
            Response with X-Request-ID header

        """
        # Check for existing request ID (for distributed tracing)
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state
        request.state.request_id = request_id

        # Bind to context vars for logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log request completion
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
        except Exception as e:
            # Log error with request ID
            process_time = time.time() - start_time
            logger.error(
                "request_error",
                method=request.method,
                path=request.url.path,
                error=str(e),
                process_time_ms=round(process_time * 1000, 2),
                exc_info=True,
            )
            raise
        else:
            return response
        finally:
            # Always cleanup context vars to prevent context leakage
            structlog.contextvars.unbind_contextvars("request_id")


# Create FastAPI application
app = FastAPI(
    title="SkillForge API",
    version="0.1.0",
    description="Research-to-Implementation Pipeline Backend",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,  # 2-3x faster JSON serialization
)

# Rate Limiting Middleware
# Attach limiter to app state and register exception handler
app.state.limiter = limiter
# slowapi's handler type is compatible but ty doesn't recognize the exception subtype
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Compression Middleware
# Compresses responses > 1000 bytes with gzip (reduces bandwidth usage)
# Starlette middleware classes are runtime-compatible but ty's strict typing requires ignore
app.add_middleware(GZipMiddleware, minimum_size=1000)  # type: ignore[arg-type]

# CORS Middleware
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID Middleware
app.add_middleware(RequestIDMiddleware)  # type: ignore[arg-type]


# Global Exception Handler
@app.exception_handler(SkillForgeException)
async def skillforge_exception_handler(request: Request, exc: SkillForgeException):
    """Handle SkillForge application exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "application_exception",
        request_id=request_id,
        path=request.url.path,
        error=str(exc),
        exception_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": type(exc).__name__,
                "message": str(exc),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "unhandled_exception",
        request_id=request_id,
        path=request.url.path,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
    )


# Register routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(analysis_router, prefix=settings.API_V1_PREFIX)
app.include_router(tutor_router, prefix=settings.API_V1_PREFIX)
app.include_router(annotations.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SkillForge API",
        "version": "0.1.0",
        "docs": "/docs",
    }
