"""LangGraph workflow for content analysis.

This module implements the initial LangGraph workflow using the Functional API.
Flow: extract → embed → done (no sub-agents yet).
"""

from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.func import entrypoint, task

from app.core.config import settings
from app.core.logging import get_logger
from app.services.embeddings import EmbeddingService
from app.services.extraction.jina_reader import JinaReader

# Try to import PostgresSaver, fallback to MemorySaver if not available
try:
    from langgraph.checkpoint.postgres import (
        PostgresSaver,  # type: ignore[import-not-found,import-untyped]
    )
except ImportError:
    PostgresSaver = None  # type: ignore[assignment, misc]

logger = get_logger(__name__)


class AnalysisState(TypedDict, total=False):
    """State schema for the analysis workflow.

    Fields marked with total=False are optional and may be populated
    as the workflow progresses through different stages.
    """

    analysis_id: str
    url: str
    content_type: str
    raw_content: str
    extraction_metadata: dict
    content_embedding: list[float]
    supervisor_decision: dict  # For future use
    agent_findings: list[dict]  # For future use
    aggregated_insights: dict  # For future use
    final_markdown: str  # For future use


# Setup checkpointer (PostgreSQL for production, MemorySaver for dev)
if settings.DATABASE_URL and PostgresSaver is not None:
    try:
        checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
        logger.info("workflow_checkpointer_initialized", type="PostgresSaver")
    except (ValueError, ConnectionError) as e:
        logger.warning(
            "workflow_checkpointer_fallback",
            error=str(e),
            fallback="MemorySaver",
        )
        checkpointer = MemorySaver()
else:
    checkpointer = MemorySaver()
    logger.info("workflow_checkpointer_initialized", type="MemorySaver")


@task
async def extract_content(url: str, analysis_id: str) -> dict:
    """Extract content from URL using JinaReader.

    Args:
        url: The URL to extract content from
        analysis_id: Unique identifier for this analysis

    Returns:
        Dictionary with 'raw_content' and 'extraction_metadata'

    Raises:
        Exception: If extraction fails

    """
    logger.info("workflow_extraction_started", analysis_id=analysis_id, url=url)
    jina = JinaReader()
    try:
        extracted = await jina.extract_article(url)
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
    finally:
        await jina.close()


@task
async def generate_embedding(content: str) -> list[float]:
    """Generate embedding vector for content.

    Args:
        content: The text content to embed

    Returns:
        List of floats representing the embedding vector

    Raises:
        Exception: If embedding generation fails

    """
    logger.info("workflow_embedding_started", content_length=len(content))
    embedding_service = EmbeddingService()
    embedding_result = await embedding_service.generate_embedding(content)
    embedding: list[float] = list(embedding_result)
    logger.info(
        "workflow_embedding_complete",
        embedding_dimensions=len(embedding),
    )
    return embedding


@entrypoint(checkpointer=checkpointer)
async def analysis_workflow(input_data: dict) -> dict:
    """Run main analysis workflow using LangGraph v1.0 Functional API.

    This workflow performs:
    1. Extract content from URL using JinaReader
    2. Generate embeddings for the extracted content
    3. Return complete state with all fields populated

    Args:
        input_data: Dictionary with 'url' and 'analysis_id' keys

    Returns:
        Dictionary matching AnalysisState structure with:
        - analysis_id
        - url
        - raw_content
        - extraction_metadata
        - content_embedding

    """
    url = input_data["url"]
    analysis_id = input_data["analysis_id"]

    logger.info(
        "workflow_started",
        analysis_id=analysis_id,
        url=url,
    )

    # Extract content (task returns awaitable)
    extraction_result = await extract_content(url, analysis_id)

    # Generate embedding (task returns awaitable)
    embedding = await generate_embedding(extraction_result["raw_content"])

    # Determine content type from metadata
    content_type = extraction_result["extraction_metadata"].get(
        "content_type",
        "article",
    )

    result = {
        "analysis_id": analysis_id,
        "url": url,
        "content_type": content_type,
        "raw_content": extraction_result["raw_content"],
        "extraction_metadata": extraction_result["extraction_metadata"],
        "content_embedding": embedding,
    }

    logger.info(
        "workflow_complete",
        analysis_id=analysis_id,
        url=url,
        content_length=len(extraction_result["raw_content"]),
        embedding_dimensions=len(embedding),
    )

    return result
