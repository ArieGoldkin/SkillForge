"""Unit tests for core utility functions."""

import uuid
from uuid import UUID

from app.core.constants import UUID_NAMESPACE_DNS
from app.core.utils import normalize_analysis_id_to_uuid


def test_normalize_uuid_string():
    """Test that valid UUID strings are converted correctly."""
    uuid_str = "123e4567-e89b-12d3-a456-426614174000"
    result = normalize_analysis_id_to_uuid(uuid_str)

    assert isinstance(result, UUID)
    assert str(result) == uuid_str


def test_normalize_uuid_object():
    """Test that UUID objects are returned as-is."""
    uuid_obj = UUID("123e4567-e89b-12d3-a456-426614174000")
    result = normalize_analysis_id_to_uuid(uuid_obj)

    assert isinstance(result, UUID)
    assert result == uuid_obj
    # Verify it's the same object (identity check)
    assert result is uuid_obj


def test_normalize_non_uuid_string():
    """Test that non-UUID strings are converted to deterministic UUIDs."""
    non_uuid_str = "dev-test-opus-4-5"
    result = normalize_analysis_id_to_uuid(non_uuid_str)

    assert isinstance(result, UUID)
    # Verify it's a valid UUID
    assert str(result)  # Should not raise


def test_normalize_deterministic():
    """Test that same non-UUID string always produces same UUID."""
    non_uuid_str = "dev-test-opus-4-5"
    result1 = normalize_analysis_id_to_uuid(non_uuid_str)
    result2 = normalize_analysis_id_to_uuid(non_uuid_str)

    assert result1 == result2
    # Verify it uses uuid5 with DNS namespace
    namespace = UUID(UUID_NAMESPACE_DNS)
    expected = uuid.uuid5(namespace, non_uuid_str)
    assert result1 == expected


def test_normalize_different_strings():
    """Test that different non-UUID strings produce different UUIDs."""
    str1 = "dev-test-opus-4-5"
    str2 = "dev-test-sonnet-4-5"
    result1 = normalize_analysis_id_to_uuid(str1)
    result2 = normalize_analysis_id_to_uuid(str2)

    assert result1 != result2
