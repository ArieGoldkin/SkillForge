"""Workflow task functions for content analysis.

This module contains individual task functions that are orchestrated by
the main analysis workflow. Each task is a self-contained unit of work
that can be executed independently and emits SSE events for progress tracking.

Note: These functions are decorated with @task in analysis.py after import
to avoid circular dependencies. The task() function can be used as a decorator
factory to wrap functions.
"""

from app.core.logging import get_logger
from app.core.types import AnalysisID, EmbeddingVector
from app.services.embeddings import EmbeddingService
from app.services.extraction.jina_reader import JinaReader
from app.services.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


async def extract_content(url: str, analysis_id: AnalysisID) -> dict:
    """Extract content from URL using JinaReader.

    Args:
        url: The URL to extract content from
        analysis_id: Unique identifier for this analysis

    Returns:
        Dictionary with 'raw_content' and 'extraction_metadata'

    Raises:
        JinaReaderError: If extraction fails

    """
    # Emit SSE event: extraction started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
    )

    logger.info("workflow_extraction_started", analysis_id=analysis_id, url=url)
    jina = JinaReader()
    try:
        extracted = await jina.extract_article(url)

        # Emit SSE event: extraction complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="extraction",
            status="complete",
            word_count=extracted.get("word_count", 0),
        )

        logger.info(
            "workflow_extraction_complete",
            analysis_id=analysis_id,
            url=url,
            word_count=extracted.get("word_count", 0),
        )
        return {
            "raw_content": extracted["content"],
            "extraction_metadata": extracted["metadata"],
        }
    except Exception as e:
        # Emit SSE event: extraction failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage="extraction",
            status="failed",
            error=str(e),
            error_code="EXTRACTION_FAILED",
        )
        logger.error(
            "workflow_extraction_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        await jina.close()


async def generate_embedding(content: str, analysis_id: AnalysisID) -> EmbeddingVector:
    """Generate embedding vector for content.

    Args:
        content: The text content to embed
        analysis_id: Unique identifier for this analysis

    Returns:
        List of floats representing the embedding vector

    Raises:
        EmbeddingError: If embedding generation fails

    """
    # Emit SSE event: embedding generation started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="embedding",
        status="running",
    )

    logger.info("workflow_embedding_started", content_length=len(content))
    embedding_service = EmbeddingService()
    try:
        embedding_result = await embedding_service.generate_embedding(content)
        embedding: EmbeddingVector = list(embedding_result)

        # Emit SSE event: embedding complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="embedding",
            status="complete",
        )

        logger.info(
            "workflow_embedding_complete",
            embedding_dimensions=len(embedding),
        )
    except Exception as e:
        # Emit SSE event: embedding failed
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage="embedding",
            status="failed",
            error=str(e),
            error_code="EMBEDDING_FAILED",
        )
        logger.error(
            "workflow_embedding_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        await embedding_service.close()

    return embedding
