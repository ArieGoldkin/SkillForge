"""StateGraph workflow builder for analysis pipeline.

This module constructs the LangGraph StateGraph workflow with native
parallel execution patterns using fan-out and fan-in.
"""

import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.core.logging import get_logger
from app.workflows.nodes.parallel_agents import execute_parallel_agents
from app.workflows.nodes.supervisor import supervisor_route
from app.workflows.state import AnalysisState
from app.workflows.tasks import (
    aggregate_findings,
    extract_content,
    generate_artifact,
    generate_embedding,
)

# Try to import PostgresSaver, fallback to MemorySaver if not available
try:
    from langgraph.checkpoint.postgres import (
        PostgresSaver,  # type: ignore[import-not-found,import-untyped]
    )
except ImportError:
    PostgresSaver = None  # type: ignore[assignment, misc]

logger = get_logger(__name__)


def _get_checkpointer():
    """Get checkpointer instance (PostgresSaver or MemorySaver)."""
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
            return checkpointer
        except (ValueError, ConnectionError) as e:
            logger.warning(
                "workflow_checkpointer_fallback",
                error=str(e),
                fallback="MemorySaver",
            )
            return MemorySaver()
    else:
        logger.info("workflow_checkpointer_initialized", type="MemorySaver")
        return MemorySaver()


async def _extract_content_node(state: AnalysisState) -> dict[str, object]:
    """Extract content from URL.

    Returns only the fields being updated to avoid LangGraph concurrent update errors.
    """
    url = state["url"]
    analysis_id = state["analysis_id"]
    result = await extract_content(url, analysis_id)
    # Return only updated fields, not entire state
    return {
        "raw_content": result["raw_content"],
        "extraction_metadata": result["extraction_metadata"],
        "content_type": result["extraction_metadata"].get("content_type", "article"),
    }


async def _generate_embedding_node(state: AnalysisState) -> dict[str, object]:
    """Generate embedding for content.

    Returns only the fields being updated to avoid LangGraph concurrent update errors.
    """
    content = state["raw_content"]
    analysis_id = state["analysis_id"]
    embedding = await generate_embedding(content, analysis_id)
    # Return only updated fields, not entire state
    return {
        "content_embedding": embedding,
    }


async def _supervisor_node(state: AnalysisState) -> dict[str, object]:
    """Supervisor routes to appropriate agents.

    Returns only the fields being updated to avoid LangGraph concurrent update errors.
    """
    content = state["raw_content"]
    content_type = state["content_type"]
    analysis_id = state["analysis_id"]
    result = await supervisor_route(content, content_type, analysis_id)
    supervisor_decision = result.get("supervisor_decision", {})
    # Return only updated fields, not entire state
    if isinstance(supervisor_decision, dict):
        return {
            "supervisor_decision": supervisor_decision,
        }
    return {}


def build_analysis_graph():
    """Build StateGraph workflow with native parallel execution.

    Workflow structure:
    1. Extract content (sequential)
    2. Fan-out: Embedding + Supervisor (parallel)
    3. Fan-out: Parallel agents (native LangGraph parallel)
    4. Fan-in: Aggregate findings
    5. End

    Returns:
        Compiled StateGraph ready for execution (compiled graph type, not StateGraph)

    """
    # Create graph with AnalysisState
    graph = StateGraph(AnalysisState)

    # Add nodes
    graph.add_node("extract", _extract_content_node)
    graph.add_node("embedding", _generate_embedding_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("parallel_agents", execute_parallel_agents)
    graph.add_node("aggregate", aggregate_findings)
    graph.add_node("generate_artifact", generate_artifact)

    # Define edges
    # Sequential: extract must complete first
    graph.set_entry_point("extract")

    # Fan-out: embedding and supervisor run in parallel after extract
    graph.add_edge("extract", "embedding")
    graph.add_edge("extract", "supervisor")

    # Fan-in: Both embedding and supervisor must complete before parallel_agents
    # StateGraph automatically waits for all incoming edges
    graph.add_edge("embedding", "parallel_agents")
    graph.add_edge("supervisor", "parallel_agents")

    # Sequential: parallel_agents -> aggregate -> generate_artifact -> end
    graph.add_edge("parallel_agents", "aggregate")
    graph.add_edge("aggregate", "generate_artifact")
    graph.add_edge("generate_artifact", END)

    # Compile with checkpointer
    checkpointer = _get_checkpointer()
    return graph.compile(checkpointer=checkpointer)
