"""Integration tests for workflow result Pydantic schemas."""

import pytest

from app.domains.analysis.schemas.workflow_result import (
    ContentRef,
    ExtractionMetadata,
    WorkflowResult,
)


@pytest.mark.integration
def test_extraction_metadata_from_workflow_result():
    """Test real workflow result parsing with ExtractionMetadata."""
    # Simulate real workflow result data
    workflow_data = {
        "title": "React Hooks Tutorial",
        "word_count": 1500,
        "char_count": 8000,
        "language": "en",
        "author": "John Doe",
    }
    metadata = ExtractionMetadata.model_validate(workflow_data)
    assert metadata.title == "React Hooks Tutorial"
    assert metadata.word_count == 1500


@pytest.mark.integration
def test_extraction_metadata_serialization():
    """Test model_dump() and model_validate_json()."""
    metadata = ExtractionMetadata(
        title="Test Article",
        word_count=1000,
        char_count=5000,
    )
    # Test serialization
    dumped = metadata.model_dump()
    assert isinstance(dumped, dict)
    assert dumped["title"] == "Test Article"

    # Test JSON serialization
    json_str = metadata.model_dump_json()
    assert isinstance(json_str, str)

    # Test deserialization
    loaded = ExtractionMetadata.model_validate_json(json_str)
    assert loaded.title == metadata.title


@pytest.mark.integration
def test_content_ref_from_artifact_store():
    """Test ContentRef integration with artifact store pattern."""
    # Simulate artifact store URI format
    analysis_id = "12345678-1234-1234-1234-123456789abc"
    uri = f"analysis://{analysis_id}/content"

    content_ref = ContentRef(
        uri=uri,
        summary="This is a test summary of the content",
        size_bytes=5000,
        content_type="text/markdown",
        available_sections=["introduction", "body", "conclusion"],
    )

    assert content_ref.uri == uri
    assert len(content_ref.available_sections) == 3


@pytest.mark.integration
def test_content_ref_serialization():
    """Test JSON serialization/deserialization."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )

    # Test JSON roundtrip
    json_str = content_ref.model_dump_json()
    loaded = ContentRef.model_validate_json(json_str)
    assert loaded.uri == content_ref.uri
    assert loaded.summary == content_ref.summary


@pytest.mark.integration
def test_workflow_result_from_real_workflow():
    """Test real workflow result parsing."""
    # Simulate complete workflow result
    workflow_result_data = {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "This is the extracted content from the article...",
        "extraction_metadata": {
            "title": "Test Article",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
        "workflow_status": "completed",
    }

    result = WorkflowResult.model_validate(workflow_result_data)
    assert result.workflow_status == "completed"
    assert result.content_ref is not None
    assert len(result.content_embedding) == 1536


@pytest.mark.integration
def test_workflow_result_serialization_roundtrip():
    """Test serialize/deserialize roundtrip."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test Article",
        word_count=1000,
        char_count=5000,
    )
    result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    # Serialize to dict
    dumped = result.model_dump()
    assert isinstance(dumped, dict)

    # Deserialize from dict
    loaded = WorkflowResult.model_validate(dumped)
    assert loaded.raw_content == result.raw_content
    assert loaded.content_ref.uri == result.content_ref.uri


@pytest.mark.integration
def test_workflow_result_with_artifact_store():
    """Test integration with artifact store pattern."""
    # Simulate artifact store content reference
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Content summary for artifact store",
        size_bytes=5000,
        content_type="text/markdown",
    )

    metadata = ExtractionMetadata(
        title="Article Title",
        word_count=2000,
        char_count=10000,
    )

    result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Full content stored in artifact store...",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
        artifact_id="artifact-123",
    )

    # Verify artifact_id is set
    assert result.artifact_id == "artifact-123"
    # Verify content_ref URI can be parsed
    uri_parts = result.content_ref.uri.split("/")
    assert len(uri_parts) == 4
    assert uri_parts[0] == "analysis:"
    assert uri_parts[3] == "content"
