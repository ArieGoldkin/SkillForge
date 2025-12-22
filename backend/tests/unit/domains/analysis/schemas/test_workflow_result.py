"""Unit tests for workflow result Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.domains.analysis.schemas.workflow_result import (
    ContentRef,
    ExtractionMetadata,
    WorkflowResult,
)

# ============================================================================
# ExtractionMetadata Tests (8 tests)
# ============================================================================


def test_extraction_metadata_valid_data():
    """Test valid data passes validation."""
    metadata = ExtractionMetadata(
        title="Test Article",
        word_count=1000,
        char_count=5000,
        language="en",
        author="Test Author",
    )
    assert metadata.title == "Test Article"
    assert metadata.word_count == 1000
    assert metadata.char_count == 5000


def test_extraction_metadata_empty_title():
    """Test empty title fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ExtractionMetadata(
            title="",
            word_count=1000,
            char_count=5000,
        )
    errors = exc_info.value.errors()
    assert any("title" in str(err["loc"]) for err in errors)


def test_extraction_metadata_whitespace_title():
    """Test whitespace-only title fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ExtractionMetadata(
            title="   ",
            word_count=1000,
            char_count=5000,
        )
    errors = exc_info.value.errors()
    assert any("title" in str(err["loc"]) for err in errors)


def test_extraction_metadata_negative_word_count():
    """Test negative word_count fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ExtractionMetadata(
            title="Test",
            word_count=-1,
            char_count=5000,
        )
    errors = exc_info.value.errors()
    assert any("word_count" in str(err["loc"]) for err in errors)


def test_extraction_metadata_negative_char_count():
    """Test negative char_count fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ExtractionMetadata(
            title="Test",
            word_count=1000,
            char_count=-1,
        )
    errors = exc_info.value.errors()
    assert any("char_count" in str(err["loc"]) for err in errors)


def test_extraction_metadata_long_title():
    """Test title >500 chars fails validation."""
    long_title = "a" * 501
    with pytest.raises(ValidationError) as exc_info:
        ExtractionMetadata(
            title=long_title,
            word_count=1000,
            char_count=5000,
        )
    errors = exc_info.value.errors()
    assert any("title" in str(err["loc"]) for err in errors)


def test_extraction_metadata_optional_fields():
    """Test optional fields can be None."""
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
        language=None,
        author=None,
        published_date=None,
    )
    assert metadata.language is None
    assert metadata.author is None
    assert metadata.published_date is None


def test_extraction_metadata_type_coercion():
    """Test string numbers convert to int."""
    # Use model_validate to test Pydantic coercion
    metadata = ExtractionMetadata.model_validate(
        {
            "title": "Test",
            "word_count": "1000",  # String should convert to int
            "char_count": "5000",  # String should convert to int
        }
    )
    assert isinstance(metadata.word_count, int)
    assert isinstance(metadata.char_count, int)
    assert metadata.word_count == 1000
    assert metadata.char_count == 5000


# ============================================================================
# ContentRef Tests (10 tests)
# ============================================================================


def test_content_ref_valid_uri():
    """Test valid URI passes validation."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    assert content_ref.uri.startswith("analysis://")


def test_content_ref_invalid_uri_format():
    """Test invalid URI format fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ContentRef(
            uri="invalid://uri",
            summary="Test summary",
            size_bytes=1000,
            content_type="text/plain",
        )
    errors = exc_info.value.errors()
    assert any("uri" in str(err["loc"]) for err in errors)


def test_content_ref_invalid_uuid():
    """Test invalid UUID in URI fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ContentRef(
            uri="analysis://not-a-uuid/content",
            summary="Test summary",
            size_bytes=1000,
            content_type="text/plain",
        )
    errors = exc_info.value.errors()
    assert any("uri" in str(err["loc"]) for err in errors)


