"""Utility functions for safe embedding vector handling.

This module provides type-safe utilities for working with embedding vectors,
handling both Python lists and numpy arrays safely.

Issue #602: NumPy arrays have ambiguous truth values. Using `if array:` raises:
    ValueError: The truth value of an array with more than one element is ambiguous.

Solution: Always use explicit `is not None` checks for nullable arrays,
and use these utility functions for consistent, safe handling across the codebase.

"""

from typing import TYPE_CHECKING, Any, Union, cast

from app.core.logging import get_logger
from app.core.types import EmbeddingVector

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

logger = get_logger(__name__)

# Type alias for embedding inputs that may be list or numpy array
EmbeddingInput = Union[EmbeddingVector, "NDArray[np.float64]", None]

# Type alias for values from SQLAlchemy columns (unknown at static analysis time)
# has_embedding() handles these safely at runtime
EmbeddingLike = EmbeddingInput | Any


def has_embedding(value: EmbeddingLike) -> bool:
    """Check if an embedding value exists and is non-empty.

    Safe for both Python lists and numpy arrays. Handles the numpy
    ambiguous truth value error by using explicit None checks.

    Args:
        value: Embedding vector (list, numpy array, or None)

    Returns:
        True if value exists and has elements, False otherwise

    Example:
        >>> has_embedding(None)
        False
        >>> has_embedding([])
        False
        >>> has_embedding([0.1, 0.2])
        True
        >>> import numpy as np
        >>> has_embedding(np.array([0.1, 0.2]))
        True

    """
    if value is None:
        return False

    # Use len() which works for both lists and numpy arrays
    try:
        return len(value) > 0
    except TypeError:
        # Shouldn't happen, but be defensive
        logger.warning(
            "embedding_length_check_failed",
            value_type=type(value).__name__,
        )
        return False


def is_valid_embedding(
    value: EmbeddingInput,
    expected_dimensions: int = 1536,
) -> bool:
    """Check if an embedding is valid (exists and has correct dimensions).

    Args:
        value: Embedding vector to validate
        expected_dimensions: Expected vector dimensions (default: 1536 for OpenAI)

    Returns:
        True if embedding exists and has correct dimensions

    Example:
        >>> is_valid_embedding([0.1] * 1536)
        True
        >>> is_valid_embedding([0.1] * 768)  # Wrong dimensions
        False
        >>> is_valid_embedding(None)
        False

    """
    if not has_embedding(value):
        return False

    try:
        return len(value) == expected_dimensions  # type: ignore[arg-type]
    except TypeError:
        return False


def to_list(value: EmbeddingInput) -> EmbeddingVector | None:
    """Convert embedding to Python list, handling numpy arrays.

    Args:
        value: Embedding vector (list, numpy array, or None)

    Returns:
        Python list of floats, or None if input is None/empty

    Example:
        >>> to_list([0.1, 0.2])
        [0.1, 0.2]
        >>> import numpy as np
        >>> to_list(np.array([0.1, 0.2]))
        [0.1, 0.2]
        >>> to_list(None)
        None

    """
    if value is None:
        return None

    # Check for numpy array using hasattr (duck typing)
    if hasattr(value, "tolist"):
        return value.tolist()  # type: ignore[union-attr]

    # Already a list
    if isinstance(value, list):
        return value

    # Try to convert (value is Sized at this point, list() accepts Iterable)
    try:
        return list(value)
    except (TypeError, ValueError) as e:
        logger.warning(
            "embedding_to_list_failed",
            value_type=type(value).__name__,
            error=str(e),
        )
        return None


def to_numpy(value: EmbeddingInput) -> "NDArray[np.float64] | None":
    """Convert embedding to numpy array.

    Args:
        value: Embedding vector (list, numpy array, or None)

    Returns:
        Numpy array of float64, or None if input is None/empty

    Example:
        >>> to_numpy([0.1, 0.2])
        array([0.1, 0.2])
        >>> to_numpy(None)
        None

    """
    if value is None:
        return None

    import numpy as np

    # Convert to numpy array with float64 dtype
    # Works for both list and existing ndarray inputs
    try:
        result = np.array(value, dtype=np.float64)
        return cast("NDArray[np.float64]", result)
    except (TypeError, ValueError) as e:
        logger.warning(
            "embedding_to_numpy_failed",
            value_type=type(value).__name__,
            error=str(e),
        )
        return None


def normalize_embedding(value: EmbeddingInput) -> EmbeddingVector | None:
    """Normalize embedding vector to unit length (L2 norm = 1).

    Args:
        value: Embedding vector to normalize

    Returns:
        Normalized embedding as Python list, or None if invalid

    Example:
        >>> result = normalize_embedding([3.0, 4.0])
        >>> round(sum(x**2 for x in result), 6)  # L2 norm = 1
        1.0

    """
    if not has_embedding(value):
        return None

    import numpy as np

    # Convert to numpy for calculation
    array = to_numpy(value)
    if array is None:
        return None

    # Calculate magnitude
    magnitude = float(np.linalg.norm(array))

    # Guard against division by zero
    if magnitude <= 0:
        logger.warning(
            "embedding_zero_magnitude",
            magnitude=magnitude,
        )
        return None

    # Normalize and convert back to list
    return (array / magnitude).tolist()


def safe_bool_for_logging(value: EmbeddingLike) -> bool:
    """Get a safe boolean representation for logging purposes.

    Replacement for `bool(embedding)` in log statements which fails
    on numpy arrays.

    Args:
        value: Embedding value to check

    Returns:
        True if value exists (not None), False otherwise

    Example:
        >>> safe_bool_for_logging([0.1, 0.2])
        True
        >>> safe_bool_for_logging(None)
        False

    """
    return value is not None
