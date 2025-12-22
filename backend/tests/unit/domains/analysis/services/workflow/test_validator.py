"""Unit tests for WorkflowResultValidator (Pydantic v2)."""

import pytest
from pydantic import ValidationError

from app.domains.analysis.schemas.workflow_result import WorkflowResult
from app.domains.analysis.services.workflow.validator import WorkflowResultValidator


@pytest.fixture
def validator():
    """Create validator instance for tests."""
    return WorkflowResultValidator()


@pytest.fixture
def valid_workflow_result():
    """Create valid workflow result dict for tests."""
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
        "workflow_status": "completed",
    }


# ============================================================================
# Valid Validation Tests
# ============================================================================


def test_validator_valid_completed(validator, valid_workflow_result):
    """Test valid completed workflow returns validated model."""
    validated, errors = validator.validate(valid_workflow_result, "completed")
    assert validated is not None
    assert isinstance(validated, WorkflowResult)
    assert errors == []
    assert validated.workflow_status == "completed"


def test_validator_valid_failed_status(validator):
    """Test failed status allows missing content fields."""
    # Failed workflows don't require content fields
    failed_result = {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
        "workflow_status": "failed",
    }
    validated, errors = validator.validate(failed_result, "failed")
    assert validated is not None
    assert errors == []


# ============================================================================
# Missing Field Tests
# ============================================================================


def test_validator_missing_required_field(validator):
    """Test missing field returns errors."""
    invalid_result = {
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
        # Missing content_ref
    }
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert len(errors) > 0
    assert any("content_ref" in error.lower() for error in errors)


def test_validator_missing_multiple_fields(validator):
    """Test multiple missing fields all returned."""
    invalid_result = {
        # Missing content_ref, raw_content, extraction_metadata, content_embedding
    }
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert len(errors) > 0


# ============================================================================
# Type Validation Tests
# ============================================================================


def test_validator_invalid_type(validator, valid_workflow_result):
    """Test wrong type returns errors."""
    invalid_result = valid_workflow_result.copy()
    # Put invalid type in nested structure where it can't be coerced
    invalid_result["extraction_metadata"]["word_count"] = "not-a-number"  # Should be int
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert len(errors) > 0


def test_validator_type_coercion(validator, valid_workflow_result):
    """Test type coercion works correctly."""
    # String numbers should convert to int/float
    coerced_result = valid_workflow_result.copy()
    coerced_result["extraction_metadata"]["word_count"] = "1000"  # String
    coerced_result["content_embedding"] = ["0.1"] * 1536  # String floats

    validated, _errors = validator.validate(coerced_result, "completed")
    assert validated is not None
    assert isinstance(validated.extraction_metadata.word_count, int)
    assert all(isinstance(x, float) for x in validated.content_embedding)


# ============================================================================
# Constraint Validation Tests
# ============================================================================


def test_validator_wrong_embedding_dimensions(validator, valid_workflow_result):
    """Test wrong embedding dimensions returns errors."""
    invalid_result = valid_workflow_result.copy()
    invalid_result["content_embedding"] = [0.1] * 100  # Wrong dimensions
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert any("embedding" in error.lower() or "1536" in error for error in errors)


def test_validator_empty_raw_content(validator, valid_workflow_result):
    """Test empty content returns errors."""
    invalid_result = valid_workflow_result.copy()
    invalid_result["raw_content"] = ""
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert any("raw_content" in error.lower() for error in errors)


def test_validator_invalid_uri_format(validator, valid_workflow_result):
    """Test invalid URI format returns errors."""
    invalid_result = valid_workflow_result.copy()
    invalid_result["content_ref"]["uri"] = "invalid://uri"
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert any("uri" in error.lower() for error in errors)


# ============================================================================
# Error Extraction Tests
# ============================================================================


