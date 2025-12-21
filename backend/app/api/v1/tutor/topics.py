"""Topics endpoint for tutoring modal.

Provides available topics extracted from analysis artifacts for user selection
before starting a tutoring session.
"""

import uuid
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.logging import get_logger
from app.db.repositories.analysis_repository import (
    IAnalysisRepository,
    get_analysis_repository,
)
from app.db.repositories.artifact_repository import (
    IArtifactRepository,
    get_artifact_repository,
)
from app.domains.tutor.schemas.api import TopicsResponse, TutoringTopic

router = APIRouter()
logger = get_logger(__name__)


def _extract_topics_from_metadata(
    artifact_metadata: dict[str, Any] | None,
) -> list[TutoringTopic]:
    """Extract and normalize topics from artifact metadata.

    Args:
        artifact_metadata: Raw artifact metadata dictionary

    Returns:
        List of TutoringTopic objects

    """
    if not artifact_metadata:
        return []

    raw_topics = artifact_metadata.get("topics", [])

    # Handle both string list and dict list formats
    topics: list[TutoringTopic] = []
    for i, topic in enumerate(raw_topics):
        if isinstance(topic, str):
            # Simple string topic
            topics.append(
                TutoringTopic(
                    id=f"topic-{i}",
                    name=topic,
                    description="",
                    complexity="intermediate",
                )
            )
        elif isinstance(topic, dict):
            # Structured topic with metadata
            topics.append(
                TutoringTopic(
                    id=topic.get("id", f"topic-{i}"),
                    name=topic.get("name", topic.get("title", "Unknown")),
                    description=topic.get("description", ""),
                    complexity=topic.get("complexity", "intermediate"),
                )
            )

    return topics


@router.get("/tutor/analyses/{analysis_id}/topics")
async def get_topics_for_analysis(
    analysis_id: uuid.UUID,
    analysis_repo: Annotated[IAnalysisRepository, Depends(get_analysis_repository)],
    artifact_repo: Annotated[IArtifactRepository, Depends(get_artifact_repository)],
) -> TopicsResponse:
    """Get available topics from an analysis for tutoring.

    Extracts topics from the analysis artifact's metadata. Topics are
    generated during content analysis and stored in artifact_metadata.topics.

    Args:
        analysis_id: Analysis UUID to get topics from
        analysis_repo: Analysis repository dependency
        artifact_repo: Artifact repository dependency

    Returns:
        TopicsResponse with analysis info and list of topics

    Raises:
        HTTPException: 404 if analysis not found

    """
    # Get analysis for title
    analysis = await analysis_repo.get_by_id(analysis_id)
    if not analysis:
        logger.warning(
            "topics_analysis_not_found",
            analysis_id=str(analysis_id),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis {analysis_id} not found",
        )

    # Get latest artifact for topics
    artifact = await artifact_repo.get_latest_artifact_by_analysis(analysis_id)

    # Extract topics from artifact metadata (if available)
    # Cast artifact_metadata since SQLAlchemy Column types confuse the type checker
    topics: list[TutoringTopic] = []
    if artifact and artifact.artifact_metadata:
        metadata = cast(dict[str, Any] | None, artifact.artifact_metadata)
        topics = _extract_topics_from_metadata(metadata)

    # Cast analysis.title since SQLAlchemy Column types confuse the type checker
    analysis_title = str(analysis.title) if analysis.title else "Untitled Analysis"

    logger.info(
        "topics_retrieved",
        analysis_id=str(analysis_id),
        analysis_title=analysis_title,
        topic_count=len(topics),
        has_artifact=artifact is not None,
    )

    return TopicsResponse(
        analysis_id=analysis_id,
        analysis_title=analysis_title,
        topics=topics,
    )