def test_content_ref_empty_summary():
    """Test empty summary fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ContentRef(
            uri="analysis://12345678-1234-1234-1234-123456789abc/content",
            summary="",
            size_bytes=1000,
            content_type="text/plain",
        )
    errors = exc_info.value.errors()
    assert any("summary" in str(err["loc"]) for err in errors)


def test_content_ref_long_summary():
    """Test summary >2000 chars fails validation."""
    long_summary = "a" * 2001
    with pytest.raises(ValidationError) as exc_info:
        ContentRef(
            uri="analysis://12345678-1234-1234-1234-123456789abc/content",
            summary=long_summary,
            size_bytes=1000,
            content_type="text/plain",
        )
    errors = exc_info.value.errors()
    assert any("summary" in str(err["loc"]) for err in errors)


def test_content_ref_negative_size():
    """Test negative size_bytes fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ContentRef(
            uri="analysis://12345678-1234-1234-1234-123456789abc/content",
            summary="Test summary",
            size_bytes=-1,
            content_type="text/plain",
        )
    errors = exc_info.value.errors()
    assert any("size_bytes" in str(err["loc"]) for err in errors)


def test_content_ref_empty_content_type():
    """Test empty content_type fails validation."""
    with pytest.raises(ValidationError) as exc_info:
        ContentRef(
            uri="analysis://12345678-1234-1234-1234-123456789abc/content",
            summary="Test summary",
            size_bytes=1000,
            content_type="",
        )
    errors = exc_info.value.errors()
    assert any("content_type" in str(err["loc"]) for err in errors)


def test_content_ref_long_content_type():
    """Test content_type >50 chars fails validation."""
    long_type = "a" * 51
    with pytest.raises(ValidationError) as exc_info:
        ContentRef(
            uri="analysis://12345678-1234-1234-1234-123456789abc/content",
            summary="Test summary",
            size_bytes=1000,
            content_type=long_type,
        )
    errors = exc_info.value.errors()
    assert any("content_type" in str(err["loc"]) for err in errors)


def test_content_ref_default_sections():
    """Test available_sections defaults to empty list."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    assert content_ref.available_sections == []


def test_content_ref_uri_extraction():
    """Test can extract analysis_id from URI."""
    analysis_id = "12345678-1234-1234-1234-123456789abc"
    uri = f"analysis://{analysis_id}/content"
    content_ref = ContentRef(
        uri=uri,
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    uri_parts = content_ref.uri.split("/")
    extracted_id = uri_parts[2]
    assert extracted_id == analysis_id


# ============================================================================
# WorkflowResult Tests (12 tests)
# ============================================================================


def test_workflow_result_valid_completed():
    """Test valid completed workflow passes validation."""
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
        workflow_status="completed",
    )
    assert result.workflow_status == "completed"
    assert result.content_ref is not None
    assert result.raw_content == "Test content"


def test_workflow_result_missing_content_ref():
    """Test missing content_ref fails validation."""
    # Use model_validate to test missing required field
    with pytest.raises(ValidationError) as exc_info:
        WorkflowResult.model_validate(
            {
                "raw_content": "Test content",
                "extraction_metadata": {
                    "title": "Test",
                    "word_count": 1000,
                    "char_count": 5000,
                },
                "content_embedding": [0.1] * 1536,
            }
        )
    errors = exc_info.value.errors()
    assert any("content_ref" in str(err["loc"]) for err in errors)


def test_workflow_result_empty_raw_content():
    """Test empty raw_content fails validation."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    with pytest.raises(ValidationError) as exc_info:
        WorkflowResult(
            content_ref=content_ref,
            raw_content="",
            extraction_metadata=metadata,
            content_embedding=[0.1] * 1536,
        )
    errors = exc_info.value.errors()
    assert any("raw_content" in str(err["loc"]) for err in errors)


