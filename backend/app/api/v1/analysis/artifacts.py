"""Artifact download endpoints."""

import uuid
from math import ceil
from typing import Annotated

import orjson
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status
from fastapi.responses import Response

from app.api.schemas.errors import ErrorResponse
from app.core.logging import get_logger
from app.db.repositories.artifact_repository import IArtifactRepository, get_artifact_repository
from app.domains.analysis.schemas.api import ArtifactMetadataResponse
from app.domains.analysis.workflows.tasks.artifact_helpers import generate_filename

router = APIRouter(tags=["artifacts"])
logger = get_logger(__name__)


@router.get(
    "/analyze/{analysis_id}/artifact",
    responses={
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_artifact_by_analysis(
    analysis_id: Annotated[uuid.UUID, Path(description="Analysis UUID")],
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
        markdown_content=artifact.markdown_content or "",
        artifact_metadata=artifact.artifact_metadata if artifact.artifact_metadata else None,
        trace_id=artifact.trace_id if artifact.trace_id else None,
        created_at=artifact.created_at.isoformat() if artifact.created_at else "",
    )


@router.get(
    "/artifacts/{artifact_id}",
    responses={
        200: {"description": "Artifact found"},
        304: {"description": "Not modified"},
        404: {"model": ErrorResponse, "description": "Artifact not found"},
    },
)
async def get_artifact_by_id(
    artifact_id: Annotated[uuid.UUID, Path(description="Artifact UUID")],
    repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
    if_none_match: Annotated[str | None, Header(alias="If-None-Match")] = None,
) -> Response:
    """Retrieve artifact with caching support."""
    artifact = await repo.get_artifact_by_id(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact {artifact_id} not found")

    etag = await repo.generate_etag(artifact_id)

    # Check conditional GET
    if if_none_match and etag and if_none_match.strip('"') == etag:
        return Response(
            status_code=304,
            headers={"ETag": f'"{etag}"', "Cache-Control": "public, max-age=3600"},
        )

    response_data = ArtifactMetadataResponse(
        artifact_id=str(artifact.id),
        analysis_id=str(artifact.analysis_id),
        markdown_content=artifact.markdown_content or "",
        artifact_metadata=artifact.artifact_metadata,
        trace_id=artifact.trace_id,
        download_count=artifact.download_count or 0,
        created_at=artifact.created_at.isoformat() if artifact.created_at else "",
    )

    return Response(
        content=orjson.dumps(response_data.model_dump()),
        media_type="application/json",
        headers={
            "ETag": f'"{etag}"' if etag else "",
            "Cache-Control": "public, max-age=3600, must-revalidate",
            "Vary": "Accept-Encoding",
        },
    )


@router.get(
    "/artifacts/{artifact_id}/download",
    response_class=Response,
    responses={
        200: {
            "description": "Artifact markdown file",
            "content": {"text/markdown": {}},
        },
        404: {"model": ErrorResponse, "description": "Artifact not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def download_artifact(
    artifact_id: Annotated[uuid.UUID, Path(description="Artifact UUID")],
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


@router.get("/artifacts")
async def list_artifacts(
    repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    """List artifacts with pagination."""
    artifacts, total = await repo.list_artifacts(page=page, limit=limit)
    pages = ceil(total / limit) if total > 0 else 0

    items = [
        {
            "artifact_id": str(a.id),
            "analysis_id": str(a.analysis_id),
            "created_at": a.created_at.isoformat() if a.created_at else "",
            "download_count": a.download_count or 0,
        }
        for a in artifacts
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
        "has_prev": page > 1,
    }


@router.delete("/artifacts/{artifact_id}")
async def delete_artifact(
    artifact_id: Annotated[uuid.UUID, Path(description="Artifact UUID")],
    repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
) -> dict:
    """Soft delete an artifact."""
    deleted = await repo.soft_delete(artifact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Artifact not found or already deleted")

    logger.info("artifact_deleted", artifact_id=str(artifact_id))
    return {"status": "deleted", "artifact_id": str(artifact_id)}
