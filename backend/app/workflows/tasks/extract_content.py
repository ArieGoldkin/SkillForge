"""Content extraction task for workflow."""

from langsmith import traceable

from app.core.logging import get_logger
from app.core.types import AnalysisID
from app.services.extraction.jina_reader import JinaReader
from app.services.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


@traceable(
    name="extract_content",
    run_type="tool",
    tags=["workflow", "node"],
)
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


