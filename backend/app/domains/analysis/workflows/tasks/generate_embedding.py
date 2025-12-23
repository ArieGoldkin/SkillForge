"""Embedding generation task for workflow."""

from app.core.agent_config import get_stage_name
from app.core.config import settings
from app.core.exceptions import WorkflowStageError
from app.core.logging import get_logger
from app.core.tracing import robust_traceable
from app.core.types import AnalysisID, EmbeddingVector
from app.shared.services.chunking.chunker import ChunkText
from app.shared.services.chunking.summaries import SummaryChunk
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.messaging.sse_helpers import (
    emit_error_event,
    emit_streaming_event,
)

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
        from app.core.tracing import update_current_trace

        update_current_trace(
            metadata={"analysis_id": str(analysis_id)},
            session_id=f"analysis-{analysis_id}",
            user_id="anonymous",
        )
    except Exception:  # noqa: S110, BLE001 - Langfuse may not be available
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
        # Record error to database before emitting events
        from app.domains.analysis.constants.error_codes import EMBEDDING_FAILED
        from app.domains.analysis.services.persistence.error_recorder import error_recorder

        try:
            await error_recorder.record(
                analysis_id=str(analysis_id),
                error_code=EMBEDDING_FAILED,
                error_message=str(e),
                stage="embedding",
            )
        except Exception:  # noqa: S110, BLE001
            pass  # Don't let error recording break the flow

        # Emit error event using standardized helper
        stage_name = get_stage_name("embedding")
        await emit_error_event(
            analysis_id=analysis_id,
            stage=stage_name,
            error=str(e),
            error_code="EMBEDDING_FAILED",
        )
        logger.error(
            "workflow_embedding_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        # Wrap exception with stage context for orchestrator-level error handling
        raise WorkflowStageError(
            stage=stage_name,
            original_exception=e,
            message=f"Embedding generation failed: {e}",
        ) from e
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
        from app.core.tracing import update_current_trace

        update_current_trace(
            metadata={"analysis_id": str(analysis_id)},
            session_id=f"analysis-{analysis_id}",
            user_id="anonymous",
        )
    except Exception:  # noqa: S110, BLE001 - Langfuse may not be available
        pass

    embedding_service = EmbeddingService()
    results: list[tuple[EmbeddingVector, dict]] = []

    try:
        for chunk in payloads:
            embedding_result = await embedding_service.generate_embedding(
                chunk.text, normalize=normalize
            )
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
        # Record error to database before emitting events
        from app.domains.analysis.constants.error_codes import EMBEDDING_FAILED
        from app.domains.analysis.services.persistence.error_recorder import error_recorder

        try:
            await error_recorder.record(
                analysis_id=str(analysis_id),
                error_code=EMBEDDING_FAILED,
                error_message=str(e),
                stage="embedding",
            )
        except Exception:  # noqa: S110, BLE001
            pass  # Don't let error recording break the flow

        # Emit error event using standardized helper
        stage_name = get_stage_name("embedding")
        await emit_error_event(
            analysis_id=analysis_id,
            stage=stage_name,
            error=str(e),
            error_code="EMBEDDING_FAILED",
        )
        logger.error(
            "workflow_embedding_batch_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        # Wrap exception with stage context for orchestrator-level error handling
        raise WorkflowStageError(
            stage=stage_name,
            original_exception=e,
            message=f"Batch embedding generation failed: {e}",
        ) from e
    finally:
        await embedding_service.close()

    return results
