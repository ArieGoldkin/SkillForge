"""Unit tests for AgentMemoryService.

Issue #245: Agent Memory Access (RAG)
Tests the core memory service functionality including store, search, and proactive recall.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent_memory import MemoryType
from app.shared.services.memory import (

    AgentMemoryService,
    MemorySearchResult,
    MemorySnippet,
)


class TestMemorySnippet:
    """Tests for MemorySnippet dataclass."""

    def test_to_context_string_format(self):
        """Test MemorySnippet formats correctly for context injection."""
        snippet = MemorySnippet(
            content="SQL injection vulnerability pattern",
            memory_type="vulnerability_pattern",
            relevance=0.85,
            source_id=str(uuid.uuid4()),
        )

        result = snippet.to_context_string()

        assert "[vulnerability_pattern]" in result
        assert "(relevance: 0.85)" in result
        assert "SQL injection vulnerability pattern" in result

    def test_to_context_string_preserves_content(self):
        """Test that full content is preserved in context string."""
        content = "Long content with multiple sentences about best practices."
        snippet = MemorySnippet(
            content=content,
            memory_type="best_practice",
            relevance=0.72,
            source_id=str(uuid.uuid4()),
        )

        result = snippet.to_context_string()

        assert content in result


class TestMemorySearchResult:
    """Tests for MemorySearchResult dataclass."""

    def test_to_dict_serialization(self):
        """Test MemorySearchResult serializes to dict correctly."""
        mock_memory = MagicMock()
        mock_memory.id = uuid.uuid4()
        mock_memory.memory_type = "analysis_summary"
        mock_memory.content = "Test analysis content"
        mock_memory.memory_metadata = {"language": "python"}

        result = MemorySearchResult(
            memory=mock_memory,
            similarity=0.92,
        )

        serialized = result.to_dict()

        assert serialized["id"] == str(mock_memory.id)
        assert serialized["type"] == "analysis_summary"
        assert serialized["content"] == "Test analysis content"
        assert serialized["similarity"] == 0.92
        assert serialized["metadata"] == {"language": "python"}

    def test_to_dict_rounds_similarity(self):
        """Test similarity is rounded to 3 decimal places."""
        mock_memory = MagicMock()
        mock_memory.id = uuid.uuid4()
        mock_memory.memory_type = "agent_finding"
        mock_memory.content = "Finding"
        mock_memory.memory_metadata = None

        result = MemorySearchResult(
            memory=mock_memory,
            similarity=0.123456789,
        )

        serialized = result.to_dict()
        assert serialized["similarity"] == 0.123

    def test_to_dict_handles_none_metadata(self):
        """Test that None metadata becomes empty dict."""
        mock_memory = MagicMock()
        mock_memory.id = uuid.uuid4()
        mock_memory.memory_type = "best_practice"
        mock_memory.content = "Practice"
        mock_memory.memory_metadata = None

        result = MemorySearchResult(memory=mock_memory, similarity=0.8)
        serialized = result.to_dict()

        assert serialized["metadata"] == {}


class TestAgentMemoryServiceInit:
    """Tests for AgentMemoryService initialization."""

    def test_init_with_session_only(self):
        """Test service initializes with just session."""
        mock_session = MagicMock()
        service = AgentMemoryService(mock_session)

        assert service.session == mock_session
        assert service._embedding_service is None

    def test_init_with_embedding_service(self):
        """Test service initializes with provided embedding service."""
        mock_session = MagicMock()
        mock_embedding = MagicMock()

        service = AgentMemoryService(mock_session, mock_embedding)

        assert service.session == mock_session
        assert service._embedding_service == mock_embedding

    @patch("app.services.memory.agent_memory_service.EmbeddingService")
    def test_lazy_load_embedding_service(self, mock_embedding_class):
        """Test embedding service is lazy loaded on first access."""
        mock_session = MagicMock()
        mock_embedding_instance = MagicMock()
        mock_embedding_class.return_value = mock_embedding_instance

        service = AgentMemoryService(mock_session)

        # Should not have created embedding service yet
        assert service._embedding_service is None

        # Access the property
        result = service.embedding_service

        # Now it should be created
        assert result == mock_embedding_instance
        mock_embedding_class.assert_called_once()


class TestAgentMemoryServiceGetRelevantTypes:
    """Tests for memory type mapping logic."""

    def test_security_auditor_types(self):
        """Test security_auditor gets correct memory types."""
        service = AgentMemoryService(MagicMock())

        types = service._get_relevant_memory_types("security_auditor")

        assert MemoryType.VULNERABILITY_PATTERN in types
        assert MemoryType.BEST_PRACTICE in types

    def test_tech_comparator_types(self):
        """Test tech_comparator gets correct memory types."""
        service = AgentMemoryService(MagicMock())

        types = service._get_relevant_memory_types("tech_comparator")

        assert MemoryType.ANALYSIS_SUMMARY in types
        assert MemoryType.BEST_PRACTICE in types

    def test_implementation_planner_types(self):
        """Test implementation_planner gets correct memory types."""
        service = AgentMemoryService(MagicMock())

        types = service._get_relevant_memory_types("implementation_planner")

        assert MemoryType.BEST_PRACTICE in types
        assert MemoryType.ANALYSIS_SUMMARY in types

    def test_unknown_agent_gets_default_types(self):
        """Test unknown agent type gets default memory types."""
        service = AgentMemoryService(MagicMock())

        types = service._get_relevant_memory_types("unknown_agent")

        assert MemoryType.ANALYSIS_SUMMARY in types
        assert MemoryType.BEST_PRACTICE in types


@pytest.mark.asyncio
class TestAgentMemoryServiceStore:
    """Tests for memory storage functionality."""

    async def test_store_creates_memory_with_embedding(self):
        """Test store() creates memory with generated embedding."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)

        content = "Test vulnerability pattern"
        memory_type = MemoryType.VULNERABILITY_PATTERN

        result = await service.store(
            content=content,
            memory_type=memory_type,
            agent_type="security_auditor",
        )

        # Verify embedding was generated
        mock_embedding_service.generate_embedding.assert_called_once_with(content)

        # Verify memory was added to session
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        mock_session.refresh.assert_awaited_once()

        # Verify memory attributes
        added_memory = mock_session.add.call_args[0][0]
        assert added_memory.content == content
        assert added_memory.memory_type == memory_type.value
        assert added_memory.agent_type == "security_auditor"
        assert added_memory.embedding == [0.1] * 1536

    async def test_store_with_analysis_id(self):
        """Test store() links memory to analysis."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)

        analysis_id = uuid.uuid4()

        await service.store(
            content="Test content",
            memory_type=MemoryType.ANALYSIS_SUMMARY,
            analysis_id=analysis_id,
        )

        added_memory = mock_session.add.call_args[0][0]
        assert added_memory.analysis_id == analysis_id

    async def test_store_with_metadata(self):
        """Test store() includes metadata."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)

        metadata = {"language": "python", "framework": "fastapi"}

        await service.store(
            content="Test content",
            memory_type=MemoryType.BEST_PRACTICE,
            metadata=metadata,
        )

        added_memory = mock_session.add.call_args[0][0]
        assert added_memory.memory_metadata == metadata


@pytest.mark.asyncio
class TestAgentMemoryServiceStoreAgentFinding:
    """Tests for store_agent_finding convenience method."""

    async def test_store_agent_finding_uses_correct_type(self):
        """Test store_agent_finding uses AGENT_FINDING type."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()

        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        service = AgentMemoryService(mock_session, mock_embedding_service)

        analysis_id = uuid.uuid4()

        await service.store_agent_finding(
            analysis_id=analysis_id,
            agent_type="security_auditor",
            finding="Critical XSS vulnerability found",
            metadata={"severity": "high"},
        )

        added_memory = mock_session.add.call_args[0][0]
        assert added_memory.memory_type == MemoryType.AGENT_FINDING.value
        assert added_memory.agent_type == "security_auditor"
        assert added_memory.analysis_id == analysis_id