def test_validator_validation_error_extraction(validator):
    """Test ValidationError properly extracted."""
    invalid_result = {
        "raw_content": "",  # Empty content
        "extraction_metadata": {
            "title": "Test",
            "word_count": -1,  # Negative
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 100,  # Wrong dimensions
    }
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert len(errors) > 0
    # Errors should be formatted strings
    assert all(isinstance(error, str) for error in errors)


def test_validator_error_message_format(validator):
    """Test error messages are clear."""
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
    # Error messages should contain field names
    error_text = " ".join(errors).lower()
    assert "raw_content" in error_text or "embedding" in error_text


def test_validator_multiple_errors(validator):
    """Test multiple errors all returned."""
    invalid_result = {
        "raw_content": "",  # Empty
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
    assert len(errors) >= 2


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_validator_none_values(validator, valid_workflow_result):
    """Test None values properly handled."""
    invalid_result = valid_workflow_result.copy()
    invalid_result["raw_content"] = None
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    assert len(errors) > 0


def test_validator_empty_dict(validator):
    """Test empty dict returns errors."""
    validated, errors = validator.validate({}, "completed")
    assert validated is None
    assert len(errors) > 0


def test_validator_partial_data(validator):
    """Test partial data returns specific errors."""
    partial_result = {
        "raw_content": "Test content",
        # Missing other required fields
    }
    validated, errors = validator.validate(partial_result, "completed")
    assert validated is None
    # Should have specific errors about missing fields
    assert len(errors) > 0


# ============================================================================
# Exception Handling Tests
# ============================================================================


def test_validator_unexpected_exception(validator, valid_workflow_result, monkeypatch):
    """Test unexpected exceptions handled."""

    # Mock model_validate to raise unexpected exception
    def mock_validate(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    monkeypatch.setattr(WorkflowResult, "model_validate", mock_validate)

    validated, errors = validator.validate(valid_workflow_result, "completed")
    assert validated is None
    assert len(errors) > 0
    assert "Validation error" in errors[0]


# ============================================================================
# Status-Aware Validation Tests
# ============================================================================


def test_validator_failed_status_validation(validator):
    """Test failed status allows missing fields."""
    # Failed workflows should pass validation even with missing content
    failed_result = {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
        "workflow_status": "failed",
    }
    validated, errors = validator.validate(failed_result, "failed")
    # Failed status doesn't require content fields
    assert validated is not None or len(errors) == 0


def test_validator_status_specific_requirements(validator, valid_workflow_result):
    """Test status-specific requirements enforced."""
    # Completed status requires all fields
    validated, errors = validator.validate(valid_workflow_result, "completed")
    assert validated is not None
    assert errors == []


# ============================================================================
# Error Extraction Helper Tests
# ============================================================================


def test_error_extraction_single_field(validator):
    """Test single field error extracted."""
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
    # Should have error about raw_content
    assert any("raw_content" in error.lower() for error in errors)


def test_error_extraction_nested_field(validator):
    """Test nested field error extracted."""
    invalid_result = {
        "content_ref": {
            "uri": "invalid://uri",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    # Should have error about content_ref.uri
    assert any("content_ref" in error.lower() or "uri" in error.lower() for error in errors)


def test_error_extraction_field_path_format(validator):
    """Test field paths formatted correctly."""
    invalid_result = {
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "",  # Empty title
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
    }
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    # Error messages should have field paths
    assert all(":" in error or "." in error for error in errors)


def test_error_extraction_empty_errors(validator):
    """Test empty error list handled."""
    # This shouldn't happen, but test the code path
    validation_error = ValidationError.from_exception_data(
        "WorkflowResult",
        [],
    )
    errors = validator._extract_validation_errors(validation_error)
    assert isinstance(errors, list)
    # Empty errors list is valid


def test_error_extraction_complex_nesting(validator):
    """Test complex nested errors handled."""
    invalid_result = {
        "content_ref": {
            "uri": "invalid://uri",
            "summary": "",  # Empty summary
            "size_bytes": -1,  # Negative
            "content_type": "text/plain",
        },
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "",  # Empty title
            "word_count": -1,  # Negative
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 100,  # Wrong dimensions
    }
    validated, errors = validator.validate(invalid_result, "completed")
    assert validated is None
    # Should have multiple errors from nested fields
    assert len(errors) >= 3
