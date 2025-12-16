"""Unit tests for the vector validation module."""

import pytest

from app.core.validation.vector import (

@pytest.mark.unit
    ValidationResult,
    VectorValidationError,
    VectorValidator,
    validate_embedding,
)


class TestVectorValidator:
    """Tests for VectorValidator class."""

    def test_valid_vector_passes(self):
        """Valid vector passes all checks."""
        validator = VectorValidator(expected_dimensions=3)
        vector = [0.5, 0.5, 0.5]  # magnitude ~0.866

        result = validator.validate(vector)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_dimension_mismatch_fails(self):
        """Wrong dimensions fail validation."""
        validator = VectorValidator(expected_dimensions=3)
        vector = [0.1, 0.2]  # Only 2 dimensions

        result = validator.validate(vector)
        assert not result.is_valid
        assert any("Dimension mismatch" in e for e in result.errors)

    def test_nan_values_fail(self):
        """NaN values fail validation."""
        validator = VectorValidator(expected_dimensions=3)
        vector = [0.1, float("nan"), 0.3]

        result = validator.validate(vector)
        assert not result.is_valid
        assert any("NaN" in e for e in result.errors)

    def test_inf_values_fail(self):
        """Infinity values fail validation."""
        validator = VectorValidator(expected_dimensions=3)
        vector = [0.1, float("inf"), 0.3]

        result = validator.validate(vector)
        assert not result.is_valid
        assert any("Inf" in e for e in result.errors)

    def test_zero_vector_fails(self):
        """Zero vector fails validation."""
        validator = VectorValidator(expected_dimensions=3, zero_threshold=1e-10)
        vector = [0.0, 0.0, 0.0]

        result = validator.validate(vector)
        assert not result.is_valid
        assert any("Zero vector" in e for e in result.errors)

    def test_magnitude_calculated(self):
        """Magnitude is calculated correctly."""
        validator = VectorValidator(expected_dimensions=3)
        vector = [3.0, 4.0, 0.0]  # magnitude = 5

        result = validator.validate(vector)
        assert result.magnitude is not None
        assert abs(result.magnitude - 5.0) < 0.0001

    def test_low_magnitude_warning(self):
        """Low magnitude generates warning."""
        validator = VectorValidator(
            expected_dimensions=3,
            min_magnitude=0.5,
        )
        vector = [0.01, 0.01, 0.01]  # magnitude ~0.017

        result = validator.validate(vector)
        assert result.is_valid  # Still valid, just warning
        assert any("Low magnitude" in w for w in result.warnings)

    def test_high_magnitude_warning(self):
        """High magnitude generates warning."""
        validator = VectorValidator(
            expected_dimensions=3,
            max_magnitude=2.0,
        )
        vector = [5.0, 5.0, 5.0]  # magnitude ~8.66

        result = validator.validate(vector)
        assert result.is_valid  # Still valid, just warning
        assert any("High magnitude" in w for w in result.warnings)

    def test_strict_mode_promotes_warnings(self):
        """Strict mode treats warnings as errors."""
        validator = VectorValidator(
            expected_dimensions=3,
            min_magnitude=0.5,
        )
        vector = [0.01, 0.01, 0.01]  # Low magnitude

        result = validator.validate(vector, strict=True)
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_disabled_validation_passes_everything(self):
        """Disabled validation always passes."""
        validator = VectorValidator(
            expected_dimensions=3,
            enabled=False,
        )
        vector = [float("nan"), float("inf"), 0.0]  # Invalid

        result = validator.validate(vector)
        assert result.is_valid

    def test_validate_or_raise_on_invalid(self):
        """validate_or_raise raises exception on invalid vector."""
        validator = VectorValidator(expected_dimensions=3)
        vector = [0.1, float("nan"), 0.3]

        with pytest.raises(VectorValidationError, match="NaN"):
            validator.validate_or_raise(vector)

    def test_validate_or_raise_on_valid(self):
        """validate_or_raise doesn't raise on valid vector."""
        validator = VectorValidator(expected_dimensions=3)
        vector = [0.5, 0.5, 0.5]

        # Should not raise
        validator.validate_or_raise(vector)

    def test_validate_batch(self):
        """validate_batch processes multiple vectors."""
        validator = VectorValidator(expected_dimensions=3)
        vectors = [
            [0.5, 0.5, 0.5],  # Valid
            [float("nan"), 0.1, 0.2],  # Invalid
            [0.3, 0.3, 0.3],  # Valid
        ]

        results, valid_count, invalid_count = validator.validate_batch(vectors)

        assert len(results) == 3
        assert valid_count == 2
        assert invalid_count == 1


class TestValidateEmbeddingFunction:
    """Tests for validate_embedding convenience function."""

    def test_validate_embedding_basic(self):
        """validate_embedding works for basic case."""
        vector = [0.5] * 1536  # Standard OpenAI dimension

        result = validate_embedding(vector, expected_dimensions=1536)
        assert result.is_valid

    def test_validate_embedding_with_custom_dimensions(self):
        """validate_embedding respects custom dimensions."""
        vector = [0.5] * 768  # Different dimension

        result = validate_embedding(vector, expected_dimensions=768)
        assert result.is_valid

        # Wrong dimensions should fail
        result = validate_embedding(vector, expected_dimensions=1536)
        assert not result.is_valid


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """ValidationResult can be created correctly."""
        result = ValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Low magnitude"],
            magnitude=0.5,
        )

        assert result.is_valid
        assert len(result.warnings) == 1
        assert result.magnitude == 0.5
