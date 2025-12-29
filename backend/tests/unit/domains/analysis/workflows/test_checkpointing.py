"""Unit tests for Redis Checkpointing functionality (GAP 3).

Tests the checkpointer selection logic in graph_builder._get_checkpointer()
to ensure proper fallback chain and configuration handling.

Reference: Issue #576 (GAP 3) - Redis Checkpointing
"""

from unittest.mock import MagicMock, patch

import pytest
from langgraph.checkpoint.memory import MemorySaver


class TestCheckpointerSelection:
    """Test _get_checkpointer() function fallback chain."""

    def test_test_mode_returns_memory_saver(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that test mode (PYTEST_CURRENT_TEST set) returns MemorySaver."""
        # Set PYTEST_CURRENT_TEST to simulate test environment
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_checkpointing.py::test_something")

        from app.domains.analysis.workflows.graph_builder import _get_checkpointer

        checkpointer = _get_checkpointer()

        assert isinstance(checkpointer, MemorySaver)

    def test_redis_enabled_with_valid_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Redis checkpointer when USE_REDIS_CHECKPOINT=true and REDIS_URL is set."""
        # Clear PYTEST_CURRENT_TEST to exit test mode
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Mock RedisSaver import and instance
        mock_redis_saver_class = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_saver_class.from_conn_string.return_value = mock_redis_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.RedisSaver",
                mock_redis_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            # Configure settings for Redis checkpointing
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = "redis://localhost:6380"
            mock_settings.REDIS_CHECKPOINT_TTL = 3600
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should return RedisSaver instance
            assert checkpointer == mock_redis_instance

            # Should call from_conn_string with correct parameters
            mock_redis_saver_class.from_conn_string.assert_called_once_with(
                "redis://localhost:6380",
                ttl={"default_ttl": 60.0},  # 3600 seconds / 60 = 60 minutes
            )

    def test_redis_enabled_ttl_conversion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that TTL is correctly converted from seconds to minutes for RedisSaver."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_redis_saver_class = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_saver_class.from_conn_string.return_value = mock_redis_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.RedisSaver",
                mock_redis_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = "redis://localhost:6380"
            mock_settings.REDIS_CHECKPOINT_TTL = 1800  # 30 minutes in seconds
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            _get_checkpointer()

            # Should convert 1800 seconds to 30 minutes
            call_args = mock_redis_saver_class.from_conn_string.call_args
            assert call_args[1]["ttl"]["default_ttl"] == 30.0

    def test_redis_enabled_but_connection_error_fallback_to_postgres(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to PostgreSQL when Redis connection fails."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Mock RedisSaver to raise ConnectionError
        mock_redis_saver_class = MagicMock()
        mock_redis_saver_class.from_conn_string.side_effect = ConnectionError("Redis unavailable")

        # Mock PostgresSaver
        mock_postgres_saver_class = MagicMock()
        mock_postgres_instance = MagicMock()
        mock_postgres_saver_class.from_conn_string.return_value = mock_postgres_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.RedisSaver",
                mock_redis_saver_class,
            ),
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = "redis://localhost:6380"
            mock_settings.REDIS_CHECKPOINT_TTL = 3600
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should fallback to PostgresSaver
            assert checkpointer == mock_postgres_instance
            mock_postgres_saver_class.from_conn_string.assert_called_once_with(
                "postgresql://localhost/db"
            )

    def test_redis_enabled_but_value_error_fallback_to_postgres(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to PostgreSQL when Redis raises ValueError (invalid config)."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_redis_saver_class = MagicMock()
        mock_redis_saver_class.from_conn_string.side_effect = ValueError("Invalid Redis URL")

        mock_postgres_saver_class = MagicMock()
        mock_postgres_instance = MagicMock()
        mock_postgres_saver_class.from_conn_string.return_value = mock_postgres_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.RedisSaver",
                mock_redis_saver_class,
            ),
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = "invalid-url"
            mock_settings.REDIS_CHECKPOINT_TTL = 3600
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should fallback to PostgresSaver
            assert checkpointer == mock_postgres_instance

    def test_redis_disabled_uses_postgres(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test PostgreSQL checkpointer when USE_REDIS_CHECKPOINT=false."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_postgres_saver_class = MagicMock()
        mock_postgres_instance = MagicMock()
        mock_postgres_saver_class.from_conn_string.return_value = mock_postgres_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            # Redis disabled
            mock_settings.USE_REDIS_CHECKPOINT = False
            mock_settings.REDIS_URL = "redis://localhost:6380"
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should use PostgresSaver (skip Redis)
            assert checkpointer == mock_postgres_instance
            mock_postgres_saver_class.from_conn_string.assert_called_once_with(
                "postgresql://localhost/db"
            )

    def test_redis_enabled_but_no_redis_url_uses_postgres(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to PostgreSQL when Redis enabled but REDIS_URL not set."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_postgres_saver_class = MagicMock()
        mock_postgres_instance = MagicMock()
        mock_postgres_saver_class.from_conn_string.return_value = mock_postgres_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = None  # No Redis URL
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should skip Redis and use PostgreSQL
            assert checkpointer == mock_postgres_instance

    def test_redis_not_available_uses_postgres(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback to PostgreSQL when RedisSaver import fails."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_postgres_saver_class = MagicMock()
        mock_postgres_instance = MagicMock()
        mock_postgres_saver_class.from_conn_string.return_value = mock_postgres_instance

        with (
            # Simulate RedisSaver import failure by setting to None
            patch("app.domains.analysis.workflows.graph_builder.RedisSaver", None),
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = "redis://localhost:6380"
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should fallback to PostgreSQL
            assert checkpointer == mock_postgres_instance

    def test_postgres_connection_error_fallback_to_memory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to MemorySaver when PostgreSQL connection fails."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_postgres_saver_class = MagicMock()
        mock_postgres_saver_class.from_conn_string.side_effect = ConnectionError("DB unavailable")

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = False
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should fallback to MemorySaver
            assert isinstance(checkpointer, MemorySaver)

    def test_postgres_value_error_fallback_to_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback to MemorySaver when PostgreSQL raises ValueError."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_postgres_saver_class = MagicMock()
        mock_postgres_saver_class.from_conn_string.side_effect = ValueError("Invalid DB URL")

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = False
            mock_settings.DATABASE_URL = "invalid-url"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should fallback to MemorySaver
            assert isinstance(checkpointer, MemorySaver)

    def test_no_database_configured_uses_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test MemorySaver when no database is configured (development mode)."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Must patch settings in the graph_builder module where it's already imported
        with patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings:
            mock_settings.USE_REDIS_CHECKPOINT = False
            mock_settings.REDIS_URL = None
            mock_settings.DATABASE_URL = None  # No database

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should use MemorySaver (development fallback)
            assert isinstance(checkpointer, MemorySaver)

    def test_postgres_not_available_uses_memory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback to MemorySaver when PostgresSaver import fails."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        with (
            # Simulate PostgresSaver import failure
            patch("app.domains.analysis.workflows.graph_builder.PostgresSaver", None),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = False
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should fallback to MemorySaver
            assert isinstance(checkpointer, MemorySaver)


class TestCheckpointerConfiguration:
    """Test configuration settings for checkpointing."""

    def test_use_redis_checkpoint_default(self) -> None:
        """Test USE_REDIS_CHECKPOINT defaults to false."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.USE_REDIS_CHECKPOINT is False

    def test_redis_checkpoint_ttl_default(self) -> None:
        """Test REDIS_CHECKPOINT_TTL defaults to 3600 seconds (1 hour)."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.REDIS_CHECKPOINT_TTL == 3600

    def test_use_redis_checkpoint_enabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test USE_REDIS_CHECKPOINT can be enabled via environment variable."""
        monkeypatch.setenv("USE_REDIS_CHECKPOINT", "true")

        from app.core.config import Settings

        settings = Settings()

        assert settings.USE_REDIS_CHECKPOINT is True

    def test_redis_checkpoint_ttl_custom(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test REDIS_CHECKPOINT_TTL can be customized via environment variable."""
        monkeypatch.setenv("REDIS_CHECKPOINT_TTL", "7200")

        from app.core.config import Settings

        settings = Settings()

        assert settings.REDIS_CHECKPOINT_TTL == 7200


class TestCheckpointerFallbackChain:
    """Test complete fallback chain scenarios."""

    def test_fallback_chain_redis_to_postgres_to_memory(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test full fallback: Redis fails -> PostgreSQL fails -> MemorySaver."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        # Both Redis and PostgreSQL fail
        mock_redis_saver_class = MagicMock()
        mock_redis_saver_class.from_conn_string.side_effect = ConnectionError("Redis down")

        mock_postgres_saver_class = MagicMock()
        mock_postgres_saver_class.from_conn_string.side_effect = ConnectionError("DB down")

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.RedisSaver",
                mock_redis_saver_class,
            ),
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = "redis://localhost:6380"
            mock_settings.REDIS_CHECKPOINT_TTL = 3600
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            from app.domains.analysis.workflows.graph_builder import _get_checkpointer

            checkpointer = _get_checkpointer()

            # Should fallback all the way to MemorySaver
            assert isinstance(checkpointer, MemorySaver)

    def test_fallback_chain_priority_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that checkpointer selection follows priority: Test > Redis > PostgreSQL > Memory."""
        # Test 1: Test mode has highest priority
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test.py::test")

        from app.domains.analysis.workflows.graph_builder import _get_checkpointer

        checkpointer = _get_checkpointer()
        assert isinstance(checkpointer, MemorySaver)

        # Test 2: Redis enabled (second priority after test mode is cleared)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        mock_redis_saver_class = MagicMock()
        mock_redis_instance = MagicMock()
        mock_redis_saver_class.from_conn_string.return_value = mock_redis_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.RedisSaver",
                mock_redis_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = True
            mock_settings.REDIS_URL = "redis://localhost:6380"
            mock_settings.REDIS_CHECKPOINT_TTL = 3600
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            checkpointer = _get_checkpointer()
            # Should use Redis when test mode is off and Redis is configured
            assert checkpointer == mock_redis_instance

        # Test 3: PostgreSQL (third priority when Redis is disabled)
        mock_postgres_saver_class = MagicMock()
        mock_postgres_instance = MagicMock()
        mock_postgres_saver_class.from_conn_string.return_value = mock_postgres_instance

        with (
            patch(
                "app.domains.analysis.workflows.graph_builder.PostgresSaver",
                mock_postgres_saver_class,
            ),
            patch("app.domains.analysis.workflows.graph_builder.settings") as mock_settings,
        ):
            mock_settings.USE_REDIS_CHECKPOINT = False
            mock_settings.DATABASE_URL = "postgresql://localhost/db"

            checkpointer = _get_checkpointer()
            # Should use PostgreSQL when Redis is disabled
            assert checkpointer == mock_postgres_instance


class TestCheckpointerIntegration:
    """Test integration with build_analysis_graph."""

    def test_build_graph_with_checkpointer_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that build_analysis_graph accepts checkpointer_override parameter."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        from app.domains.analysis.workflows.graph_builder import build_analysis_graph

        # Create custom checkpointer
        custom_checkpointer = MemorySaver()

        # Build graph with override
        graph = build_analysis_graph(checkpointer_override=custom_checkpointer)

        # Graph should be compiled with custom checkpointer
        assert graph is not None
        # Note: Can't directly access compiled graph's checkpointer,
        # but we verify it accepts the parameter without error

    def test_build_graph_uses_default_checkpointer(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that build_analysis_graph uses _get_checkpointer() by default."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.USE_REDIS_CHECKPOINT = False
            mock_settings.DATABASE_URL = None

            from app.domains.analysis.workflows.graph_builder import build_analysis_graph

            # Build graph without override (should use _get_checkpointer)
            graph = build_analysis_graph()

            # Should compile successfully
            assert graph is not None
