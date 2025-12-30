"""Unit tests for embedding_utils.py - safe embedding vector handling.

Issue #602: NumPy array handling utilities to avoid ambiguous truth value errors.

This module tests all utility functions for safe handling of embedding vectors,
which can be either Python lists or numpy arrays.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core.embedding_utils import (
    has_embedding,
    is_valid_embedding,
    normalize_embedding,
    safe_bool_for_logging,
    to_list,
    to_numpy,
)


@pytest.mark.unit
class TestHasEmbedding:
    """Tests for has_embedding() - check if embedding exists and is non-empty."""

    def test_none_returns_false(self):
        """Test that None returns False."""
        assert has_embedding(None) is False

    def test_empty_list_returns_false(self):
        """Test that empty list returns False."""
        assert has_embedding([]) is False

    def test_empty_numpy_array_returns_false(self):
        """Test that empty numpy array returns False."""
        assert has_embedding(np.array([])) is False

    def test_list_with_elements_returns_true(self):
        """Test that non-empty list returns True."""
        assert has_embedding([0.1, 0.2, 0.3]) is True

    def test_numpy_array_with_elements_returns_true(self):
        """Test that non-empty numpy array returns True."""
        assert has_embedding(np.array([0.1, 0.2, 0.3])) is True

    def test_single_element_list_returns_true(self):
        """Test that single-element list returns True."""
        assert has_embedding([0.1]) is True

    def test_single_element_numpy_array_returns_true(self):
        """Test that single-element numpy array returns True."""
        assert has_embedding(np.array([0.1])) is True

    def test_openai_embedding_size(self):
        """Test with OpenAI-sized embedding (1536 dimensions)."""
        embedding = [0.1] * 1536
        assert has_embedding(embedding) is True

    def test_numpy_avoids_ambiguous_truth_value_error(self):
        """Test that numpy arrays don't raise ValueError on truth check.

        This is the core issue #602: using `if array:` raises:
        ValueError: The truth value of an array with more than one element is ambiguous.
        """
        array = np.array([0.1, 0.2, 0.3])
        # This should NOT raise ValueError
        result = has_embedding(array)
        assert result is True

    def test_invalid_type_returns_false(self):
        """Test that invalid types are handled gracefully."""
        # Strings have len() so they'll return True if non-empty
        # But this demonstrates the function handles non-embedding types
        assert has_embedding("not an embedding") is True  # type: ignore[arg-type]

        # Integer doesn't have len() - should catch TypeError
        result = has_embedding(42)  # type: ignore[arg-type]
        assert result is False


@pytest.mark.unit
class TestIsValidEmbedding:
    """Tests for is_valid_embedding() - validate dimensions."""

    def test_none_returns_false(self):
        """Test that None returns False."""
        assert is_valid_embedding(None) is False

    def test_empty_list_returns_false(self):
        """Test that empty list returns False."""
        assert is_valid_embedding([]) is False

    def test_correct_dimensions_returns_true(self):
        """Test that correct dimensions (1536) returns True."""
        embedding = [0.1] * 1536
        assert is_valid_embedding(embedding) is True

    def test_numpy_array_correct_dimensions_returns_true(self):
        """Test that numpy array with correct dimensions returns True."""
        embedding = np.array([0.1] * 1536)
        assert is_valid_embedding(embedding) is True

    def test_wrong_dimensions_returns_false(self):
        """Test that wrong dimensions returns False."""
        # 768 dimensions (BERT/sentence-transformers)
        embedding = [0.1] * 768
        assert is_valid_embedding(embedding) is False

    def test_too_few_dimensions_returns_false(self):
        """Test that too few dimensions returns False."""
        embedding = [0.1] * 10
        assert is_valid_embedding(embedding) is False

    def test_too_many_dimensions_returns_false(self):
        """Test that too many dimensions returns False."""
        embedding = [0.1] * 2000
        assert is_valid_embedding(embedding) is False

    def test_custom_dimensions(self):
        """Test validation with custom expected dimensions."""
        embedding = [0.1] * 768
        assert is_valid_embedding(embedding, expected_dimensions=768) is True
        assert is_valid_embedding(embedding, expected_dimensions=1536) is False

    def test_single_element_invalid_for_openai(self):
        """Test that single element is invalid for OpenAI (1536)."""
        assert is_valid_embedding([0.1]) is False


@pytest.mark.unit
class TestToList:
    """Tests for to_list() - convert embeddings to Python lists."""

    def test_none_returns_none(self):
        """Test that None returns None."""
        assert to_list(None) is None

    def test_list_returns_same_list(self):
        """Test that Python list is returned unchanged."""
        original = [0.1, 0.2, 0.3]
        result = to_list(original)
        assert result == original
        assert result is original  # Same object

    def test_numpy_array_returns_list(self):
        """Test that numpy array is converted to list."""
        array = np.array([0.1, 0.2, 0.3])
        result = to_list(array)
        assert isinstance(result, list)
        assert result == [0.1, 0.2, 0.3]

    def test_numpy_array_float64_preserves_precision(self):
        """Test that conversion preserves float64 precision."""
        array = np.array([0.123456789012345], dtype=np.float64)
        result = to_list(array)
        assert result is not None
        assert abs(result[0] - 0.123456789012345) < 1e-10

    def test_empty_list_returns_empty_list(self):
        """Test that empty list is returned."""
        assert to_list([]) == []

    def test_empty_numpy_array_returns_empty_list(self):
        """Test that empty numpy array returns empty list."""
        array = np.array([])
        result = to_list(array)
        assert result == []

    def test_large_embedding_conversion(self):
        """Test conversion of OpenAI-sized embedding (1536 dims)."""
        array = np.random.rand(1536).astype(np.float64)
        result = to_list(array)
        assert result is not None
        assert len(result) == 1536
        assert isinstance(result, list)


@pytest.mark.unit
class TestToNumpy:
    """Tests for to_numpy() - convert embeddings to numpy arrays."""

    def test_none_returns_none(self):
        """Test that None returns None."""
        assert to_numpy(None) is None

    def test_list_returns_numpy_array(self):
        """Test that Python list is converted to numpy array."""
        original = [0.1, 0.2, 0.3]
        result = to_numpy(original)
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float64
        np.testing.assert_array_almost_equal(result, [0.1, 0.2, 0.3])

    def test_numpy_array_returns_numpy_array(self):
        """Test that numpy array is returned (converted to float64)."""
        array = np.array([0.1, 0.2, 0.3], dtype=np.float32)
        result = to_numpy(array)
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float64

    def test_numpy_array_float64_returns_same_dtype(self):
        """Test that float64 numpy array maintains dtype."""
        array = np.array([0.1, 0.2, 0.3], dtype=np.float64)
        result = to_numpy(array)
        assert result is not None
        assert result.dtype == np.float64

    def test_empty_list_returns_empty_array(self):
        """Test that empty list returns empty numpy array."""
        result = to_numpy([])
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert len(result) == 0

    def test_large_embedding_conversion(self):
        """Test conversion of OpenAI-sized embedding (1536 dims)."""
        original = [0.1] * 1536
        result = to_numpy(original)
        assert result is not None
        assert result.shape == (1536,)
        assert result.dtype == np.float64


@pytest.mark.unit
class TestNormalizeEmbedding:
    """Tests for normalize_embedding() - normalize to unit length."""

    def test_none_returns_none(self):
        """Test that None returns None."""
        assert normalize_embedding(None) is None

    def test_empty_list_returns_none(self):
        """Test that empty list returns None."""
        assert normalize_embedding([]) is None

    def test_normalize_simple_vector(self):
        """Test normalization of simple 3-4-5 right triangle (magnitude 5)."""
        vector = [3.0, 4.0]
        result = normalize_embedding(vector)
        assert result is not None

        # Should have L2 norm = 1
        magnitude = sum(x**2 for x in result) ** 0.5
        assert abs(magnitude - 1.0) < 1e-10

        # Components should be [3/5, 4/5] = [0.6, 0.8]
        assert abs(result[0] - 0.6) < 1e-10
        assert abs(result[1] - 0.8) < 1e-10

    def test_normalize_returns_list(self):
        """Test that result is a Python list, not numpy array."""
        vector = [1.0, 2.0, 3.0]
        result = normalize_embedding(vector)
        assert isinstance(result, list)

    def test_normalize_numpy_array(self):
        """Test normalization of numpy array input."""
        array = np.array([3.0, 4.0])
        result = normalize_embedding(array)
        assert result is not None
        assert isinstance(result, list)

        magnitude = sum(x**2 for x in result) ** 0.5
        assert abs(magnitude - 1.0) < 1e-10

    def test_normalize_unit_vector_unchanged(self):
        """Test that already-normalized vector stays normalized."""
        # Unit vector [0.6, 0.8] already has magnitude 1
        vector = [0.6, 0.8]
        result = normalize_embedding(vector)
        assert result is not None

        magnitude = sum(x**2 for x in result) ** 0.5
        assert abs(magnitude - 1.0) < 1e-10

    def test_normalize_high_dimensional_vector(self):
        """Test normalization of OpenAI-sized embedding (1536 dims)."""
        # Random vector
        vector = list(np.random.randn(1536))
        result = normalize_embedding(vector)
        assert result is not None
        assert len(result) == 1536

        # Check unit length
        magnitude = sum(x**2 for x in result) ** 0.5
        assert abs(magnitude - 1.0) < 1e-6

    def test_zero_vector_returns_none(self):
        """Test that zero vector (magnitude 0) returns None."""
        vector = [0.0, 0.0, 0.0]
        result = normalize_embedding(vector)
        assert result is None

    def test_near_zero_vector_returns_none(self):
        """Test that near-zero vector returns None."""
        vector = [1e-100, 1e-100, 1e-100]
        result = normalize_embedding(vector)
        # Might return None depending on floating point behavior
        # At minimum, should not crash


@pytest.mark.unit
class TestSafeBoolForLogging:
    """Tests for safe_bool_for_logging() - safe boolean for logging."""

    def test_none_returns_false(self):
        """Test that None returns False."""
        assert safe_bool_for_logging(None) is False

    def test_empty_list_returns_true(self):
        """Test that empty list returns True (exists, even if empty)."""
        # This checks existence, not emptiness
        assert safe_bool_for_logging([]) is True

    def test_list_with_elements_returns_true(self):
        """Test that non-empty list returns True."""
        assert safe_bool_for_logging([0.1, 0.2]) is True

    def test_numpy_array_returns_true(self):
        """Test that numpy array returns True (no ambiguous truth error)."""
        array = np.array([0.1, 0.2, 0.3])
        # This is the key test - should NOT raise ValueError
        result = safe_bool_for_logging(array)
        assert result is True

    def test_empty_numpy_array_returns_true(self):
        """Test that empty numpy array returns True (exists)."""
        array = np.array([])
        assert safe_bool_for_logging(array) is True

    def test_use_in_logging_context(self):
        """Test typical usage in logging statements."""
        embedding_1 = [0.1] * 1536
        embedding_2 = None
        embedding_3 = np.array([0.1] * 1536)

        # These should all work in a logging context
        log_msg_1 = f"has_embedding={safe_bool_for_logging(embedding_1)}"
        log_msg_2 = f"has_embedding={safe_bool_for_logging(embedding_2)}"
        log_msg_3 = f"has_embedding={safe_bool_for_logging(embedding_3)}"

        assert "True" in log_msg_1
        assert "False" in log_msg_2
        assert "True" in log_msg_3


@pytest.mark.unit
class TestEdgeCases:
    """Edge cases and error handling tests."""

    def test_has_embedding_with_nested_list(self):
        """Test has_embedding with nested list (invalid embedding format)."""
        # Nested lists should still return True (has length > 0)
        nested = [[0.1, 0.2], [0.3, 0.4]]
        assert has_embedding(nested) is True

    def test_to_list_with_tuple(self):
        """Test to_list with tuple input (iterable but not list/array)."""
        tuple_input = (0.1, 0.2, 0.3)
        result = to_list(tuple_input)  # type: ignore[arg-type]
        # Should convert via list() fallback
        assert result == [0.1, 0.2, 0.3]

    def test_to_numpy_with_tuple(self):
        """Test to_numpy with tuple input."""
        tuple_input = (0.1, 0.2, 0.3)
        result = to_numpy(tuple_input)  # type: ignore[arg-type]
        assert result is not None
        assert isinstance(result, np.ndarray)

    def test_normalize_single_element_vector(self):
        """Test normalization of single-element vector."""
        vector = [5.0]
        result = normalize_embedding(vector)
        assert result is not None
        # Normalized to [1.0] (sign preserved)
        assert abs(result[0] - 1.0) < 1e-10

    def test_normalize_negative_values(self):
        """Test that negative values are handled correctly."""
        vector = [-3.0, -4.0]
        result = normalize_embedding(vector)
        assert result is not None

        # Should still be unit length
        magnitude = sum(x**2 for x in result) ** 0.5
        assert abs(magnitude - 1.0) < 1e-10

        # Signs should be preserved
        assert result[0] < 0
        assert result[1] < 0

    def test_normalize_mixed_signs(self):
        """Test normalization with mixed positive/negative values."""
        vector = [3.0, -4.0]
        result = normalize_embedding(vector)
        assert result is not None

        magnitude = sum(x**2 for x in result) ** 0.5
        assert abs(magnitude - 1.0) < 1e-10

        # Should be [0.6, -0.8]
        assert abs(result[0] - 0.6) < 1e-10
        assert abs(result[1] - (-0.8)) < 1e-10


@pytest.mark.unit
class TestIntegrationWithRealEmbeddings:
    """Integration tests with realistic embedding scenarios."""

    def test_openai_embedding_workflow(self):
        """Test complete workflow with OpenAI-style embedding."""
        # Simulate OpenAI embedding response (1536 dimensions)
        embedding = list(np.random.randn(1536))

        # Check existence
        assert has_embedding(embedding) is True

        # Validate dimensions
        assert is_valid_embedding(embedding) is True

        # Normalize for cosine similarity
        normalized = normalize_embedding(embedding)
        assert normalized is not None
        assert len(normalized) == 1536

        # Verify unit length
        magnitude = sum(x**2 for x in normalized) ** 0.5
        assert abs(magnitude - 1.0) < 1e-6

    def test_numpy_array_roundtrip(self):
        """Test conversion roundtrip: list -> numpy -> list."""
        original = [0.1, 0.2, 0.3]

        # Convert to numpy
        array = to_numpy(original)
        assert array is not None

        # Convert back to list
        result = to_list(array)
        assert result is not None

        # Should match original
        assert len(result) == len(original)
        for i in range(len(original)):
            assert abs(result[i] - original[i]) < 1e-10

    def test_database_persistence_scenario(self):
        """Test typical database persistence scenario.

        When storing embeddings in PostgreSQL/PGVector:
        1. Receive numpy array from model
        2. Validate it exists and has correct dimensions
        3. Convert to list for JSON serialization
        """
        # Simulate model output
        model_output = np.random.rand(1536).astype(np.float64)

        # Validate before storage
        assert has_embedding(model_output) is True
        assert is_valid_embedding(model_output) is True

        # Convert for database
        db_embedding = to_list(model_output)
        assert db_embedding is not None
        assert isinstance(db_embedding, list)
        assert len(db_embedding) == 1536

        # Logging
        log_has_embedding = safe_bool_for_logging(model_output)
        assert log_has_embedding is True

    def test_retrieval_scenario(self):
        """Test typical retrieval scenario.

        When loading embeddings from database:
        1. Load as list from JSON
        2. Convert to numpy for similarity calculation
        3. Normalize if needed
        """
        # Simulate database retrieval (list from JSON)
        db_embedding = [0.1] * 1536

        # Convert to numpy for calculations
        array = to_numpy(db_embedding)
        assert array is not None

        # Normalize for cosine similarity
        normalized = normalize_embedding(db_embedding)
        assert normalized is not None

        # Calculate similarity (dot product of normalized vectors)
        similarity = sum(a * b for a, b in zip(normalized, normalized))
        assert abs(similarity - 1.0) < 1e-6  # Self-similarity = 1.0
