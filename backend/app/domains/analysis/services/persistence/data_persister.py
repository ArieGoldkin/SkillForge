"""Data persistence service for analysis records."""

import uuid

from sqlalchemy import select

from app.core.constants import DEFAULT_TITLE
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal

logger = get_logger(__name__)


class DataPersister:
    """Service for persisting workflow results to analysis records."""

    async def persist(self, analysis_id: uuid.UUID, workflow_result: dict) -> bool:
        """Persist workflow results to the analysis record.

        Updates the analysis with extracted content, title, and embedding data.
        This enables full-text search (via search_vector trigger) and semantic search.

        Args:
            analysis_id: UUID of the analysis to update
            workflow_result: Dictionary containing workflow state with:
                - raw_content: Extracted text content
                - extraction_metadata: Metadata dict with title, word_count, etc.
                - content_embedding: Vector embedding (1536 dimensions)

        Returns:
            bool: True if data was persisted successfully, False otherwise

        Raises:
            RuntimeError: If persistence fails due to database error

        """
        try:
            async with AsyncSessionLocal() as db_session:
                result = await db_session.execute(
                    select(Analysis).where(Analysis.id == analysis_id)
                )
                analysis = result.scalar_one_or_none()

                if not analysis:
                    logger.warning(
                        "persist_analysis_data_not_found",
                        analysis_id=str(analysis_id),
                    )
                    return False

                # Persist raw content
                raw_content = workflow_result.get("raw_content")
                if raw_content:
                    analysis.raw_content = raw_content  # type: ignore[assignment]
                else:
                    logger.warning(
                        "persist_missing_raw_content",
                        analysis_id=str(analysis_id),
                        message="Workflow result missing raw_content",
                    )

                # Extract and persist title from extraction_metadata
                extraction_metadata = workflow_result.get("extraction_metadata")
                if extraction_metadata and isinstance(extraction_metadata, dict):
                    analysis.extraction_metadata = extraction_metadata  # type: ignore[assignment]
                    title = extraction_metadata.get("title")
                    if title:
                        analysis.title = title  # type: ignore[assignment]
                    else:
                        # Always persist a title - use default if extraction failed
                        analysis.title = DEFAULT_TITLE  # type: ignore[assignment]
                        logger.warning(
                            "persist_default_title",
                            analysis_id=str(analysis_id),
                            message=f"Title missing, using default: {DEFAULT_TITLE}",
                        )
                else:
                    logger.warning(
                        "persist_missing_extraction_metadata",
                        analysis_id=str(analysis_id),
                        message="Workflow result missing extraction_metadata",
                    )

                # Persist content embedding
                content_embedding = workflow_result.get("content_embedding")
                if content_embedding:
                    analysis.content_embedding = content_embedding  # type: ignore[assignment]
                else:
                    logger.warning(
                        "persist_missing_content_embedding",
                        analysis_id=str(analysis_id),
                        message="Workflow result missing content_embedding",
                    )

                await db_session.commit()

                logger.info(
                    "persist_analysis_data_success",
                    analysis_id=str(analysis_id),
                    has_raw_content=raw_content is not None,
                    has_title=analysis.title is not None,
                    has_embedding=content_embedding is not None,
                    raw_content_length=len(raw_content) if raw_content else 0,
                )
                return True

        except Exception as db_error:
            logger.error(
                "persist_analysis_data_failed",
                analysis_id=str(analysis_id),
                error=str(db_error),
                exc_info=True,
            )
            error_message = f"Failed to persist analysis data: {db_error}"
            raise RuntimeError(error_message) from db_error