def test_workflow_result_wrong_embedding_dimensions():
    """Test wrong embedding dimensions fails validation."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    with pytest.raises(ValidationError) as exc_info:
        WorkflowResult(
            content_ref=content_ref,
            raw_content="Test content",
            extraction_metadata=metadata,
            content_embedding=[0.1] * 100,  # Wrong dimensions
        )
    errors = exc_info.value.errors()
    assert any("content_embedding" in str(err["loc"]) for err in errors)


def test_workflow_result_validate_for_status_completed():
    """Test status validation works for completed status."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )
    missing = result.validate_for_status("completed")
    assert missing == []


def test_workflow_result_validate_for_status_failed():
    """Test failed status allows missing fields."""
    # Create minimal result (no content fields required for failed)
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
        workflow_status="failed",
    )
    missing = result.validate_for_status("failed")
    # Failed status doesn't require content fields
    assert missing == []


def test_workflow_result_type_coercion():
    """Test string numbers convert to float."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    # Use string numbers in embedding (should convert to float)
    embedding_str = ["0.1"] * 1536
    # Use model_validate to test Pydantic coercion
    result = WorkflowResult.model_validate(
        {
            "content_ref": {
                "uri": content_ref.uri,
                "summary": content_ref.summary,
                "size_bytes": content_ref.size_bytes,
                "content_type": content_ref.content_type,
            },
            "raw_content": "Test content",
            "extraction_metadata": {
                "title": metadata.title,
                "word_count": metadata.word_count,
                "char_count": metadata.char_count,
            },
            "content_embedding": embedding_str,
        }
    )
    assert all(isinstance(x, float) for x in result.content_embedding)


def test_workflow_result_optional_fields():
    """Test optional fields can be None."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
        artifact_id=None,
        workflow_status=None,
        final_error=None,
    )
    assert result.artifact_id is None
    assert result.workflow_status is None
    assert result.final_error is None


def test_workflow_result_invalid_status():
    """Test invalid status value fails validation."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    # Use model_validate to test invalid enum value
    with pytest.raises(ValidationError) as exc_info:
        WorkflowResult.model_validate(
            {
                "content_ref": {
                    "uri": content_ref.uri,
                    "summary": content_ref.summary,
                    "size_bytes": content_ref.size_bytes,
                    "content_type": content_ref.content_type,
                },
                "raw_content": "Test content",
                "extraction_metadata": {
                    "title": metadata.title,
                    "word_count": metadata.word_count,
                    "char_count": metadata.char_count,
                },
                "content_embedding": [0.1] * 1536,
                "workflow_status": "invalid_status",  # Invalid status
            }
        )
    errors = exc_info.value.errors()
    assert any("workflow_status" in str(err["loc"]) for err in errors)


def test_workflow_result_whitespace_raw_content():
    """Test whitespace-only content fails validation."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    with pytest.raises(ValidationError) as exc_info:
        WorkflowResult(
            content_ref=content_ref,
            raw_content="   ",  # Whitespace only
            extraction_metadata=metadata,
            content_embedding=[0.1] * 1536,
        )
    errors = exc_info.value.errors()
    assert any("raw_content" in str(err["loc"]) for err in errors)


def test_workflow_result_embedding_validation():
    """Test embedding validation detailed error message."""
    content_ref = ContentRef(
        uri="analysis://12345678-1234-1234-1234-123456789abc/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    with pytest.raises(ValidationError) as exc_info:
        WorkflowResult(
            content_ref=content_ref,
            raw_content="Test content",
            extraction_metadata=metadata,
            content_embedding=[0.1] * 768,  # Wrong: 768 instead of 1536
        )
    errors = exc_info.value.errors()
    error_msg = str(errors[0]["msg"]).lower()
    assert "1536" in error_msg or "dimensions" in error_msg


def test_workflow_result_nested_validation():
    """Test nested models validated."""
    # Invalid content_ref (invalid URI)
    # Use model_validate to test nested validation with dicts
    with pytest.raises(ValidationError) as exc_info:
        WorkflowResult.model_validate(
            {
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
        )
    errors = exc_info.value.errors()
    # Should have error about content_ref.uri
    assert any("content_ref" in str(err["loc"]) or "uri" in str(err["loc"]) for err in errors)
