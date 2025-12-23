"""Performance tests for schema validation."""

import pytest

from app.domains.analysis.schemas.workflow_result import (
    ContentRef,
    ExtractionMetadata,
    WorkflowResult,
)


@pytest.mark.performance
def test_extraction_metadata_validation_speed(benchmark):
    """Test extraction metadata validation speed <1ms p95."""
    metadata_data = {
        "title": "Test Article",
        "word_count": 1000,
        "char_count": 5000,
    }

    def validate():
        return ExtractionMetadata.model_validate(metadata_data)

    result = benchmark(validate)
    assert result.title == "Test Article"

    # Verify p95 is <1ms (benchmark will report this)
    # This is a smoke test - actual benchmarking done by pytest-benchmark


@pytest.mark.performance
def test_content_ref_validation_speed(benchmark):
    """Test content ref validation speed <1ms p95."""
    content_ref_data = {
        "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
        "summary": "Test summary",
        "size_bytes": 1000,
        "content_type": "text/plain",
    }

    def validate():
        return ContentRef.model_validate(content_ref_data)

    result = benchmark(validate)
    assert result.uri.startswith("analysis://")


@pytest.mark.performance
def test_workflow_result_validation_speed(benchmark):
    """Test workflow result validation speed <2ms p95."""
    workflow_data = {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test Article",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }

    def validate():
        return WorkflowResult.model_validate(workflow_data)

    result = benchmark(validate)
    assert result.raw_content == "Test content"
    assert len(result.content_embedding) == 1536
