"""Utility functions for common operations across the application."""

import uuid
from uuid import UUID

from app.core.constants import UUID_NAMESPACE_DNS


def normalize_analysis_id_to_uuid(analysis_id: str | UUID) -> UUID:
    """Normalize analysis_id to UUID, handling all input types.

    Converts analysis_id to UUID, supporting:
    - Valid UUID strings: "123e4567-e89b-12d3-a456-426614174000"
    - UUID objects: UUID("123e4567-...")
    - Non-UUID strings: "dev-test-opus-4-5" (converted deterministically)

    This function ensures consistent UUID handling throughout the application,
    allowing both production UUIDs and development/testing non-UUID strings to
    work seamlessly.

    Args:
        analysis_id: String or UUID object to normalize

    Returns:
        UUID object (same if input is UUID, converted if string)

    Examples:
        >>> normalize_analysis_id_to_uuid("123e4567-e89b-12d3-a456-426614174000")
        UUID('123e4567-e89b-12d3-a456-426614174000')
        >>> normalize_analysis_id_to_uuid(UUID("123e4567-e89b-12d3-a456-426614174000"))
        UUID('123e4567-e89b-12d3-a456-426614174000')
        >>> normalize_analysis_id_to_uuid("dev-test")
        UUID('...')  # Deterministic UUID from string

    """
    # If already UUID, return as-is
    if isinstance(analysis_id, UUID):
        return analysis_id

    # Try to parse as UUID string
    try:
        return UUID(str(analysis_id))
    except ValueError:
        # Not a valid UUID - generate deterministically using DNS namespace
        # This allows dev/testing with non-UUID strings while maintaining
        # consistency (same string always produces same UUID)
        namespace = UUID(UUID_NAMESPACE_DNS)
        return uuid.uuid5(namespace, str(analysis_id))



