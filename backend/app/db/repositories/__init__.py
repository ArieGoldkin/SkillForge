"""Repository interfaces and implementations for database access.

This module provides repository pattern implementations following the
mandatory architecture pattern defined in cursor rules.
"""

from app.db.repositories.analysis_repository import (
    AnalysisRepository,
    IAnalysisRepository,
    get_analysis_repository,
)
from app.db.repositories.artifact_repository import (
    ArtifactRepository,
    IArtifactRepository,
    get_artifact_repository,
)
from app.db.repositories.library_repository import (
    ILibraryRepository,
    LibraryRepository,
    get_library_repository,
)

__all__ = [
    "AnalysisRepository",
    "ArtifactRepository",
    "IAnalysisRepository",
    "IArtifactRepository",
    "ILibraryRepository",
    "LibraryRepository",
    "get_analysis_repository",
    "get_artifact_repository",
    "get_library_repository",
]
