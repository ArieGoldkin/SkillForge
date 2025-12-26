"""Rate limiting middleware using SlowAPI.

This module configures SlowAPI rate limiting for the FastAPI application.
Rate limiting helps protect the API from abuse and ensures fair usage across clients.

Features:
    - Per-client rate limiting using client IP address
    - Redis-backed storage for distributed rate limiting (if configured)
    - In-memory fallback for development
    - Rate limit headers in responses (X-RateLimit-*)

Configuration:
    - Uses REDIS_URL from settings if available
    - Falls back to in-memory storage for single-instance deployments
    - Rate limit constants defined per endpoint category

Rate Limit Strategy:
    - Artifact GET: 100/minute (high read throughput)
    - Artifact Download: 10/minute (bandwidth-intensive)
    - Artifact List: 30/minute (moderate read throughput)

Example:
    ```python
    from app.middleware.rate_limit import limiter, ARTIFACT_GET_LIMIT


    @app.get("/api/v1/artifacts/{id}")
    @limiter.limit(ARTIFACT_GET_LIMIT)
    async def get_artifact(request: Request, id: str): ...
    ```

"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Use Redis if available, otherwise in-memory
# Redis enables distributed rate limiting across multiple backend instances
# In-memory storage is suitable for single-instance development environments
storage_uri = settings.REDIS_URL if hasattr(settings, "REDIS_URL") else "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    headers_enabled=True,  # Add X-RateLimit-* headers to responses
)

# Rate limit constants for different endpoint categories
# Format: "count/period" where period is second, minute, hour, or day
ARTIFACT_GET_LIMIT = "100/minute"  # High throughput for metadata reads
ARTIFACT_DOWNLOAD_LIMIT = "10/minute"  # Lower limit for bandwidth-intensive downloads
ARTIFACT_LIST_LIMIT = "30/minute"  # Moderate limit for list operations
