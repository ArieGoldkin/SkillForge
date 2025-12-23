"""Integration tests for WorkflowResultValidator with real Pydantic validation."""

import pytest

from app.domains.analysis.schemas.workflow_result import WorkflowResult
from app.domains.analysis.services.workflow.validator import WorkflowResultValidator


@pytest.fixture
def validator():
    """Create validator instance for tests."""
    return WorkflowResultValidator()


@pytest.mark.integration
def test_validator_real_workflow_result(validator):
    """Test real workflow result validation."""
    # Simulate real workflow result from LangGraph
    real_result = {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "This is a comprehensive article about React hooks...",
            "size_bytes": 5000,
            "content_type": "text/markdown",
            "available_sections": ["introduction", "body", "conclusion"],
        },
        "raw_content": "Full extracted content from the article...",
        "extraction_metadata": {
            "title": "React Hooks: A Complete Guide",
            "word_count": 2500,
            "char_count": 15000,
            "language": "en",
            "author": "John Doe",
        },
        "content_embedding": [0.123] * 1536,
        "artifact_id": "artifact-123",
        "workflow_status": "completed",
    }

    validated, errors = validator.validate(real_result, "completed")
    assert validated is not None
    assert isinstance(validated, WorkflowResult)
    assert errors == []
    assert validated.artifact_id == "artifact-123"


@pytest.mark.integration
def test_validator_with_pydantic_models(validator):
    """Test direct Pydantic model validation."""
    # Create Pydantic model directly
    from app.domains.analysis.schemas.workflow_result import ContentRef, ExtractionMetadata

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
    workflow_result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    # Convert to dict and validate
    result_dict = workflow_result.model_dump()
    validated, errors = validator.validate(result_dict, "completed")
    assert validated is not None
    assert errors == []


@pytest.mark.integration
def test_validator_error_logging(validator, caplog):
    """Test errors properly logged."""
    invalid_result = {
        "raw_content": "",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 100,
    }

    validated, _errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert len(_errors) > 0

    # Check that errors are logged (if logging is enabled)
    # Note: Actual logging happens in orchestrator, not validator


@pytest.mark.integration
def test_validator_performance_real_data(validator):
    """Test performance with real data."""
    import time

    real_result = {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "Test content " * 100,  # Larger content
        "extraction_metadata": {
            "title": "Test Article",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }

    # Measure validation time
    start = time.time()
    validated, _errors = validator.validate(real_result, "completed")
    elapsed = time.time() - start

    assert validated is not None
    # Should be fast (<10ms for real data)
    assert elapsed < 0.01, f"Validation took {elapsed * 1000:.2f}ms, expected <10ms"


@pytest.mark.integration
def test_validator_edge_cases_real_data(validator):
    """Test edge cases with real workflow results."""
    # Test with very long content
    long_content_result = {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 100000,
            "content_type": "text/plain",
        },
        "raw_content": "x" * 10000,  # Very long content
        "extraction_metadata": {
            "title": "Test Article",
            "word_count": 10000,
            "char_count": 100000,
        },
        "content_embedding": [0.1] * 1536,
    }

    validated, _errors = validator.validate(long_content_result, "completed")
    assert validated is not None
    assert len(validated.raw_content) == 10000


@pytest.mark.integration
def test_validator_real_validation_errors(validator):
    """Test real Pydantic validation errors."""
    # Create invalid data that will trigger ValidationError
    invalid_result = {
        "content_ref": {
            "uri": "invalid://uri",  # Invalid URI
            "summary": "",  # Empty summary
            "size_bytes": -1,  # Negative
            "content_type": "text/plain",
        },
        "raw_content": "",  # Empty content
        "extraction_metadata": {
            "title": "",  # Empty title
            "word_count": -1,  # Negative
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 100,  # Wrong dimensions
    }

    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    # Should have multiple errors
    assert len(errors) >= 3
    # Errors should be formatted strings
    assert all(isinstance(error, str) for error in errors)


@pytest.mark.integration
def test_validator_error_logging_context(validator):
    """Test errors logged with context."""
    invalid_result = {
        "raw_content": "",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }

    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    # Error messages should contain field information
    error_text = " ".join(errors)
    assert "raw_content" in error_text.lower()


@pytest.mark.integration
def test_validator_error_serialization(validator):
    """Test errors can be serialized."""
    invalid_result = {
        "raw_content": "",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 100,
    }

    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None

    # Errors should be JSON-serializable
    import json

    json_str = json.dumps(errors)
    assert isinstance(json_str, str)

    # Should be able to deserialize
    deserialized = json.loads(json_str)
    assert isinstance(deserialized, list)
    assert len(deserialized) == len(errors)
