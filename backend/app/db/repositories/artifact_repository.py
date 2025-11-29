"""Artifact repository for database operations.

This module implements the repository pattern for artifact database operations,
following the mandatory architecture pattern defined in cursor rules.
"""

import uuid
from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.artifact import Artifact

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)


class IArtifactRepository(Protocol):
    """Protocol interface for artifact repository operations."""

    async def create_artifact(self, artifact_data: "Mapping[str, object]") -> Artifact:
        """Create a new artifact in the database."""
        ...

    async def get_artifact_by_id(self, artifact_id: uuid.UUID) -> Artifact | None:
        """Get artifact by ID."""
        ...

    async def get_artifact_with_analysis(
        self, artifact_id: uuid.UUID
    ) -> tuple[Artifact, Analysis] | None:
        """Get artifact with associated analysis in a single query."""
        ...

    async def increment_download_count(self, artifact_id: uuid.UUID) -> None:
        """Increment download count for an artifact."""
        ...


class ArtifactRepository:
    """Repository implementation for artifact database operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: Async database session

        """
        self.session = session

    async def create_artifact(self, artifact_data: "Mapping[str, object]") -> Artifact:
        """Create a new artifact in the database."""
        version_value = artifact_data.get("version", 1)
        download_count_value = artifact_data.get("download_count", 0)
        artifact = Artifact(
            id=artifact_data.get("id", uuid.uuid4()),
            analysis_id=uuid.UUID(str(artifact_data["analysis_id"])),
            markdown_content=str(artifact_data["markdown_content"]),
            version=int(version_value) if isinstance(version_value, (int, str)) else 1,
            artifact_metadata=artifact_data.get("artifact_metadata"),
            download_count=(
                int(download_count_value) if isinstance(download_count_value, (int, str)) else 0
            ),
        )
        self.session.add(artifact)
        await self.session.commit()
        await self.session.refresh(artifact)

        logger.info(
            "artifact_created",
            artifact_id=str(artifact.id),
            analysis_id=str(artifact.analysis_id),
        )

        return artifact

    async def get_artifact_by_id(self, artifact_id: uuid.UUID) -> Artifact | None:
        """Get artifact by ID."""
        result = await self.session.execute(select(Artifact).where(Artifact.id == artifact_id))
        return result.scalar_one_or_none()

    async def get_artifact_with_analysis(
        self, artifact_id: uuid.UUID
    ) -> tuple[Artifact, Analysis] | None:
        """Get artifact with associated analysis in a single query."""
        result = await self.session.execute(
            select(Artifact, Analysis)
            .join(Analysis, Artifact.analysis_id == Analysis.id)
            .where(Artifact.id == artifact_id)
        )
        row = result.one_or_none()
        return (row[0], row[1]) if row else None

    async def increment_download_count(self, artifact_id: uuid.UUID) -> None:
        """Increment download count for an artifact."""
        artifact = await self.get_artifact_by_id(artifact_id)
        if artifact:
            artifact.download_count = artifact.download_count + 1  # type: ignore[assignment]
            await self.session.commit()


def get_artifact_repository(
    db: Annotated[AsyncSession, Depends(get_db)],  # noqa: B008
) -> IArtifactRepository:
    """Dependency injection function for artifact repository."""
    return ArtifactRepository(session=db)
