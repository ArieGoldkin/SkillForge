"""Redis connection factory with robust connection pooling.

Issue #299-304: Fixes "Connection closed by server" errors by adding
socket keepalive, timeouts, health checks, and retry policy.
"""

from redis import ConnectionPool, Redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def create_redis_client(
    redis_url: str | None = None,
    **kwargs,
) -> Redis:
    """Create a Redis client with robust connection pooling.

    Configures:
    - Socket keepalive (prevents idle disconnections > 5 minutes)
    - Connection/read timeouts (prevents hanging)
    - Connection pool health checks (validates stale connections)
    - Automatic retry with exponential backoff

    Args:
        redis_url: Redis connection URL (defaults to settings.REDIS_URL)
        **kwargs: Additional connection pool parameters

    Returns:
        Configured Redis client instance

    """
    settings = get_settings()
    url = redis_url or settings.REDIS_URL

    # Extract configuration from kwargs or use settings
    socket_connect_timeout = kwargs.pop(
        "socket_connect_timeout",
        settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    )
    socket_timeout = kwargs.pop(
        "socket_timeout",
        settings.REDIS_SOCKET_TIMEOUT,
    )
    socket_keepalive = kwargs.pop(
        "socket_keepalive",
        settings.REDIS_SOCKET_KEEPALIVE,
    )
    max_connections = kwargs.pop(
        "max_connections",
        settings.REDIS_MAX_CONNECTIONS,
    )
    health_check_interval = kwargs.pop(
        "health_check_interval",
        settings.REDIS_HEALTH_CHECK_INTERVAL,
    )

    logger.info(
        "redis_connection_factory_creating",
        socket_keepalive=socket_keepalive,
        socket_timeout=socket_timeout,
        max_connections=max_connections,
        health_check_interval=health_check_interval,
    )

    # Create connection pool with proper configuration
    connection_pool = ConnectionPool.from_url(
        url,
        max_connections=max_connections,
        socket_connect_timeout=socket_connect_timeout,
        socket_timeout=socket_timeout,
        socket_keepalive=socket_keepalive,
        health_check_interval=health_check_interval,
        retry=Retry(
            backoff=ExponentialBackoff(),
            retries=3,
        ),
        **kwargs,
    )

    return Redis(connection_pool=connection_pool)


def get_redis_url_for_langchain() -> str:
    """Get Redis URL with connection parameters for LangChain components.

    LangChain's cache classes accept redis_url but need parameters passed differently.
    This returns the base URL - the create_redis_client should be used for direct Redis.
    """
    settings = get_settings()
    return settings.REDIS_URL
