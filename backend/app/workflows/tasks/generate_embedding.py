"""Embedding generation task for workflow."""

from langsmith import get_current_run_tree

from app.core.agent_config import get_stage_name
from app.core.config import settings
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.core.types import AnalysisID, EmbeddingVector
from app.services.chunking.chunker import ChunkText
from app.services.chunking.summaries import SummaryChunk
from app.services.embeddings import EmbeddingService
from app.services.sse_helpers import emit_streaming_event

logger = get_logger(__name__)


@robust_traceable(
    name="generate_embedding",
    run_type="tool",
    tags=["workflow", "node", "embedding"],
    metadata={
        "environment": settings.ENVIRONMENT,
        "workflow_type": "analysis",
        "component": "task",
        "task_type": "embedding",
    },
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

    # Runtime metadata updates
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.metadata["analysis_id"] = str(analysis_id)
    except Exception:  # noqa: BLE001 - LangSmith may not be available, catch all to continue
        # LangSmith not available or not in trace context - continue
        pass

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


async def generate_embeddings_batch(
    payloads: list[ChunkText | SummaryChunk],
    analysis_id: AnalysisID,
    normalize: bool = True,
) -> list[tuple[EmbeddingVector, dict]]:
    """Batch-generate embeddings for a list of chunk payloads."""
    if not payloads:
        return []

    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage=get_stage_name("embedding"),
        status="running",
    )

    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.metadata["analysis_id"] = str(analysis_id)
    except Exception:
        pass

    embedding_service = EmbeddingService()
    results: list[tuple[EmbeddingVector, dict]] = []

    try:
        for chunk in payloads:
            embedding_result = await embedding_service.generate_embedding(chunk.text, normalize=normalize)
            results.append((list(embedding_result), chunk.__dict__))

        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage=get_stage_name("embedding"),
            status="complete",
        )

        logger.info(
            "workflow_embedding_batch_complete",
            count=len(results),
            normalize=normalize,
        )
    except Exception as e:
        await emit_streaming_event(
            "error",
            analysis_id=analysis_id,
            stage=get_stage_name("embedding"),
            status="failed",
            error=str(e),
            error_code="EMBEDDING_FAILED",
        )
        logger.error(
            "workflow_embedding_batch_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        await embedding_service.close()

    return results
