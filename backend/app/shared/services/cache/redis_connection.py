"""Redis connection factory with robust connection pooling.

Issue #388: Production-ready Redis connection with TCP keepalive socket options.

Fixes "Connection closed by server" errors by adding:
- TCP keepalive socket options (prevents idle connection drops)
- Socket keepalive boolean flag (enables keepalive)
- Connection/read timeouts (prevents hanging)
- Connection pool health checks (validates stale connections)
- Automatic retry with exponential backoff
"""

import socket
import sys

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
    """Create a Redis client with production-ready connection pooling.

    Configures:
    - TCP keepalive socket options (OS-level, prevents idle disconnections)
    - Socket keepalive boolean (enables keepalive)
    - Connection/read timeouts (prevents hanging)
    - Connection pool health checks (validates stale connections)
    - Automatic retry with exponential backoff (3 attempts)

    TCP Keepalive Configuration:
    - TCP_KEEPIDLE: 60 seconds before sending keepalive probe
    - TCP_KEEPINTVL: 10 seconds between keepalive probes
    - TCP_KEEPCNT: 3 failed probes before connection marked dead
    - Total timeout: 60 + (10 * 3) = 90 seconds

    Args:
        redis_url: Redis connection URL (defaults to settings.REDIS_URL)
        **kwargs: Additional connection pool parameters

    Returns:
        Configured Redis client instance

    Example:
        >>> client = create_redis_client()
        >>> await client.ping()  # Validates connection

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

    # TCP keepalive socket options (OS-level configuration)
    # Platform-specific constants for socket.setsockopt()
    socket_keepalive_options = _get_socket_keepalive_options()

    logger.info(
        "redis_connection_factory_creating",
        socket_keepalive=socket_keepalive,
        socket_keepalive_options=socket_keepalive_options,
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
        socket_keepalive_options=socket_keepalive_options,
        health_check_interval=health_check_interval,
        retry=Retry(
            backoff=ExponentialBackoff(),
            retries=3,
        ),
        **kwargs,
    )

    return Redis(connection_pool=connection_pool)


def _get_socket_keepalive_options() -> dict[int, int]:
    """Get platform-specific TCP keepalive socket options.

    Returns:
        Dictionary of socket options for TCP keepalive:
        - TCP_KEEPIDLE: Seconds before sending keepalive probe (60s)
        - TCP_KEEPINTVL: Seconds between keepalive probes (10s)
        - TCP_KEEPCNT: Number of failed probes before connection dead (3)

    Note:
        Options are platform-specific:
        - Linux: TCP_KEEPIDLE, TCP_KEEPINTVL, TCP_KEEPCNT
        - macOS: TCP_KEEPALIVE, TCP_KEEPINTVL, TCP_KEEPCNT
        - Windows: Uses different constant values

    """
    options = {}

    # TCP_KEEPIDLE or TCP_KEEPALIVE (macOS uses different constant name)
    if sys.platform == "darwin":  # macOS
        # macOS uses TCP_KEEPALIVE instead of TCP_KEEPIDLE
        options[socket.TCP_KEEPALIVE] = 60
    elif hasattr(socket, "TCP_KEEPIDLE"):  # Linux
        options[socket.TCP_KEEPIDLE] = 60
    # Windows doesn't support TCP_KEEPIDLE - keepalive is configured differently

    # TCP_KEEPINTVL: Interval between keepalive probes (10 seconds)
    if hasattr(socket, "TCP_KEEPINTVL"):
        options[socket.TCP_KEEPINTVL] = 10

    # TCP_KEEPCNT: Number of failed probes before connection is marked dead (3)
    if hasattr(socket, "TCP_KEEPCNT"):
        options[socket.TCP_KEEPCNT] = 3

    return options


def get_redis_url_for_langchain() -> str:
    """Get Redis URL with connection parameters for LangChain components.

    LangChain's cache classes accept redis_url but need parameters passed differently.
    This returns the base URL - the create_redis_client should be used for direct Redis.
    """
    settings = get_settings()
    return settings.REDIS_URL
