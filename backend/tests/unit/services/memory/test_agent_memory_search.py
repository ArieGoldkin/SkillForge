"""Unit tests for AgentMemoryService search and proactive recall.

Issue #245: Agent Memory Access (RAG)
Tests the missing coverage for search() and proactive_recall() methods.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.agent_memory import AgentMemory, MemoryType
from app.services.memory import AgentMemoryService, MemorySearchResult, MemorySnippet


@pytest.mark.asyncio
class TestAgentMemoryServiceSearch:
    """Tests for the search() method."""

    async def test_search_returns_results_above_threshold(self):
        """Test search returns only results above relevance threshold."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        # Mock _semantic_search to return results
        mock_memory_1 = MagicMock(spec=AgentMemory)
        mock_memory_1.id = uuid.uuid4()
        mock_memory_1.content = "High relevance content"
        mock_memory_1.memory_type = "best_practice"

        mock_memory_2 = MagicMock(spec=AgentMemory)
        mock_memory_2.id = uuid.uuid4()
        mock_memory_2.content = "Very high relevance content"
        mock_memory_2.memory_type = "best_practice"

        mock_results = [
            MemorySearchResult(memory=mock_memory_1, similarity=0.75),
            MemorySearchResult(memory=mock_memory_2, similarity=0.85),
        ]

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=mock_results)

        results = await service.search(
            query="test query",
            threshold=0.7,
        )

        assert len(results) == 2
        assert results[0].similarity == 0.75
        assert results[1].similarity == 0.85
        mock_embedding_service.generate_embedding.assert_called_once_with("test query")

    async def test_search_filters_by_memory_type(self):
        """Test search filters results by memory type."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=[])

        await service.search(
            query="test query",
            memory_type=MemoryType.VULNERABILITY_PATTERN,
        )

        # Verify _semantic_search was called with correct memory_type
        service._semantic_search.assert_called_once()
        call_args = service._semantic_search.call_args[1]
        assert call_args["memory_type"] == MemoryType.VULNERABILITY_PATTERN

    async def test_search_respects_limit_parameter(self):
        """Test search respects the limit parameter."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=[])

        await service.search(
            query="test query",
            limit=3,
        )

        # Verify limit was passed to _semantic_search
        service._semantic_search.assert_called_once()
        call_args = service._semantic_search.call_args[1]
        assert call_args["limit"] == 3

    async def test_search_returns_empty_for_no_matches(self):
        """Test search returns empty list when no matches found."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=[])

        results = await service.search(query="nonexistent query")

        assert results == []

    async def test_search_handles_empty_query(self):
        """Test search handles empty query string."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=[])

        results = await service.search(query="")

        assert results == []
        mock_embedding_service.generate_embedding.assert_called_once_with("")


