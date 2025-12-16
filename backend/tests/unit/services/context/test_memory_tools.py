"""Unit tests for search_memory MCP tool.

Issue #245: Agent Memory Access (RAG)
Tests the reactive recall tool that agents use to search past analyses.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent_memory import AgentMemory, MemoryType
from app.domains.analysis.services.context.memory_tools import search_memory
from app.shared.services.memory import MemorySearchResult

@pytest.mark.unit


@pytest.mark.asyncio
class TestSearchMemoryTool:
    """Tests for the search_memory tool."""

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_success(self, mock_session_factory):
        """Test search_memory returns formatted results on success."""
        # Setup mock session
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        # Create mock search results
        mock_memory = MagicMock(spec=AgentMemory)
        mock_memory.id = uuid.uuid4()
        mock_memory.content = "SQL injection prevention best practice"
        mock_memory.memory_type = "best_practice"

        mock_result = MemorySearchResult(memory=mock_memory, similarity=0.88)

        # Mock the service search method
        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[mock_result])
            mock_service_class.return_value = mock_service

            # Call the tool via .invoke()
            result = await search_memory.ainvoke(
                {
                    "query": "SQL injection prevention",
                    "memory_type": "best_practice",
                    "limit": 5,
                }
            )

            # Verify result formatting
            assert "Found 1 relevant memories" in result
            assert "[best_practice]" in result
            assert "(relevance: 0.88)" in result
            assert "SQL injection prevention best practice" in result

            # Verify service was called correctly
            mock_service.search.assert_called_once()
            call_kwargs = mock_service.search.call_args[1]
            assert call_kwargs["query"] == "SQL injection prevention"
            assert call_kwargs["memory_type"] == MemoryType.BEST_PRACTICE
            assert call_kwargs["limit"] == 5

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_invalid_memory_type(self, mock_session_factory):
        """Test search_memory returns error for invalid memory type."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await search_memory.ainvoke(
            {
                "query": "test query",
                "memory_type": "invalid_type",
                "limit": 5,
            }
        )

        # Should return error message
        assert "Invalid memory_type" in result
        assert "invalid_type" in result
        assert "Valid options" in result

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_no_results(self, mock_session_factory):
        """Test search_memory returns helpful message when no results found."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            result = await search_memory.ainvoke(
                {
                    "query": "nonexistent pattern",
                    "memory_type": "all",
                    "limit": 5,
                }
            )

            assert "No relevant memories found" in result
            assert "Try broadening your search terms" in result

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_database_error(self, mock_session_factory):
        """Test search_memory handles database errors gracefully."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(side_effect=Exception("Database connection lost"))
            mock_service_class.return_value = mock_service

            result = await search_memory.ainvoke(
                {
                    "query": "test query",
                    "memory_type": "all",
                    "limit": 5,
                }
            )

            assert "Error searching memories" in result
            assert "Database connection lost" in result

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_all_type(self, mock_session_factory):
        """Test search_memory with 'all' type searches across all types."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            await search_memory.ainvoke(
                {
                    "query": "test query",
                    "memory_type": "all",
                    "limit": 5,
                }
            )

            # Verify search was called with memory_type=None (searches all)
            call_kwargs = mock_service.search.call_args[1]
            assert call_kwargs["memory_type"] is None

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_limit_validation(self, mock_session_factory):
        """Test search_memory respects limit parameter."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            await search_memory.ainvoke(
                {
                    "query": "test query",
                    "memory_type": "all",
                    "limit": 3,
                }
            )

            call_kwargs = mock_service.search.call_args[1]
            assert call_kwargs["limit"] == 3

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_multiple_results(self, mock_session_factory):
        """Test search_memory formats multiple results correctly."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        # Create multiple mock results
        mock_results = []
        for i in range(3):
            mock_memory = MagicMock(spec=AgentMemory)
            mock_memory.id = uuid.uuid4()
            mock_memory.content = f"Memory content {i + 1}"
            mock_memory.memory_type = "analysis_summary"
            mock_results.append(MemorySearchResult(memory=mock_memory, similarity=0.9 - i * 0.1))

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=mock_results)
            mock_service_class.return_value = mock_service

            result = await search_memory.ainvoke(
                {
                    "query": "test query",
                    "memory_type": "all",
                    "limit": 5,
                }
            )

            # Verify all results are numbered and formatted
            assert "Found 3 relevant memories" in result
            assert "1. [analysis_summary]" in result
            assert "2. [analysis_summary]" in result
            assert "3. [analysis_summary]" in result
            assert "Memory content 1" in result
            assert "Memory content 2" in result
            assert "Memory content 3" in result

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_empty_query(self, mock_session_factory):
        """Test search_memory handles empty query string."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            result = await search_memory.ainvoke(
                {
                    "query": "",
                    "memory_type": "all",
                    "limit": 5,
                }
            )

            # Should still call search (embedding service handles empty)
            mock_service.search.assert_called_once()
            call_kwargs = mock_service.search.call_args[1]
            assert call_kwargs["query"] == ""


@pytest.mark.asyncio
class TestSearchMemoryToolEdgeCases:
    """Tests for edge cases in search_memory tool."""

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_very_long_query(self, mock_session_factory):
        """Test search_memory handles very long queries."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            long_query = "x" * 1000

            await search_memory.ainvoke(
                {
                    "query": long_query,
                    "memory_type": "all",
                    "limit": 5,
                }
            )

            # Should pass query through (truncation happens in logging only)
            mock_service.search.assert_called_once()
            call_kwargs = mock_service.search.call_args[1]
            assert call_kwargs["query"] == long_query

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_special_characters(self, mock_session_factory):
        """Test search_memory handles special characters in query."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            query_with_special = "SQL injection: <script>alert('xss')</script>"

            result = await search_memory.ainvoke(
                {
                    "query": query_with_special,
                    "memory_type": "all",
                    "limit": 5,
                }
            )

            # Should handle without crashing
            assert "No relevant memories found" in result or "Found" in result

    @patch("app.domains.analysis.services.context.memory_tools.get_session_factory")
    async def test_search_memory_specific_memory_types(self, mock_session_factory):
        """Test search_memory with each specific memory type."""
        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("app.domains.analysis.services.context.memory_tools.AgentMemoryService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.search = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            # Test each valid memory type
            for memory_type_str in [
                "analysis_summary",
                "vulnerability_pattern",
                "best_practice",
                "agent_finding",
            ]:
                await search_memory.ainvoke(
                    {
                        "query": "test",
                        "memory_type": memory_type_str,
                        "limit": 5,
                    }
                )

                call_kwargs = mock_service.search.call_args[1]
                assert call_kwargs["memory_type"].value == memory_type_str
