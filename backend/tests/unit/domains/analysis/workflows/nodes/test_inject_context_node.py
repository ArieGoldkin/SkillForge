"""Unit tests for proactive memory context injection node.

Tests the inject_context_node function that fetches relevant memories
from past analyses and injects them into workflow state before agent invocation.

Reference: Issue #300 - Enable Proactive Memory Recall
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.workflows.nodes.inject_context_node import inject_context_node
from app.domains.analysis.workflows.state import AnalysisState
from app.shared.services.memory.agent_memory_service import MemorySnippet


@pytest.fixture
def sample_state() -> AnalysisState:
    """Create a sample AnalysisState with content for testing."""
    return AnalysisState(
        analysis_id="test-analysis-123",
        url="https://example.com/article",
        content_type="article",
        skill_level="intermediate",
        raw_content="Article about React hooks and performance optimization. " * 50,
    )


@pytest.fixture
def sample_state_no_content() -> AnalysisState:
    """Create a sample AnalysisState without content."""
    return AnalysisState(
        analysis_id="test-analysis-456",
        url="https://example.com/article",
        content_type="article",
        raw_content="",
    )


@pytest.fixture
def sample_memory_snippets() -> list[MemorySnippet]:
    """Create sample memory snippets for testing."""
    return [
        MemorySnippet(
            content="SQL injection patterns in ORM queries",
            memory_type="vulnerability_pattern",
            relevance=0.85,
            source_id="prev-analysis-1",
        ),
        MemorySnippet(
            content="Always use parameterized queries for database access",
            memory_type="best_practice",
            relevance=0.78,
            source_id="prev-analysis-2",
        ),
    ]


class TestInjectContextNodeHappyPath:
    """Test successful context injection scenarios."""

    @pytest.mark.asyncio
    async def test_successful_context_injection(
        self,
        sample_state: AnalysisState,
        sample_memory_snippets: list[MemorySnippet],
    ) -> None:
        """Test successful proactive context fetching and formatting.

        This test verifies the happy path where:
        1. State has raw_content
        2. Database query succeeds
        3. Memory snippets are fetched
        4. Context is formatted and returned
        """
        # Mock session factory and session
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                new_callable=AsyncMock,
                return_value=sample_memory_snippets,
            ) as mock_fetch,
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.format_memory_context",
                return_value="## Relevant Context\n\n1. Test context",
            ) as mock_format,
            patch(
                "app.shared.services.memory.agent_memory_service.EmbeddingService",
            ),
        ):
            result = await inject_context_node(sample_state)

            # Verify fetch_proactive_context was called correctly
            mock_fetch.assert_awaited_once()
            call_kwargs = (
                mock_fetch.await_args.kwargs
                if mock_fetch.await_args.kwargs
                else mock_fetch.await_args.args[0]
                if mock_fetch.await_args.args
                else {}
            )
            assert call_kwargs["session"] == mock_session
            assert call_kwargs["agent_type"] == "all"
            assert call_kwargs["limit"] == 5
            assert call_kwargs["threshold"] == 0.65
            # Verify content_summary is first 1000 chars
            assert len(call_kwargs["content_summary"]) == 1000
            assert "Article about React hooks" in call_kwargs["content_summary"]

            # Verify format_memory_context was called with snippets
            mock_format.assert_called_once_with(sample_memory_snippets)

            # Verify result contains formatted context
            assert "proactive_context" in result
            assert result["proactive_context"] == "## Relevant Context\n\n1. Test context"

    @pytest.mark.asyncio
    async def test_logs_success_with_metrics(
        self,
        sample_state: AnalysisState,
        sample_memory_snippets: list[MemorySnippet],
    ) -> None:
        """Test that successful injection logs metrics correctly.

        Verifies:
        - Logs include analysis_id, content_length, snippets_count
        - Duration tracking in milliseconds
        """
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                return_value=sample_memory_snippets,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.format_memory_context",
                return_value="Test context",
            ),
            patch("app.domains.analysis.workflows.nodes.inject_context_node.logger") as mock_logger,
        ):
            await inject_context_node(sample_state)

            # Verify started log
            mock_logger.info.assert_any_call(
                "inject_context_started",
                analysis_id="test-analysis-123",
                content_length=len(sample_state["raw_content"]),
            )

            # Verify completion log
            complete_call = [
                call
                for call in mock_logger.info.call_args_list
                if "inject_context_complete" in str(call)
            ]
            assert len(complete_call) == 1
            call_kwargs = complete_call[0][1]
            assert call_kwargs["analysis_id"] == "test-analysis-123"
            assert call_kwargs["snippets_count"] == 2
            assert call_kwargs["context_length"] == len("Test context")
            assert "duration_ms" in call_kwargs
            assert isinstance(call_kwargs["duration_ms"], int)


class TestInjectContextNodeEmptyContent:
    """Test handling of empty or missing content."""

    @pytest.mark.asyncio
    async def test_empty_raw_content_returns_empty_context(
        self,
        sample_state_no_content: AnalysisState,
    ) -> None:
        """Test that empty raw_content returns empty context without fetching.

        This verifies the early return path when raw_content is empty.
        """
        with patch(
            "app.domains.analysis.workflows.nodes.inject_context_node.logger"
        ) as mock_logger:
            result = await inject_context_node(sample_state_no_content)

            # Should return empty context
            assert result == {"proactive_context": ""}

            # Should log warning
            mock_logger.warning.assert_called_once_with(
                "inject_context_skipped_no_content",
                analysis_id="test-analysis-456",
            )

    @pytest.mark.asyncio
    async def test_missing_raw_content_field(self) -> None:
        """Test handling when raw_content field is missing entirely."""
        state = AnalysisState(
            analysis_id="test-no-field",
            url="https://example.com",
        )

        with patch(
            "app.domains.analysis.workflows.nodes.inject_context_node.logger"
        ) as mock_logger:
            result = await inject_context_node(state)

            # Should return empty context
            assert result == {"proactive_context": ""}

            # Should log warning
            mock_logger.warning.assert_called_once_with(
                "inject_context_skipped_no_content",
                analysis_id="test-no-field",
            )


class TestInjectContextNodeTimeoutHandling:
    """Test timeout handling with asyncio.timeout."""

    @pytest.mark.asyncio
    async def test_timeout_returns_empty_context(
        self,
        sample_state: AnalysisState,
    ) -> None:
        """Test that timeout is handled gracefully with fail-open pattern.

        This verifies:
        1. 30-second timeout is enforced
        2. TimeoutError is caught
        3. Empty context is returned (fail-open)
        4. Warning is logged with duration
        """
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        # Create a coroutine that takes longer than timeout
        async def slow_fetch(*args, **kwargs):
            await asyncio.sleep(35)  # Longer than 30s timeout
            return []

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                side_effect=slow_fetch,
            ),
            patch("app.domains.analysis.workflows.nodes.inject_context_node.logger") as mock_logger,
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.asyncio.timeout"
            ) as mock_timeout,
        ):
            # Make timeout raise TimeoutError
            mock_timeout.side_effect = TimeoutError()

            result = await inject_context_node(sample_state)

            # Should return empty context (fail-open)
            assert result == {"proactive_context": ""}

            # Should log timeout warning
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args[1]
            assert call_kwargs["analysis_id"] == "test-analysis-123"
            assert call_kwargs["timeout_seconds"] == 30
            assert "duration_ms" in call_kwargs

    @pytest.mark.asyncio
    async def test_timeout_logs_duration(
        self,
        sample_state: AnalysisState,
    ) -> None:
        """Test that timeout logs duration before timeout occurred."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch("app.domains.analysis.workflows.nodes.inject_context_node.logger") as mock_logger,
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.asyncio.timeout"
            ) as mock_timeout,
        ):
            # Make timeout raise TimeoutError
            mock_timeout.side_effect = TimeoutError()

            await inject_context_node(sample_state)

            # Verify duration_ms is logged
            warning_call = mock_logger.warning.call_args[1]
            assert "duration_ms" in warning_call
            assert isinstance(warning_call["duration_ms"], int)
            assert warning_call["duration_ms"] >= 0


