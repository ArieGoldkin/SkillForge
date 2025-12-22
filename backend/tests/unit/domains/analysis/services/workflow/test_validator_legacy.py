"""Unit tests for workflow result validator."""

from app.domains.analysis.services.workflow.validator import validate_workflow_result


def test_validator_identifies_missing_fields():
    """Test validator identifies missing required workflow fields."""
    result = {
        "raw_content": "content",
        "extraction_metadata": None,
        "content_embedding": None,
    }

    missing = validate_workflow_result(result)
    assert set(missing) == {"extraction_metadata", "content_embedding"}


def test_validator_returns_empty_list_when_all_fields_present():
    """Test validator returns empty list when all required fields are present."""
    result = {
        "raw_content": "content",
        "extraction_metadata": {"title": "Test"},
        "content_embedding": [0.1] * 1536,
    }

    missing = validate_workflow_result(result)
    assert missing == []


def test_validator_identifies_missing_raw_content():
    """Test validator identifies missing raw_content field."""
    result = {
        "extraction_metadata": {"title": "Test"},
        "content_embedding": [0.1] * 1536,
    }

    missing = validate_workflow_result(result)
    assert "raw_content" in missing
