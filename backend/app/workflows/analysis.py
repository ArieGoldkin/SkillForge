"""LangGraph analysis workflow implementation.

Implements the main analysis workflow using LangGraph v1.0 Functional API.
Workflow extracts content, generates embeddings, and emits SSE progress events.
"""

import asyncio
from typing import TypedDict

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embeddings import embedding_service
from app.services.extraction.jina_reader import JinaReader
from app.services.sse_helpers import emit_streaming_event

logger = get_logger(__name__)

# Try to import LangGraph, fallback to mock if not available
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.func import entrypoint, task

    LANGGRAPH_AVAILABLE = True
except ImportError:
    # Fallback for development when LangGraph not installed
    LANGGRAPH_AVAILABLE = False
    logger.warning("langgraph_not_installed", message="Using mock implementation")

    # Mock decorators for development
    class MockFuture:
        """Mock future object that wraps async function results."""

        def __init__(self, coro):
            """Initialize with coroutine."""
            self._coro = coro

        async def _await_result(self):
            """Await the coroutine (for use in async context)."""
            return await self._coro

        def result(self):
            """Execute coroutine and return result (synchronous)."""
            # Check if we're in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context - can't use run_until_complete
                # Return a coroutine that the caller should await
                # This is a limitation of the mock - in real LangGraph, this wouldn't happen
                raise RuntimeError(
                    "MockFuture.result() called in async context. "
                    "Use await MockFuture._await_result() instead, or ensure LangGraph is installed."
                )
            except RuntimeError:
                # No running loop, create a new one
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                return loop.run_until_complete(self._coro)

    def task(func):
        """Mock task decorator that returns MockFuture."""

        def wrapper(*args, **kwargs):
            return MockFuture(func(*args, **kwargs))

        return wrapper

    def entrypoint(checkpointer=None):
        """Mock entrypoint decorator."""

        def decorator(func):
            return func

        return decorator

    PostgresSaver = None  # type: ignore[assignment, misc]


class AnalysisState(TypedDict):
    """State schema for analysis workflow.

    Defines the structure of data passed between workflow nodes.

    """

    analysis_id: str
    url: str
    content_type: str
    raw_content: str
    extraction_metadata: dict
    content_embedding: list[float]
    supervisor_decision: dict | None
    agent_findings: list[dict]
    aggregated_insights: dict | None
    final_markdown: str | None


# Setup checkpointer (PostgreSQL for production, MemorySaver for dev)
checkpointer = None
if LANGGRAPH_AVAILABLE and settings.DATABASE_URL:
    try:
        checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
    except (ValueError, ImportError, RuntimeError) as e:
        logger.warning(
            "checkpointer_setup_failed",
            error=str(e),
            message="Workflow will run without checkpointing",
        )


@task
async def extract_content(url: str, analysis_id: str) -> dict:
    """Extract content from URL using Jina Reader.

    Args:
        url: URL to extract content from
        analysis_id: UUID of the analysis

    Returns:
        Dictionary with raw_content and extraction_metadata

    """
    # Emit SSE event: extraction started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="extraction",
        status="running",
    )

    jina = JinaReader()
    try:
        extracted = await jina.extract_article(url)

        # Emit SSE event: extraction complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="extraction",
            status="complete",
            word_count=extracted["word_count"],
        )

        logger.info(
            "workflow_extraction_complete",
            analysis_id=analysis_id,
            word_count=extracted["word_count"],
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


@task
async def generate_embedding(content: str, analysis_id: str) -> list[float]:
    """Generate embedding for content.

    Args:
        content: Text content to generate embedding for
        analysis_id: UUID of the analysis

    Returns:
        List of floats representing the embedding vector

    """
    # Emit SSE event: embedding generation started
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="embedding",
        status="running",
    )

    try:
        embedding = await embedding_service.generate_embedding(content)

        # Emit SSE event: embedding complete
        await emit_streaming_event(
            "progress",
            analysis_id=analysis_id,
            stage="embedding",
            status="complete",
        )

        logger.info(
            "workflow_embedding_complete",
            analysis_id=analysis_id,
            embedding_dim=len(embedding),
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
    else:
        return embedding


# Main workflow using Functional API
@entrypoint(checkpointer=checkpointer)
async def analysis_workflow(
    url: str,
    analysis_id: str,
    previous: dict | None = None,
) -> dict:
    """Execute main analysis workflow using LangGraph v1.0 Functional API.

    Args:
        url: URL to analyze
        analysis_id: UUID of the analysis
        previous: Previous workflow state (for resumption)

    Returns:
        Dictionary with analysis results

    """
    logger.info(
        "workflow_started",
        analysis_id=analysis_id,
        url=url,
    )

    try:
        # Extract content (returns future, can run in parallel)
        extraction_future = extract_content(url, analysis_id)

        # Get result - handle both MockFuture and real LangGraph futures
        if hasattr(extraction_future, "_await_result"):
            # MockFuture in async context
            extraction_result = await extraction_future._await_result()
        elif hasattr(extraction_future, "result"):
            # MockFuture in sync context or real LangGraph future
            extraction_result = extraction_future.result()
        else:
            # Direct coroutine (shouldn't happen with @task decorator)
            extraction_result = await extraction_future

        # Generate embedding
        embedding_future = generate_embedding(
            extraction_result["raw_content"], analysis_id
        )
        if hasattr(embedding_future, "_await_result"):
            embedding = await embedding_future._await_result()
        elif hasattr(embedding_future, "result"):
            embedding = embedding_future.result()
        else:
            embedding = await embedding_future

        result = {
            "analysis_id": analysis_id,
            "url": url,
            "raw_content": extraction_result["raw_content"],
            "extraction_metadata": extraction_result["extraction_metadata"],
            "content_embedding": embedding,
        }

        logger.info(
            "workflow_complete",
            analysis_id=analysis_id,
        )
    except Exception as e:
        logger.error(
            "workflow_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
    else:
        return result
