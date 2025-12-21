"""Unit tests for Redis connection factory.

Tests verify that the connection factory creates Redis clients with proper
configuration for socket keepalive, timeouts, health checks, and retry policy.
"""

from unittest.mock import Mock, patch

from redis import ConnectionPool, Redis
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

from app.shared.services.cache.redis_connection import (
    create_redis_client,
    get_redis_url_for_langchain,
)


class TestCreateRedisClient:
    """Test suite for create_redis_client function."""

    @patch("app.shared.services.cache.redis_connection.ConnectionPool")
    @patch("app.shared.services.cache.redis_connection.Redis")
    def test_creates_client_with_default_settings(
        self,
        mock_redis: Mock,
        mock_pool_class: Mock,
    ) -> None:
        """Test that client is created with default settings from config."""
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool_class.from_url.return_value = mock_pool
        mock_client = Mock(spec=Redis)
        mock_redis.return_value = mock_client

        result = create_redis_client()

        # Verify ConnectionPool.from_url was called with correct parameters
        mock_pool_class.from_url.assert_called_once()
        call_kwargs = mock_pool_class.from_url.call_args[1]

        assert call_kwargs["socket_connect_timeout"] == 5
        assert call_kwargs["socket_timeout"] == 5
        assert call_kwargs["socket_keepalive"] is True
        assert call_kwargs["max_connections"] == 20
        assert call_kwargs["health_check_interval"] == 30

        # Verify retry configuration
        assert isinstance(call_kwargs["retry"], Retry)
        # Note: Retry uses _retries (private attribute)
        assert call_kwargs["retry"]._retries == 3
        assert isinstance(call_kwargs["retry"]._backoff, ExponentialBackoff)

        # Verify Redis client was created with the pool
        mock_redis.assert_called_once_with(connection_pool=mock_pool)
        assert result == mock_client

    @patch("app.shared.services.cache.redis_connection.ConnectionPool")
    @patch("app.shared.services.cache.redis_connection.Redis")
    def test_accepts_custom_redis_url(
        self,
        mock_redis: Mock,
        mock_pool_class: Mock,
    ) -> None:
        """Test that custom Redis URL is passed to ConnectionPool."""
        custom_url = "redis://custom-host:6379"
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool_class.from_url.return_value = mock_pool

        create_redis_client(redis_url=custom_url)

        # Verify custom URL was used
        call_args = mock_pool_class.from_url.call_args
        assert call_args[0][0] == custom_url

    @patch("app.shared.services.cache.redis_connection.ConnectionPool")
    @patch("app.shared.services.cache.redis_connection.Redis")
    def test_accepts_custom_connection_parameters(
        self,
        mock_redis: Mock,
        mock_pool_class: Mock,
    ) -> None:
        """Test that custom connection parameters override defaults."""
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool_class.from_url.return_value = mock_pool

        create_redis_client(
            socket_connect_timeout=10,
            socket_timeout=15,
            socket_keepalive=False,
            max_connections=50,
            health_check_interval=60,
        )

        call_kwargs = mock_pool_class.from_url.call_args[1]
        assert call_kwargs["socket_connect_timeout"] == 10
        assert call_kwargs["socket_timeout"] == 15
        assert call_kwargs["socket_keepalive"] is False
        assert call_kwargs["max_connections"] == 50
        assert call_kwargs["health_check_interval"] == 60

    @patch("app.shared.services.cache.redis_connection.ConnectionPool")
    @patch("app.shared.services.cache.redis_connection.Redis")
    def test_passes_additional_kwargs_to_connection_pool(
        self,
        mock_redis: Mock,
        mock_pool_class: Mock,
    ) -> None:
        """Test that additional kwargs are passed to ConnectionPool."""
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool_class.from_url.return_value = mock_pool

        create_redis_client(
            decode_responses=True,
            encoding="utf-8",
        )

        call_kwargs = mock_pool_class.from_url.call_args[1]
        assert call_kwargs["decode_responses"] is True
        assert call_kwargs["encoding"] == "utf-8"

    @patch("app.shared.services.cache.redis_connection.logger")
    @patch("app.shared.services.cache.redis_connection.ConnectionPool")
    @patch("app.shared.services.cache.redis_connection.Redis")
    def test_logs_connection_creation(
        self,
        mock_redis: Mock,
        mock_pool_class: Mock,
        mock_logger: Mock,
    ) -> None:
        """Test that connection creation is logged with configuration details."""
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool_class.from_url.return_value = mock_pool

        create_redis_client()

        # Verify logger was called with connection details
        # Note: logger may be called multiple times, check for the creation log
        log_calls = [call for call in mock_logger.info.call_args_list if call[0][0] == "redis_connection_factory_creating"]
        assert len(log_calls) > 0, "Expected redis_connection_factory_creating log"
        log_call = log_calls[0]
        assert log_call[1]["socket_keepalive"] is True
        assert log_call[1]["socket_timeout"] == 5
        assert log_call[1]["max_connections"] == 20
        assert log_call[1]["health_check_interval"] == 30


class TestGetRedisUrlForLangchain:
    """Test suite for get_redis_url_for_langchain function."""

    def test_returns_redis_url_from_settings(self) -> None:
        """Test that function returns Redis URL from settings."""
        url = get_redis_url_for_langchain()

        # Should return a valid Redis URL
        assert url.startswith("redis://")
        assert isinstance(url, str)
        assert len(url) > 0
