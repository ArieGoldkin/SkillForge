"""FastAPI application initialization and middleware."""

import os
import time
import uuid
from contextlib import asynccontextmanager

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Load .env file BEFORE any other imports to ensure LangSmith env vars are available
# This is critical for LangChain to detect LANGCHAIN_TRACING_V2 at import time
load_dotenv()

from app.api.v1 import analyze, artifacts, health, search  # noqa: E402
from app.api.v1.tutor import router as tutor_router  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.exceptions import SkillForgeException  # noqa: E402
from app.core.logging import get_logger, setup_logging  # noqa: E402

# Setup logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    langsmith_enabled = os.getenv("LANGCHAIN_TRACING_V2") == "true"
    langsmith_project = os.getenv("LANGCHAIN_PROJECT", "default")

    logger.info(
        "application_startup",
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
        langsmith_enabled=langsmith_enabled,
        langsmith_project=langsmith_project if langsmith_enabled else None,
    )
    yield
    # Shutdown
    logger.info("application_shutdown")


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
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID Middleware
app.add_middleware(RequestIDMiddleware)


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
        exc_info=True,
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
        exc_info=True,
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
app.include_router(analyze.router, prefix=settings.API_V1_PREFIX)
app.include_router(artifacts.router, prefix=settings.API_V1_PREFIX)
app.include_router(search.router, prefix=settings.API_V1_PREFIX)
app.include_router(tutor_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SkillForge API",
        "version": "0.1.0",
        "docs": "/docs",
    }
