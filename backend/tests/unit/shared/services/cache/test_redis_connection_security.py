"""Test to verify Redis password is not logged in plaintext."""

from unittest.mock import Mock, patch

from redis import ConnectionPool

from app.shared.services.cache.redis_connection import create_redis_client


class TestRedisConnectionSecurityLogging:
    """Test suite for verifying sensitive data is not logged."""

    @patch("app.shared.services.cache.redis_connection.logger")
    @patch("app.shared.services.cache.redis_connection.ConnectionPool")
    @patch("app.shared.services.cache.redis_connection.Redis")
    def test_password_not_logged_in_url_components(
        self,
        mock_redis: Mock,
        mock_pool_class: Mock,
        mock_logger: Mock,
    ) -> None:
        """Test that Redis password is NOT included in logged url_components."""
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool_class.from_url.return_value = mock_pool

        # Create client with a URL that contains a password
        redis_url_with_password = "redis://user:secret-password@redis-host:6379/0"
        create_redis_client(redis_url=redis_url_with_password)

        # Get the redis_connection_factory_creating log call
        log_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "redis_connection_factory_creating"
        ]
        assert len(log_calls) > 0, "Expected redis_connection_factory_creating log"

        log_call = log_calls[0]
        logged_components = log_call[1]["redis_url_components"]

        # Verify password is NOT in the logged components
        assert "password" not in logged_components, (
            "Password field should not be present in logged url_components"
        )
        assert logged_components.get("password") is None, (
            "Password should be None or absent from logged data"
        )

        # Verify other components are still logged (for debugging)
        assert logged_components.get("hostname") == "redis-host"
        assert logged_components.get("port") == "6379"
        assert logged_components.get("username") == "user"
        assert logged_components.get("scheme") == "redis"
        assert logged_components.get("path") == "/0"

    @patch("app.shared.services.cache.redis_connection.logger")
    @patch("app.shared.services.cache.redis_connection.ConnectionPool")
    @patch("app.shared.services.cache.redis_connection.Redis")
    def test_password_not_logged_for_default_user(
        self,
        mock_redis: Mock,
        mock_pool_class: Mock,
        mock_logger: Mock,
    ) -> None:
        """Test that password is not logged even for default user authentication."""
        mock_pool = Mock(spec=ConnectionPool)
        mock_pool_class.from_url.return_value = mock_pool

        # Redis default user format: redis://:password@host:port
        redis_url = "redis://:mypassword123@redis:6379/0"
        create_redis_client(redis_url=redis_url)

        # Get the redis_connection_factory_creating log call
        log_calls = [
            call
            for call in mock_logger.info.call_args_list
            if call[0][0] == "redis_connection_factory_creating"
        ]
        assert len(log_calls) > 0

        log_call = log_calls[0]
        logged_components = log_call[1]["redis_url_components"]

        # Verify password is not logged
        assert "password" not in logged_components or logged_components.get("password") is None
        assert "mypassword123" not in str(logged_components)
