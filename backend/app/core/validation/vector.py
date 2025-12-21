"""Vector validation guardrails for embedding quality assurance.

Provides validation for embedding vectors to catch common issues:
- Dimension mismatches
- NaN/Inf values
- Zero vectors
- Magnitude anomalies

These guardrails help ensure data integrity before vectors are
stored in the database or used for search operations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from app.core.config import settings

if TYPE_CHECKING:
    from app.core.types import EmbeddingVector

logger = structlog.get_logger(__name__)


class VectorValidationError(ValueError):
    """Exception raised when vector validation fails."""


@dataclass
class ValidationResult:
    """Result of vector validation.

    Attributes:
        is_valid: Whether the vector passed all validation checks.
        errors: List of validation error messages.
        warnings: List of non-critical warnings.
        magnitude: Computed L2 magnitude of the vector.

    """

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    magnitude: float | None = None


class VectorValidator:
    """Validates embedding vectors for quality and integrity.

    Configurable validator that checks vectors for common issues
    before storage or search operations.

    Attributes:
        expected_dimensions: Expected number of dimensions.
        zero_threshold: Threshold below which magnitude is considered zero.
        min_magnitude: Minimum acceptable magnitude.
        max_magnitude: Maximum acceptable magnitude.
        enabled: Whether validation is enabled.

    """

    def __init__(
        self,
        expected_dimensions: int | None = None,
        zero_threshold: float | None = None,
        min_magnitude: float = 0.1,
        max_magnitude: float = 10.0,
        enabled: bool | None = None,
    ) -> None:
        """Initialize the vector validator.

        Args:
            expected_dimensions: Expected dimensions (defaults to settings).
            zero_threshold: Threshold for zero detection (defaults to settings).
            min_magnitude: Minimum acceptable magnitude.
            max_magnitude: Maximum acceptable magnitude.
            enabled: Whether validation is enabled (defaults to settings).

        """
        self.expected_dimensions = expected_dimensions or settings.EMBEDDING_DIMENSIONS
        self.zero_threshold = zero_threshold or settings.VECTOR_ZERO_THRESHOLD
        self.min_magnitude = min_magnitude
        self.max_magnitude = max_magnitude
        self.enabled = enabled if enabled is not None else settings.VECTOR_VALIDATION_ENABLED

    def validate(self, vector: EmbeddingVector, strict: bool = False) -> ValidationResult:
        """Validate an embedding vector.

        Performs comprehensive validation including:
        - Dimension check
        - NaN/Inf detection
        - Zero vector detection
        - Magnitude range check

        Args:
            vector: The embedding vector to validate.
            strict: If True, treat warnings as errors.

        Returns:
            ValidationResult with validation status and any issues found.

        """
        if not self.enabled:
            return ValidationResult(is_valid=True, errors=[], warnings=[])

        errors: list[str] = []
        warnings: list[str] = []
        magnitude: float | None = None

        # Check dimensions
        if len(vector) != self.expected_dimensions:
            errors.append(
                f"Dimension mismatch: expected {self.expected_dimensions}, got {len(vector)}"
            )

        # Check for NaN/Inf values
        nan_count = sum(1 for v in vector if math.isnan(v))
        inf_count = sum(1 for v in vector if math.isinf(v))

        if nan_count > 0:
            errors.append(f"Vector contains {nan_count} NaN value(s)")

        if inf_count > 0:
            errors.append(f"Vector contains {inf_count} Inf value(s)")

        # Calculate magnitude (only if no NaN/Inf)
        if nan_count == 0 and inf_count == 0:
            magnitude = math.sqrt(sum(v * v for v in vector))

            # Check for zero vector
            if magnitude < self.zero_threshold:
                errors.append(f"Zero vector detected (magnitude {magnitude:.2e})")

            # Check magnitude range (for normalized vectors, should be ~1.0)
            elif magnitude < self.min_magnitude:
                warnings.append(f"Low magnitude {magnitude:.4f} (expected >= {self.min_magnitude})")
            elif magnitude > self.max_magnitude:
                warnings.append(
                    f"High magnitude {magnitude:.4f} (expected <= {self.max_magnitude})"
                )

        # In strict mode, promote warnings to errors
        if strict and warnings:
            errors.extend(warnings)
            warnings = []

        is_valid = len(errors) == 0

        if not is_valid:
            logger.warning(
                "vector_validation_failed",
                dimensions=len(vector),
                expected_dimensions=self.expected_dimensions,
                magnitude=magnitude,
                error_count=len(errors),
                errors=errors,
            )
        elif warnings:
            logger.debug(
                "vector_validation_warnings",
                dimensions=len(vector),
                magnitude=magnitude,
                warnings=warnings,
            )

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            magnitude=magnitude,
        )

    def validate_or_raise(self, vector: EmbeddingVector, strict: bool = False) -> None:
        """Validate a vector and raise an exception if invalid.

        Args:
            vector: The embedding vector to validate.
            strict: If True, treat warnings as errors.

        Raises:
            VectorValidationError: If validation fails.

        """
        result = self.validate(vector, strict=strict)

        if not result.is_valid:
            error_msg = "; ".join(result.errors)
            msg = f"Vector validation failed: {error_msg}"
            raise VectorValidationError(msg)

    def validate_batch(
        self,
        vectors: list[EmbeddingVector],
        strict: bool = False,
    ) -> tuple[list[ValidationResult], int, int]:
        """Validate a batch of vectors.

        Args:
            vectors: List of embedding vectors to validate.
            strict: If True, treat warnings as errors.

        Returns:
            Tuple of (results, valid_count, invalid_count).

        """
        results = [self.validate(v, strict=strict) for v in vectors]
        valid_count = sum(1 for r in results if r.is_valid)
        invalid_count = len(results) - valid_count

        if invalid_count > 0:
            logger.warning(
                "batch_validation_results",
                total=len(vectors),
                valid=valid_count,
                invalid=invalid_count,
            )

        return results, valid_count, invalid_count


def validate_embedding(
    vector: EmbeddingVector,
    expected_dimensions: int | None = None,
    strict: bool = False,
) -> ValidationResult:
    """Validate a single embedding vector.

    Args:
        vector: The embedding vector to validate.
        expected_dimensions: Expected dimensions (optional override).
        strict: If True, treat warnings as errors.

    Returns:
        ValidationResult with validation status.

    """
    validator = VectorValidator(expected_dimensions=expected_dimensions)
    return validator.validate(vector, strict=strict)
