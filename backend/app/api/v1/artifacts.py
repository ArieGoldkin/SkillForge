"""Artifact download endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.analysis import Analysis
from app.models.artifact import Artifact
from app.workflows.tasks.artifact_helpers import generate_filename

router = APIRouter(tags=["artifacts"])
logger = get_logger(__name__)


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(
    artifact_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Download artifact as markdown file.

    Returns the artifact markdown content with proper headers for file download.
    Increments the download_count for analytics.

    Args:
        artifact_id: UUID of the artifact to download
        db: Database session dependency

    Returns:
        Response with markdown content and Content-Disposition header

    Raises:
        HTTPException: 404 if artifact not found
        HTTPException: 500 if database operation fails

    """
    try:
        # Get artifact from database
        result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
        artifact = result.scalar_one_or_none()

        if not artifact:
            logger.warning(
                "artifact_download_not_found",
                artifact_id=str(artifact_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artifact {artifact_id} not found",
            )

        # Get analysis for title (for filename generation)
        result = await db.execute(select(Analysis).where(Analysis.id == artifact.analysis_id))
        analysis = result.scalar_one_or_none()
        title: str | None = None
        if analysis is not None:
            # extraction_metadata is JSONB column, type checker needs help
            extraction_metadata = analysis.extraction_metadata  # type: ignore[attr-defined]
            if isinstance(extraction_metadata, dict):
                title = extraction_metadata.get("title")  # type: ignore[assignment]

        # Generate filename
        filename = generate_filename(title, str(artifact.analysis_id))

        # Increment download_count
        artifact.download_count = artifact.download_count + 1  # type: ignore[assignment]
        await db.commit()

        logger.info(
            "artifact_downloaded",
            artifact_id=str(artifact_id),
            analysis_id=str(artifact.analysis_id),
            download_count=artifact.download_count,
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