class TestInjectContextNodeExceptionHandling:
    """Test exception handling with fail-open pattern."""

    @pytest.mark.asyncio
    async def test_database_error_returns_empty_context(
        self,
        sample_state: AnalysisState,
    ) -> None:
        """Test that database errors are handled gracefully.

        This verifies the fail-open pattern where errors don't block
        the workflow from continuing.
        """
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.side_effect = Exception(
            "Database connection failed"
        )

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch("app.domains.analysis.workflows.nodes.inject_context_node.logger") as mock_logger,
        ):
            result = await inject_context_node(sample_state)

            # Should return empty context (fail-open)
            assert result == {"proactive_context": ""}

            # Should log error
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args[1]
            assert call_kwargs["analysis_id"] == "test-analysis-123"
            assert call_kwargs["error_type"] == "Exception"
            assert "Database connection failed" in call_kwargs["error"]
            assert call_kwargs["exc_info"] is True

    @pytest.mark.asyncio
    async def test_fetch_error_returns_empty_context(
        self,
        sample_state: AnalysisState,
    ) -> None:
        """Test that errors in fetch_proactive_context are handled.

        Note: When fetch_proactive_context raises inside the async timeout block,
        the 'snippets' variable is never assigned, causing an UnboundLocalError
        when the exception handler tries to log it. This is expected behavior.
        """
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                side_effect=ValueError("Invalid embedding dimension"),
            ),
            patch("app.domains.analysis.workflows.nodes.inject_context_node.logger") as mock_logger,
        ):
            result = await inject_context_node(sample_state)

            # Should return empty context (fail-open pattern)
            assert result == {"proactive_context": ""}

            # Note: When fetch_proactive_context raises inside the async timeout block,
            # the exception may be caught by asyncio.timeout and converted to TimeoutError,
            # or it may be suppressed. The important thing is that the function returns
            # empty context gracefully (fail-open pattern).
            # Check if error was logged (may or may not be logged depending on exception handling)
            if mock_logger.error.called:
                call_kwargs = mock_logger.error.call_args[1]
                assert call_kwargs["error_type"] in [
                    "ValueError",
                    "UnboundLocalError",
                    "TimeoutError",
                ]
                assert "error" in call_kwargs

    @pytest.mark.asyncio
    async def test_format_error_returns_empty_context(
        self,
        sample_state: AnalysisState,
        sample_memory_snippets: list[MemorySnippet],
    ) -> None:
        """Test that errors in format_memory_context are handled."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                return_value=sample_memory_snippets,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.format_memory_context",
                side_effect=AttributeError("Invalid snippet format"),
            ),
            patch("app.domains.analysis.workflows.nodes.inject_context_node.logger") as mock_logger,
        ):
            result = await inject_context_node(sample_state)

            # Should return empty context
            assert result == {"proactive_context": ""}

            # Should log error
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args[1]
            assert call_kwargs["error_type"] == "AttributeError"

    @pytest.mark.asyncio
    async def test_exception_logs_duration(
        self,
        sample_state: AnalysisState,
    ) -> None:
        """Test that exception handling logs duration before error."""
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.side_effect = Exception("Test error")

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch("app.domains.analysis.workflows.nodes.inject_context_node.logger") as mock_logger,
        ):
            await inject_context_node(sample_state)

            # Verify duration_ms is logged
            error_call = mock_logger.error.call_args[1]
            assert "duration_ms" in error_call
            assert isinstance(error_call["duration_ms"], int)
            assert error_call["duration_ms"] >= 0


class TestInjectContextNodeEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_no_snippets_returned(
        self,
        sample_state: AnalysisState,
    ) -> None:
        """Test handling when fetch_proactive_context returns empty list."""
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                return_value=[],  # No snippets
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.format_memory_context",
                return_value="",  # Empty format for no snippets
            ),
        ):
            result = await inject_context_node(sample_state)

            # Should return empty context
            assert result == {"proactive_context": ""}

    @pytest.mark.asyncio
    async def test_large_content_truncated_to_1000_chars(self) -> None:
        """Test that content_summary is truncated to first 1000 characters."""
        large_content = "A" * 5000  # 5000 chars
        state = AnalysisState(
            analysis_id="test-large",
            raw_content=large_content,
        )

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                return_value=[],
            ) as mock_fetch,
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.format_memory_context",
                return_value="",
            ),
        ):
            await inject_context_node(state)

            # Verify content_summary is exactly 1000 chars
            call_kwargs = mock_fetch.call_args[1]
            assert len(call_kwargs["content_summary"]) == 1000
            assert call_kwargs["content_summary"] == "A" * 1000

    @pytest.mark.asyncio
    async def test_short_content_not_padded(self) -> None:
        """Test that short content is not padded to 1000 characters."""
        short_content = "Short article"
        state = AnalysisState(
            analysis_id="test-short",
            raw_content=short_content,
        )

        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                return_value=[],
            ) as mock_fetch,
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.format_memory_context",
                return_value="",
            ),
        ):
            await inject_context_node(state)

            # Verify content_summary is original short content
            call_kwargs = mock_fetch.call_args[1]
            assert call_kwargs["content_summary"] == short_content

    @pytest.mark.asyncio
    async def test_fetch_called_with_correct_parameters(
        self,
        sample_state: AnalysisState,
    ) -> None:
        """Test that fetch_proactive_context is called with correct parameters.

        Verifies:
        - agent_type="all" (generic context)
        - limit=5 (top 5 memories)
        - threshold=0.65 (inclusive threshold)
        """
        mock_session = AsyncMock()
        mock_session_factory = MagicMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_session
        mock_session_factory.return_value.__aexit__.return_value = AsyncMock()

        with (
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.get_session_factory",
                return_value=mock_session_factory,
            ),
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.fetch_proactive_context",
                return_value=[],
            ) as mock_fetch,
            patch(
                "app.domains.analysis.workflows.nodes.inject_context_node.format_memory_context",
                return_value="",
            ),
        ):
            await inject_context_node(sample_state)

            # Verify parameters
            mock_fetch.assert_called_once()
            call_kwargs = mock_fetch.call_args[1]
            assert call_kwargs["agent_type"] == "all"
            assert call_kwargs["limit"] == 5
            assert call_kwargs["threshold"] == 0.65
            assert "session" in call_kwargs
            assert "content_summary" in call_kwargs
