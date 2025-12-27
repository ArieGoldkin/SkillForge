"""Artifact repository for database operations.

This module implements the repository pattern for artifact database operations,
following the mandatory architecture pattern defined in cursor rules.
"""

import uuid
from typing import TYPE_CHECKING, Annotated, Protocol

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.branded_ids import AnalysisID, ArtifactID
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.artifact import Artifact
from app.db.session import get_db

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)


class IArtifactRepository(Protocol):
    """Protocol interface for artifact repository operations."""

    async def create_artifact(self, artifact_data: "Mapping[str, object]") -> Artifact:
        """Create a new artifact in the database."""
        ...

    async def get_artifact_by_id(self, artifact_id: ArtifactID) -> Artifact | None:
        """Get artifact by ID."""
        ...

    async def get_artifact_by_analysis_id(self, analysis_id: AnalysisID) -> Artifact | None:
        """Get artifact by analysis ID."""
        ...

    async def get_latest_artifact_by_analysis(self, analysis_id: AnalysisID) -> Artifact | None:
        """Get the most recent artifact for an analysis."""
        ...

    async def get_artifact_with_analysis(
        self, artifact_id: ArtifactID
    ) -> tuple[Artifact, Analysis] | None:
        """Get artifact with associated analysis in a single query."""
        ...

    async def increment_download_count(self, artifact_id: ArtifactID) -> None:
        """Increment download count for an artifact."""
        ...

    async def list_artifacts(
        self, page: int = 1, limit: int = 20, include_deleted: bool = False
    ) -> tuple[list[Artifact], int]:
        """List artifacts with pagination."""
        ...

    async def soft_delete(self, artifact_id: ArtifactID) -> bool:
        """Soft delete an artifact."""
        ...

    async def restore(self, artifact_id: ArtifactID) -> bool:
        """Restore a soft-deleted artifact."""
        ...

    async def generate_etag(self, artifact_id: ArtifactID) -> str | None:
        """Generate ETag for caching."""
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
        trace_id_value = artifact_data.get("trace_id")
        artifact = Artifact(
            id=artifact_data.get("id", uuid.uuid4()),
            analysis_id=uuid.UUID(str(artifact_data["analysis_id"])),
            markdown_content=str(artifact_data["markdown_content"]),
            version=int(version_value) if isinstance(version_value, (int, str)) else 1,
            artifact_metadata=artifact_data.get("artifact_metadata"),
            download_count=(
                int(download_count_value) if isinstance(download_count_value, (int, str)) else 0
            ),
            trace_id=str(trace_id_value) if trace_id_value else None,
        )
        self.session.add(artifact)
        await self.session.commit()
        await self.session.refresh(artifact)

        logger.info(
            "artifact_created",
            artifact_id=str(artifact.id),
            analysis_id=str(artifact.analysis_id),
            trace_id=artifact.trace_id,
        )

        return artifact

    async def get_artifact_by_id(self, artifact_id: ArtifactID) -> Artifact | None:
        """Get artifact by ID."""
        result = await self.session.execute(select(Artifact).where(Artifact.id == artifact_id))
        return result.scalar_one_or_none()

    async def get_artifact_by_analysis_id(self, analysis_id: AnalysisID) -> Artifact | None:
        """Get artifact by analysis ID."""
        result = await self.session.execute(
            select(Artifact).where(Artifact.analysis_id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_latest_artifact_by_analysis(self, analysis_id: AnalysisID) -> Artifact | None:
        """Get the most recent artifact for an analysis."""
        result = await self.session.execute(
            select(Artifact)
            .where(Artifact.analysis_id == analysis_id)
            .order_by(Artifact.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_artifact_with_analysis(
        self, artifact_id: ArtifactID
    ) -> tuple[Artifact, Analysis] | None:
        """Get artifact with associated analysis in a single query."""
        result = await self.session.execute(
            select(Artifact, Analysis)
            .join(Analysis, Artifact.analysis_id == Analysis.id)
            .where(Artifact.id == artifact_id)
        )
        row = result.one_or_none()
        return (row[0], row[1]) if row else None

    async def increment_download_count(self, artifact_id: ArtifactID) -> None:
        """Increment download count atomically."""
        from sqlalchemy import update

        await self.session.execute(
            update(Artifact)
            .where(Artifact.id == artifact_id)
            .values(download_count=Artifact.download_count + 1)
        )
        await self.session.commit()

    async def list_artifacts(
        self, page: int = 1, limit: int = 20, include_deleted: bool = False
    ) -> tuple[list[Artifact], int]:
        """List artifacts with pagination."""
        from sqlalchemy import func

        query = select(Artifact)
        count_query = select(func.count(Artifact.id))

        if not include_deleted:
            query = query.where(Artifact.is_deleted == False)  # noqa: E712
            count_query = count_query.where(Artifact.is_deleted == False)  # noqa: E712

        # Get total count
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * limit
        query = query.order_by(Artifact.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        artifacts = list(result.scalars().all())

        return artifacts, total

    async def soft_delete(self, artifact_id: ArtifactID) -> bool:
        """Soft delete an artifact."""
        from datetime import UTC, datetime

        artifact = await self.get_artifact_by_id(artifact_id)
        if not artifact or artifact.is_deleted:
            return False

        artifact.is_deleted = True
        artifact.deleted_at = datetime.now(UTC)
        await self.session.commit()
        return True

    async def restore(self, artifact_id: ArtifactID) -> bool:
        """Restore a soft-deleted artifact."""
        result = await self.session.execute(select(Artifact).where(Artifact.id == artifact_id))
        artifact = result.scalar_one_or_none()
        if not artifact or not artifact.is_deleted:
            return False

        artifact.is_deleted = False
        artifact.deleted_at = None
        await self.session.commit()
        return True

    async def generate_etag(self, artifact_id: ArtifactID) -> str | None:
        """Generate ETag for caching."""
        import hashlib

        artifact = await self.get_artifact_by_id(artifact_id)
        if not artifact:
            return None

        # Use updated_at or created_at + id for ETag
        timestamp = artifact.updated_at or artifact.created_at
        etag_source = f"{artifact_id}-{timestamp.isoformat() if timestamp else ''}"
        return hashlib.md5(etag_source.encode()).hexdigest()  # noqa: S324


def get_artifact_repository(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IArtifactRepository:
    """Dependency injection function for artifact repository."""
    return ArtifactRepository(session=db)
