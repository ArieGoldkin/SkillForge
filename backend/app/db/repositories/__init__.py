"""Repository interfaces and implementations for database access.

This module provides repository pattern implementations following the
mandatory architecture pattern defined in cursor rules.
"""

from app.db.repositories.artifact_repository import (
    ArtifactRepository,
    IArtifactRepository,
    get_artifact_repository,
)

__all__ = [
    "IArtifactRepository",
    "ArtifactRepository",
    "get_artifact_repository",
]
