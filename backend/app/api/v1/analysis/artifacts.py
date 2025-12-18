"""Artifact download endpoints."""

import uuid
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from app.core.logging import get_logger
from app.db.repositories.artifact_repository import IArtifactRepository, get_artifact_repository
from app.domains.analysis.schemas.api import ArtifactMetadataResponse
from app.domains.analysis.workflows.tasks.artifact_helpers import generate_filename

router = APIRouter(tags=["artifacts"])
logger = get_logger(__name__)


@router.get("/analyze/{analysis_id}/artifact")
async def get_artifact_by_analysis(
    analysis_id: uuid.UUID,
    repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
) -> ArtifactMetadataResponse:
    """Retrieve the latest artifact for an analysis (metadata + markdown)."""
    artifact = await repo.get_latest_artifact_by_analysis(analysis_id)

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No artifact found for analysis {analysis_id}",
        )

    return ArtifactMetadataResponse(
        artifact_id=str(artifact.id),
        analysis_id=str(artifact.analysis_id),
        markdown_content=str(cast(str | None, artifact.markdown_content) or ""),
        artifact_metadata=cast(dict[str, object] | None, artifact.artifact_metadata)
        if artifact.artifact_metadata
        else None,
        created_at=artifact.created_at.isoformat() if artifact.created_at else "",
    )


@router.get("/artifacts/{artifact_id}")
async def get_artifact_by_id(
    artifact_id: uuid.UUID,
    repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
) -> ArtifactMetadataResponse:
    """Retrieve artifact metadata by artifact ID.

    Args:
        artifact_id: UUID of the artifact to retrieve
        repo: Artifact repository dependency

    Returns:
        Artifact metadata including markdown content

    Raises:
        HTTPException: 404 if artifact not found

    """
    artifact = await repo.get_artifact_by_id(artifact_id)

    if not artifact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact {artifact_id} not found",
        )

    return ArtifactMetadataResponse(
        artifact_id=str(artifact.id),
        analysis_id=str(artifact.analysis_id),
        markdown_content=str(cast(str | None, artifact.markdown_content) or ""),
        artifact_metadata=cast(dict[str, object] | None, artifact.artifact_metadata)
        if artifact.artifact_metadata
        else None,
        created_at=artifact.created_at.isoformat() if artifact.created_at else "",
    )


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: uuid.UUID,
    repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
) -> Response:
    """Download artifact as markdown file.

    Returns the artifact markdown content with proper headers for file download.
    Increments the download_count for analytics.

    Args:
        artifact_id: UUID of the artifact to download
        repo: Artifact repository dependency

    Returns:
        Response with markdown content and Content-Disposition header

    Raises:
        HTTPException: 404 if artifact not found
        HTTPException: 500 if database operation fails

    """
    try:
        # Get artifact with analysis in optimized single query
        result = await repo.get_artifact_with_analysis(artifact_id)

        if not result:
            logger.warning(
                "artifact_download_not_found",
                artifact_id=str(artifact_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found",
            )

        artifact, analysis = result

        # Extract title from analysis metadata
        title: str | None = None
        if analysis.extraction_metadata:  # type: ignore[attr-defined]
            extraction_metadata = analysis.extraction_metadata  # type: ignore[attr-defined]
            if isinstance(extraction_metadata, dict):
                title = extraction_metadata.get("title")  # type: ignore[assignment]

        # Generate filename
        filename = generate_filename(title, str(artifact.analysis_id))

        # Increment download_count using repository
        await repo.increment_download_count(artifact_id)

        # Get updated artifact for logging
        updated_artifact = await repo.get_artifact_by_id(artifact_id)

        download_count = updated_artifact.download_count if updated_artifact else 0
        logger.info(
            "artifact_downloaded",
            artifact_id=str(artifact_id),
            analysis_id=str(artifact.analysis_id),
            download_count=download_count,
        )

        # Return markdown with proper headers
        return Response(
            content=artifact.markdown_content,
            media_type="text/markdown",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "artifact_download_failed",
            artifact_id=str(artifact_id),
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download artifact",
        ) from e
