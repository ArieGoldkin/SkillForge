"""Unit tests for type aliases."""

from app.core.types import (
import pytest

@pytest.mark.unit
    AnalysisID,
    ChannelName,
    EmbeddingVector,
    EventData,
    ExtractionResult,
)


def test_embedding_vector_type() -> None:
    """Test EmbeddingVector type alias."""
    vector: EmbeddingVector = [0.1, 0.2, 0.3]
    assert isinstance(vector, list)
    assert all(isinstance(x, float) for x in vector)


def test_analysis_id_type() -> None:
    """Test AnalysisID type alias."""
    analysis_id: AnalysisID = "123e4567-e89b-12d3-a456-426614174000"
    assert isinstance(analysis_id, str)
    assert len(analysis_id) > 0


def test_channel_name_type() -> None:
    """Test ChannelName type alias."""
    channel: ChannelName = "workflow:123e4567-e89b-12d3-a456-426614174000"
    assert isinstance(channel, str)
    assert channel.startswith("workflow:")


def test_event_data_type() -> None:
    """Test EventData type alias."""
    event: EventData = {
        "type": "progress",
        "stage": "extraction",
        "status": "running",
        "analysis_id": "123",
    }
    assert isinstance(event, dict)
    assert "type" in event


def test_extraction_result_type() -> None:
    """Test ExtractionResult type alias."""
    result: ExtractionResult = {
        "title": "Test Article",
        "content": "Article content",
        "word_count": 100,
        "metadata": {"extractor": "jina_reader", "source_url": "https://example.com"},
    }
    assert isinstance(result, dict)
    assert "title" in result
    assert "content" in result
    assert "word_count" in result
    assert "metadata" in result
    assert isinstance(result["word_count"], int)
    assert isinstance(result["metadata"], dict)
