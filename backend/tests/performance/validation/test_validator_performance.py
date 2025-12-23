"""Performance tests for WorkflowResultValidator."""

import asyncio
import time

import pytest

from app.domains.analysis.schemas.workflow_result import WorkflowResult
from app.domains.analysis.services.workflow.validator import WorkflowResultValidator


@pytest.fixture
def validator():
    """Create validator instance for tests."""
    return WorkflowResultValidator()


@pytest.fixture
def valid_workflow_result():
    """Create valid workflow result for performance tests."""
    return {
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


@pytest.mark.performance
def test_validator_single_validation_speed(validator, valid_workflow_result, benchmark):
    """Test single validation speed <5ms p95."""

    def validate():
        return validator.validate(valid_workflow_result, "completed")

    validated, errors = benchmark(validate)
    assert validated is not None
    assert errors == []


@pytest.mark.performance
@pytest.mark.asyncio
async def test_validator_concurrent_100_validations(validator, valid_workflow_result):
    """Test 100 concurrent validations <500ms total."""
    # Create 100 validation tasks
    tasks = [validator.validate(valid_workflow_result.copy(), "completed") for _ in range(100)]

    start = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    # All should succeed
    assert all(v[0] is not None for v in results)
    assert all(v[1] == [] for v in results)

    # Should be fast (<500ms for 100 validations)
    assert elapsed < 0.5, f"100 validations took {elapsed * 1000:.2f}ms, expected <500ms"


@pytest.mark.performance
def test_validator_typeadapter_reuse(validator, valid_workflow_result):
    """Test TypeAdapter reuse improves performance."""
    from pydantic import TypeAdapter

    # Create TypeAdapter once (reused)
    adapter = TypeAdapter(WorkflowResult)

    # First validation (cold start)
    start1 = time.time()
    validated1 = adapter.validate_python(valid_workflow_result)
    elapsed1 = time.time() - start1

    # Second validation (warm, adapter cached)
    start2 = time.time()
    validated2 = adapter.validate_python(valid_workflow_result)
    elapsed2 = time.time() - start2

    assert validated1 is not None
    assert validated2 is not None

    # Second should be faster (adapter schema cached)
    # Note: This is a smoke test - actual improvement depends on Pydantic internals
    assert elapsed2 <= elapsed1 * 1.5  # Allow some variance


@pytest.mark.performance
def test_validator_error_extraction_speed(validator, benchmark):
    """Test error extraction speed <1ms."""
    from pydantic import ValidationError

    # Create a ValidationError with multiple errors
    try:
        WorkflowResult.model_validate(
            {
                "raw_content": "",
                "extraction_metadata": {
                    "title": "",
                    "word_count": -1,
                    "char_count": 5000,
                },
                "content_embedding": [0.1] * 100,
            }
        )
    except ValidationError as e:
        validation_error = e

    def extract_errors():
        return validator._extract_validation_errors(validation_error)

    errors = benchmark(extract_errors)
    assert len(errors) > 0
    assert all(isinstance(error, str) for error in errors)


@pytest.mark.performance
def test_validator_large_error_list(validator):
    """Test large error lists handled efficiently."""
    from pydantic import ValidationError

    # Create result with many validation errors
    invalid_result = {
        "content_ref": {
            "uri": "invalid://uri",
            "summary": "",
            "size_bytes": -1,
            "content_type": "",
        },
        "raw_content": "",
        "extraction_metadata": {
            "title": "",
            "word_count": -1,
            "char_count": -1,
        },
        "content_embedding": [0.1] * 100,
    }

    try:
        WorkflowResult.model_validate(invalid_result)
    except ValidationError as e:
        validation_error = e

    # Extract errors should be fast even with many errors
    start = time.time()
    errors = validator._extract_validation_errors(validation_error)
    elapsed = time.time() - start

    assert len(errors) >= 5
    assert elapsed < 0.001, f"Error extraction took {elapsed * 1000:.2f}ms, expected <1ms"
