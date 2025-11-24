"""LangGraph workflow for content analysis.

This module implements the analysis workflow using LangGraph v1.0 Functional API.
The workflow orchestrates content extraction and embedding generation for URLs.

Architecture:
    The workflow uses LangGraph's @entrypoint and @task decorators to create
    a functional workflow. Tasks are executed sequentially with automatic
    checkpointing to PostgreSQL (or MemorySaver in development).

Workflow Flow:
    1. Extract Content: Uses JinaReader to extract content from URL
    2. Generate Embedding: Uses EmbeddingService to create vector embeddings
    3. Return Complete State: Returns AnalysisState with all fields populated

Checkpointing:
    - Production: Uses PostgresSaver for persistent state across restarts
    - Development: Falls back to MemorySaver if database unavailable
    - Thread-based isolation: Each analysis_id uses a unique thread_id

SSE Events:
    The workflow emits Server-Sent Events (SSE) at each stage:
    - progress events: Stage status updates (running, complete)
    - error events: Failure notifications with error details
    - complete events: Final workflow completion

State Management:
    AnalysisState is a TypedDict that tracks workflow progress. Fields are
    populated incrementally as the workflow progresses through stages.

Example:
    ```python
    from app.workflows.analysis import analysis_workflow

    result = await analysis_workflow.ainvoke(
        {
            "url": "https://example.com/article",
            "analysis_id": "unique-analysis-id",
        },
        config={"configurable": {"thread_id": "unique-analysis-id"}},
    )
    ```

Future Enhancements:
    - Sub-agents for specialized analysis (tech comparison, security audit, etc.)
    - Supervisor pattern for agent coordination
    - Artifact generation (markdown guides, code examples)
"""

import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.func import entrypoint, task

from app.core.config import settings
from app.core.constants import CONTENT_TYPE_ARTICLE
from app.core.logging import get_logger
from app.workflows.tasks import extract_content, generate_embedding

# Try to import PostgresSaver, fallback to MemorySaver if not available
try:
    from langgraph.checkpoint.postgres import (
        PostgresSaver,  # type: ignore[import-not-found,import-untyped]
    )
except ImportError:
    PostgresSaver = None  # type: ignore[assignment, misc]

logger = get_logger(__name__)

# Setup checkpointer (PostgreSQL for production, MemorySaver for dev)
# Use MemorySaver in tests to avoid database connection hangs
if (
    settings.DATABASE_URL
    and PostgresSaver is not None
    and not os.environ.get("PYTEST_CURRENT_TEST")
):
    try:
        checkpointer = PostgresSaver.from_conn_string(settings.DATABASE_URL)
        logger.info("workflow_checkpointer_initialized", type="PostgresSaver")
    except (ValueError, ConnectionError, Exception) as e:
        logger.warning(
            "workflow_checkpointer_fallback",
            error=str(e),
            fallback="MemorySaver",
        )
        checkpointer = MemorySaver()
else:
    checkpointer = MemorySaver()
    logger.info("workflow_checkpointer_initialized", type="MemorySaver")


# Apply @task decorator to task functions for LangGraph
# Note: task() can be used as a decorator factory or called directly
extract_content_task = task(extract_content)
generate_embedding_task = task(generate_embedding)


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

    try:
        # Extract content (task returns awaitable)
        extraction_result = await extract_content_task(url, analysis_id)

        # Generate embedding (task returns awaitable)
        embedding = await generate_embedding_task(extraction_result["raw_content"], analysis_id)

        # Determine content type from metadata
        content_type = extraction_result["extraction_metadata"].get(
            "content_type",
            CONTENT_TYPE_ARTICLE,
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
    except Exception as e:
        logger.error(
            "workflow_failed",
            analysis_id=analysis_id,
            error=str(e),
            exc_info=True,
        )
        raise
