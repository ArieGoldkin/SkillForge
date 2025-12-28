"""Unit tests for graph builder."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domains.analysis.workflows.graph_builder import build_analysis_graph
from app.domains.analysis.workflows.nodes.agent_router import route_to_agents
from app.domains.analysis.workflows.state import AnalysisState

# Expected embedding dimensions for OpenAI text-embedding-3-small
EXPECTED_EMBEDDING_DIMENSIONS = 1536

# Test UUID for analysis_id (must be valid UUID for artifact generation)
TEST_ANALYSIS_ID = str(uuid4())


@pytest.fixture
def sample_state() -> AnalysisState:
    """Sample initial state for testing."""
    return {
        "analysis_id": TEST_ANALYSIS_ID,
        "url": "https://example.com",
    }


@pytest.fixture
def sample_extraction_result() -> dict:
    """Sample extraction result."""
    return {
        "raw_content": "Test content",
        "extraction_metadata": {
            "content_type": "article",
            "word_count": 10,
        },
    }


@pytest.fixture
def sample_embedding() -> list[float]:
    """Sample embedding vector."""
    return [0.1] * EXPECTED_EMBEDDING_DIMENSIONS


@pytest.fixture
def sample_supervisor_result() -> dict:
    """Sample supervisor result."""
    return {
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "Test",
            "confidence": 0.5,
        }
    }


@pytest.mark.asyncio
async def test_graph_builder_creates_graph(sample_state: AnalysisState) -> None:
    """Test that build_analysis_graph creates a valid graph."""
    graph = build_analysis_graph()

    # Verify graph is compiled (has ainvoke method)
    assert hasattr(graph, "ainvoke")
    assert callable(graph.ainvoke)


@pytest.mark.asyncio
@pytest.mark.slow  # Issue #588: Test requires external services (Langfuse, Redis) not properly mocked
async def test_graph_execution_with_mocks(
    sample_state: AnalysisState,
    sample_extraction_result: dict,
    sample_embedding: list[float],
    sample_supervisor_result: dict,
) -> None:
    """Test graph execution with mocked services."""
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        return_value={
            "content": sample_extraction_result["raw_content"],
            "metadata": sample_extraction_result["extraction_metadata"],
        }
    )
    mock_jina.close = AsyncMock()

    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=sample_embedding)
    mock_embedding_service.close = AsyncMock()

    # Mock artifact repository to avoid database foreign key violations
    from uuid import UUID

    mock_artifact = MagicMock()
    mock_artifact.id = UUID(TEST_ANALYSIS_ID)
    mock_artifact_repo = AsyncMock()
    mock_artifact_repo.create_artifact = AsyncMock(return_value=mock_artifact)

    class _DummySession:
        async def commit(self): ...

        async def rollback(self): ...

        def add_all(self, items): ...

        async def flush(self): ...

    class _DummySessionContext:
        def __init__(self) -> None:
            self.session = _DummySession()

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def _dummy_session_factory():
        return _DummySessionContext()

    # Mock _create_artifact_ref to avoid database calls (Issue #244 Handle Pattern)
    mock_content_ref = {
        "uri": f"analysis://{TEST_ANALYSIS_ID}/content",
        "summary": "Test content summary",
        "size_bytes": len(sample_extraction_result["raw_content"]),
        "content_type": "text/markdown",
        "available_sections": ["full", "summary"],
    }

    with (
        patch(
            "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
            return_value=mock_jina,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.extract_content._create_artifact_ref",
            new_callable=AsyncMock,
            return_value=mock_content_ref,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_embedding.EmbeddingService",
            return_value=mock_embedding_service,
        ),
        patch(
            "app.domains.analysis.workflows.graph_builder.supervisor_route",
            new_callable=AsyncMock,
            return_value=sample_supervisor_result,
        ),
        patch(
            "app.domains.analysis.workflows.nodes.agent_router.route_to_agents",
            return_value=[],  # No agents selected
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_artifact.ArtifactRepository",
            return_value=mock_artifact_repo,
        ),
        patch(
            "app.domains.analysis.workflows.graph_builder.get_session_factory",
            return_value=_dummy_session_factory,
        ),
        patch(
            "app.shared.services.persistence.progress.persist_progress_event_async",
            return_value=None,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.store_embeddings.store_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        # Issue #588: Use backward compatibility mode (parallel routing) for existing tests
        # New tiered routing is the default, but these tests expect parallel behavior
        graph = build_analysis_graph(route_to_agents_fn=route_to_agents)
        result = await graph.ainvoke(
            sample_state,
            config={"configurable": {"thread_id": "test-thread"}},
        )

        # Verify state transitions
        assert result["raw_content"] == sample_extraction_result["raw_content"]
        assert result["content_embedding"] == sample_embedding
        assert result["supervisor_decision"] == sample_supervisor_result["supervisor_decision"]
        assert result["agent_findings"] == []


@pytest.mark.asyncio
async def test_graph_handles_extraction_error(sample_state: AnalysisState) -> None:
    """Test graph handles extraction errors gracefully with abort signal."""
    from app.core.exceptions import ExtractionErrorCode
    from app.shared.services.extraction.jina_reader import JinaReaderError

    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        side_effect=JinaReaderError("Extraction failed", error_code=ExtractionErrorCode.UNKNOWN)
    )
    mock_jina.close = AsyncMock()

    with patch(
        "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
        return_value=mock_jina,
    ):
        graph = build_analysis_graph()
        result = await graph.ainvoke(
            sample_state,
            config={"configurable": {"thread_id": "test-thread"}},
        )

    # Issue #441: Extraction errors now set abort signals instead of raising
    assert result.get("should_abort") is True
    assert result.get("extraction_status") == "failed"
    assert "Extraction failed" in result.get("abort_reason", "")
    # Verify workflow terminated at workflow_failed node
    # The workflow_status and final_error fields are set by workflow_failed node
    assert result.get("workflow_status") == "failed", (
        f"Expected 'failed', got {result.get('workflow_status')}. Keys: {list(result.keys())}"
    )
    assert result.get("final_error") == "Extraction failed"


@pytest.mark.asyncio
@pytest.mark.slow  # Issue #588: Test requires external services (Langfuse, Redis) not properly mocked
async def test_graph_state_structure(sample_state: AnalysisState) -> None:
    """Test that graph maintains proper state structure."""
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        return_value={
            "content": "Test",
            "metadata": {"content_type": "article"},
        }
    )
    mock_jina.close = AsyncMock()

    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(
        return_value=[0.1] * EXPECTED_EMBEDDING_DIMENSIONS
    )
    mock_embedding_service.close = AsyncMock()

    mock_supervisor_result = {
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "Test",
            "confidence": 0.5,
        }
    }

    # Mock artifact repository to avoid database foreign key violations
    from uuid import UUID

    mock_artifact = MagicMock()
    mock_artifact.id = UUID(TEST_ANALYSIS_ID)
    mock_artifact_repo = AsyncMock()
    mock_artifact_repo.create_artifact = AsyncMock(return_value=mock_artifact)

    class _DummySession:
        async def commit(self): ...

        async def rollback(self): ...

        def add_all(self, items): ...

        async def flush(self): ...

    class _DummySessionContext:
        def __init__(self) -> None:
            self.session = _DummySession()

        async def __aenter__(self):
            return self.session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def _dummy_session_factory():
        return _DummySessionContext()

    # Mock _create_artifact_ref to avoid database calls (Issue #244 Handle Pattern)
    mock_content_ref = {
        "uri": f"analysis://{TEST_ANALYSIS_ID}/content",
        "summary": "Test summary",
        "size_bytes": 4,
        "content_type": "text/markdown",
        "available_sections": ["full", "summary"],
    }

    with (
        patch(
            "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
            return_value=mock_jina,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.extract_content._create_artifact_ref",
            new_callable=AsyncMock,
            return_value=mock_content_ref,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_embedding.EmbeddingService",
            return_value=mock_embedding_service,
        ),
        patch(
            "app.domains.analysis.workflows.graph_builder.supervisor_route",
            new_callable=AsyncMock,
            return_value=mock_supervisor_result,
        ),
        patch(
            "app.domains.analysis.workflows.nodes.agent_router.route_to_agents",
            return_value=[],  # No agents selected
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_artifact.ArtifactRepository",
            return_value=mock_artifact_repo,
        ),
        patch(
            "app.domains.analysis.workflows.graph_builder.get_session_factory",
            return_value=_dummy_session_factory,
        ),
        patch(
            "app.shared.services.persistence.progress.persist_progress_event_async",
            return_value=None,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.store_embeddings.store_embeddings",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        # Issue #588: Use backward compatibility mode (parallel routing) for existing tests
        # New tiered routing is the default, but these tests expect parallel behavior
        graph = build_analysis_graph(route_to_agents_fn=route_to_agents)
        result = await graph.ainvoke(
            sample_state,
            config={"configurable": {"thread_id": "test-thread"}},
        )

        # Verify all required state fields are present
        required_fields = [
            "analysis_id",
            "url",
            "content_type",
            "raw_content",
            "extraction_metadata",
            "content_embedding",
            "supervisor_decision",
            "agent_findings",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"
