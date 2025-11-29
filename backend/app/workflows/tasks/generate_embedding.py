"""Embedding generation task for workflow."""

from langsmith import traceable

from app.core.agent_config import get_stage_name
from app.core.logging import get_logger
from app.core.types import AnalysisID, EmbeddingVector
from app.services.embeddings import EmbeddingService
from app.services.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


@traceable(
    name="generate_embedding",
    run_type="tool",
    tags=["workflow", "node"],
)
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
        stage=get_stage_name("embedding"),
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
            stage=get_stage_name("embedding"),
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
            stage=get_stage_name("embedding"),
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