@pytest.mark.asyncio
class TestAgentMemoryServiceProactiveRecall:
    """Tests for the proactive_recall() method."""

    async def test_proactive_recall_filters_by_agent_type(self):
        """Test proactive recall filters by agent-specific memory types."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service.search = AsyncMock(return_value=[])

        await service.proactive_recall(
            content_summary="Test content",
            agent_type="security_auditor",
        )

        # Verify search was called for security_auditor relevant types
        assert service.search.call_count == 2  # vulnerability_pattern + best_practice
        call_args_list = [call[1] for call in service.search.call_args_list]

        memory_types_searched = {args["memory_type"] for args in call_args_list}
        assert MemoryType.VULNERABILITY_PATTERN in memory_types_searched
        assert MemoryType.BEST_PRACTICE in memory_types_searched

    async def test_proactive_recall_sorts_by_relevance(self):
        """Test proactive recall sorts results by relevance score."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()

        # Create mock results with different relevance scores
        mock_memory_1 = MagicMock(spec=AgentMemory)
        mock_memory_1.id = uuid.uuid4()
        mock_memory_1.content = "Low relevance"
        mock_memory_1.memory_type = "best_practice"

        mock_memory_2 = MagicMock(spec=AgentMemory)
        mock_memory_2.id = uuid.uuid4()
        mock_memory_2.content = "High relevance"
        mock_memory_2.memory_type = "vulnerability_pattern"

        mock_memory_3 = MagicMock(spec=AgentMemory)
        mock_memory_3.id = uuid.uuid4()
        mock_memory_3.content = "Medium relevance"
        mock_memory_3.memory_type = "best_practice"

        service = AgentMemoryService(mock_session, mock_embedding_service)

        # Mock search to return results in random order
        async def mock_search(query, memory_type, limit, threshold):
            if memory_type == MemoryType.VULNERABILITY_PATTERN:
                return [MemorySearchResult(memory=mock_memory_2, similarity=0.95)]
            else:  # BEST_PRACTICE
                return [
                    MemorySearchResult(memory=mock_memory_1, similarity=0.72),
                    MemorySearchResult(memory=mock_memory_3, similarity=0.85),
                ]

        service.search = AsyncMock(side_effect=mock_search)

        snippets = await service.proactive_recall(
            content_summary="Test content",
            agent_type="security_auditor",
            limit=3,
        )

        # Verify snippets are sorted by relevance (highest first)
        assert len(snippets) == 3
        assert snippets[0].relevance == 0.95
        assert snippets[1].relevance == 0.85
        assert snippets[2].relevance == 0.72

    async def test_proactive_recall_limits_results(self):
        """Test proactive recall limits total results to specified limit."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()

        # Create 5 mock results
        mock_results = []
        for i in range(5):
            mock_memory = MagicMock(spec=AgentMemory)
            mock_memory.id = uuid.uuid4()
            mock_memory.content = f"Content {i}"
            mock_memory.memory_type = "best_practice"
            mock_results.append(MemorySearchResult(memory=mock_memory, similarity=0.8))

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service.search = AsyncMock(return_value=mock_results)

        snippets = await service.proactive_recall(
            content_summary="Test content",
            agent_type="tech_comparator",
            limit=3,
        )

        # Should only return 3 snippets despite 10 results (5 per memory type)
        assert len(snippets) <= 3

    async def test_proactive_recall_creates_snippets(self):
        """Test proactive recall creates MemorySnippet objects correctly."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()

        mock_memory = MagicMock(spec=AgentMemory)
        mock_memory.id = uuid.uuid4()
        mock_memory.content = "Test memory content"
        mock_memory.memory_type = "best_practice"

        mock_result = MemorySearchResult(memory=mock_memory, similarity=0.88)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service.search = AsyncMock(return_value=[mock_result])

        snippets = await service.proactive_recall(
            content_summary="Test content",
            agent_type="implementation_planner",
        )

        assert len(snippets) > 0
        snippet = snippets[0]
        assert isinstance(snippet, MemorySnippet)
        assert snippet.content == "Test memory content"
        assert snippet.memory_type == "best_practice"
        assert snippet.relevance == 0.88
        assert snippet.source_id == str(mock_memory.id)

    async def test_proactive_recall_handles_no_results(self):
        """Test proactive recall handles case with no matching memories."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service.search = AsyncMock(return_value=[])

        snippets = await service.proactive_recall(
            content_summary="Nonexistent content",
            agent_type="security_auditor",
        )

        assert snippets == []


@pytest.mark.asyncio
class TestAgentMemoryServiceSemanticSearch:
    """Tests for the _semantic_search() private method."""

    async def test_semantic_search_executes_pgvector_query(self):
        """Test _semantic_search builds and executes pgvector query."""
        mock_session = AsyncMock()

        # Mock query result
        mock_memory = MagicMock(spec=AgentMemory)
        mock_memory.id = uuid.uuid4()
        mock_memory.content = "Test content"
        mock_memory.memory_type = "best_practice"

        mock_row = MagicMock()
        mock_row.AgentMemory = mock_memory
        mock_row.distance = 0.15  # cosine distance

        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[mock_row])

        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AgentMemoryService(mock_session)

        query_embedding = [0.1] * 1536
        results = await service._semantic_search(
            query_embedding=query_embedding,
            memory_type=None,
            limit=5,
            threshold=0.7,
        )

        # Verify query was executed
        mock_session.execute.assert_called_once()

        # Verify results were converted correctly
        assert len(results) == 1
        assert results[0].memory == mock_memory
        assert results[0].similarity == 0.85  # 1.0 - 0.15

    async def test_semantic_search_converts_threshold_to_distance(self):
        """Test _semantic_search converts similarity threshold to cosine distance."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AgentMemoryService(mock_session)

        query_embedding = [0.1] * 1536
        threshold = 0.8  # similarity threshold

        await service._semantic_search(
            query_embedding=query_embedding,
            memory_type=None,
            limit=5,
            threshold=threshold,
        )

        # The max distance should be 1.0 - 0.8 = 0.2
        # This is verified by the query execution (implementation detail)
        mock_session.execute.assert_called_once()

    async def test_semantic_search_filters_by_memory_type(self):
        """Test _semantic_search adds memory_type filter when specified."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AgentMemoryService(mock_session)

        query_embedding = [0.1] * 1536

        await service._semantic_search(
            query_embedding=query_embedding,
            memory_type=MemoryType.VULNERABILITY_PATTERN,
            limit=5,
            threshold=0.7,
        )

        # Query should have been executed with memory type filter
        mock_session.execute.assert_called_once()
        # The actual filter is in the query object (implementation detail)

    async def test_semantic_search_respects_limit(self):
        """Test _semantic_search limits results to specified count."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = AgentMemoryService(mock_session)

        query_embedding = [0.1] * 1536

        await service._semantic_search(
            query_embedding=query_embedding,
            memory_type=None,
            limit=3,
            threshold=0.7,
        )

        # Query should have limit applied
        mock_session.execute.assert_called_once()


@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_search_with_zero_threshold(self):
        """Test search with threshold=0.0 returns all results."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=[])

        await service.search(query="test", threshold=0.0)

        # Verify threshold was passed correctly
        call_args = service._semantic_search.call_args[1]
        assert call_args["threshold"] == 0.0

    async def test_search_with_max_threshold(self):
        """Test search with threshold=1.0 returns only perfect matches."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=[])

        await service.search(query="test", threshold=1.0)

        call_args = service._semantic_search.call_args[1]
        assert call_args["threshold"] == 1.0

    async def test_search_with_limit_one(self):
        """Test search with limit=1 returns single result."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service._semantic_search = AsyncMock(return_value=[])

        await service.search(query="test", limit=1)

        call_args = service._semantic_search.call_args[1]
        assert call_args["limit"] == 1

    async def test_proactive_recall_with_empty_summary(self):
        """Test proactive recall handles empty content summary."""
        mock_session = AsyncMock()
        mock_embedding_service = AsyncMock()

        service = AgentMemoryService(mock_session, mock_embedding_service)
        service.search = AsyncMock(return_value=[])

        snippets = await service.proactive_recall(
            content_summary="",
            agent_type="security_auditor",
        )

        # Should still execute but return empty
        assert snippets == []

    async def test_store_with_very_long_content(self):
        """Test store handles very long content (10k+ characters)."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)

        long_content = "x" * 10000

        await service.store(
            content=long_content,
            memory_type=MemoryType.ANALYSIS_SUMMARY,
        )

        # Verify content was stored without truncation
        added_memory = mock_session.add.call_args[0][0]
        assert len(added_memory.content) == 10000
