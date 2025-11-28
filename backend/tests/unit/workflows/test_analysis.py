"""Unit tests for analysis workflow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.extraction.jina_reader import JinaReaderError
from app.workflows.analysis import analysis_workflow
from app.workflows.state import AnalysisState

# Expected embedding dimensions for OpenAI text-embedding-3-small
EXPECTED_EMBEDDING_DIMENSIONS = 1536


@pytest.fixture
def sample_extraction_result() -> dict:
    """Sample extraction result from JinaReader."""
    return {
        "content": "# Test Article\n\nThis is test content.",
        "metadata": {
            "extractor": "jina_reader",
            "source_url": "https://example.com",
            "word_count": 5,
        },
        "word_count": 5,
    }


@pytest.fixture
def sample_embedding() -> list[float]:
    """Sample embedding vector."""
    return [0.1] * EXPECTED_EMBEDDING_DIMENSIONS


@pytest.mark.asyncio
async def test_analysis_workflow_with_mocked_services(
    sample_extraction_result: dict,
    sample_embedding: list[float],
) -> None:
    """Test analysis_workflow with mocked JinaReader and EmbeddingService."""
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(return_value=sample_extraction_result)
    mock_jina.close = AsyncMock()

    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(return_value=sample_embedding)
    mock_embedding_service.close = AsyncMock()

    # Mock supervisor to return empty agent selection (no agents to execute)
    mock_supervisor_result = {
        "supervisor_decision": {
            "agents": [],
            "priority": [],
            "reasoning": "Test content",
            "confidence": 0.5,
        }
    }

    with (
        patch("app.workflows.tasks.extract_content.JinaReader", return_value=mock_jina),
        patch(
            "app.workflows.tasks.generate_embedding.EmbeddingService",
            return_value=mock_embedding_service,
        ),
        patch(
            "app.workflows.graph_builder.supervisor_route",
            new_callable=AsyncMock,
            return_value=mock_supervisor_result,
        ),
        patch(
            "app.workflows.nodes.parallel_agents.execute_agents",
            new_callable=AsyncMock,
            return_value=[],  # No agent findings since no agents selected
        ),
    ):
        result = await analysis_workflow.ainvoke(
            {
                "url": "https://example.com",
                "analysis_id": "test-analysis-id",
            },
            config={"configurable": {"thread_id": "test-thread"}},
        )

        # Verify result structure
        assert "analysis_id" in result
        assert "url" in result
        assert "raw_content" in result
        assert "extraction_metadata" in result
        assert "content_embedding" in result
        assert "supervisor_decision" in result
        assert "agent_findings" in result

        # Verify values
        assert result["analysis_id"] == "test-analysis-id"
        assert result["url"] == "https://example.com"
        assert result["raw_content"] == sample_extraction_result["content"]
        assert result["extraction_metadata"] == sample_extraction_result["metadata"]
        assert result["content_embedding"] == sample_embedding
        assert result["agent_findings"] == []

        # Verify services were called
        mock_jina.extract_article.assert_called_once_with("https://example.com")
        mock_jina.close.assert_called_once()
        mock_embedding_service.generate_embedding.assert_called_once()


@pytest.mark.asyncio
async def test_analysis_workflow_error_handling() -> None:
    """Test analysis_workflow handles extraction errors gracefully."""
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        side_effect=JinaReaderError("Extraction failed"),
    )
    mock_jina.close = AsyncMock()

    with (
        patch("app.workflows.tasks.extract_content.JinaReader", return_value=mock_jina),
        pytest.raises(JinaReaderError, match="Extraction failed"),
    ):
        await analysis_workflow.ainvoke(
            {
                "url": "https://example.com",
                "analysis_id": "test-analysis-id",
            },
            config={"configurable": {"thread_id": "test-thread"}},
        )


@pytest.mark.asyncio
async def test_analysis_state_structure() -> None:
    """Test AnalysisState TypedDict structure."""
    state: AnalysisState = {
        "analysis_id": "test-id",
        "url": "https://example.com",
        "content_type": "article",
        "raw_content": "Test content",
        "extraction_metadata": {"key": "value"},
        "content_embedding": [0.1] * EXPECTED_EMBEDDING_DIMENSIONS,
    }

    assert state["analysis_id"] == "test-id"
    assert state["url"] == "https://example.com"
    assert state["content_type"] == "article"
    assert state["raw_content"] == "Test content"
    assert len(state["content_embedding"]) == EXPECTED_EMBEDDING_DIMENSIONS
