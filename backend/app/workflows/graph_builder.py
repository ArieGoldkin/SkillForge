"""StateGraph workflow builder for analysis pipeline.

This module constructs the LangGraph StateGraph workflow with native
parallel execution patterns using fan-out and fan-in with Send API.
"""

import os

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.db.repositories.chunk_repository import ChunkRepository
from app.db.session import get_session_factory
from app.workflows.nodes.agent_router import route_to_agents
from app.workflows.nodes.agents import (
    code_quality_critic_node,
    dependency_mapper_node,
    implementation_planner_node,
    integration_feasibility_node,
    performance_analyst_node,
    security_auditor_node,
    tech_comparator_node,
    trend_validator_node,
)
from app.workflows.nodes.supervisor import supervisor_route
from app.workflows.state import AnalysisState
from app.workflows.tasks import (
    aggregate_findings,
    chunk_content,
    extract_content,
    generate_artifact,
    generate_embedding,
    generate_embeddings_batch,
    log_chunking_metrics,
    store_embeddings,
)

# Try to import PostgresSaver dynamically to avoid hard dependency in lint
try:
    import importlib

    _lg_pg = importlib.import_module("langgraph.checkpoint.postgres")
    PostgresSaver = getattr(_lg_pg, "PostgresSaver", None)  # type: ignore[var-annotated]
except Exception:  # noqa: BLE001
    PostgresSaver = None  # type: ignore[var-annotated]

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
    """Generate embedding for content (legacy single vector).

    Returns only the fields being updated to avoid LangGraph concurrent update errors.
    """
    content = state["raw_content"]
    analysis_id = state["analysis_id"]
    embedding = await generate_embedding(content, analysis_id)
    # Return only updated fields, not entire state
    return {
        "content_embedding": embedding,
    }


async def _chunk_and_embed_node(state: AnalysisState) -> dict[str, object]:
    """Chunk content and generate embeddings for coarse/fine (and summaries)."""
    content = state["raw_content"]
    analysis_id = state["analysis_id"]

    # SSE: chunking started
    from app.services.sse_helpers import emit_streaming_event  # local import to avoid cycles

    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="chunking",
        status="running",
    )

    # Chunk
    chunk_payload = await chunk_content(content)

    # Embed all chunks (coarse + fine + summaries)
    all_payloads = (
        list(chunk_payload["coarse"])
        + list(chunk_payload["fine"])
        + list(chunk_payload["summaries"])
    )
    embedded = await generate_embeddings_batch(all_payloads, analysis_id)

    # Persist embeddings via ChunkRepository
    session_factory = get_session_factory()
    async with session_factory() as session:
        repo = ChunkRepository(session)
        await store_embeddings(embedded, analysis_id, repo)
        await session.commit()

    # Telemetry/logs (no raw text)
    log_chunking_metrics(
        coarse=len(chunk_payload["coarse"]),
        fine=len(chunk_payload["fine"]),
        summaries=len(chunk_payload["summaries"]),
        dedup_kept=chunk_payload["dedup_stats"].kept,
        dedup_dropped=chunk_payload["dedup_stats"].dropped,
    )

    # SSE: chunking+embedding complete
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="chunking",
        status="complete",
    )

    return {
        "chunk_counts": {
            "coarse": len(chunk_payload["coarse"]),
            "fine": len(chunk_payload["fine"]),
            "summaries": len(chunk_payload["summaries"]),
        },
        "dedup_stats": {
            "kept": chunk_payload["dedup_stats"].kept,
            "dropped": chunk_payload["dedup_stats"].dropped,
        },
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
    """Build StateGraph workflow with native parallel execution using Send API.

    Workflow structure:
    1. Extract content (sequential)
    2. Fan-out: Embedding + Supervisor (parallel)
    3. Fan-out: Selected agents (native LangGraph parallel via Send API)
    4. Fan-in: Aggregate findings (waits for all agent nodes)
    5. Generate artifact
    6. End

    Returns:
        Compiled StateGraph ready for execution (compiled graph type, not StateGraph)

    """
    # Create graph with AnalysisState
    graph = StateGraph(AnalysisState)

    # Add workflow nodes
    graph.add_node("extract", _extract_content_node)
    graph.add_node("embedding", _generate_embedding_node)
    graph.add_node("chunk_and_embed", _chunk_and_embed_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("aggregate", aggregate_findings)
    graph.add_node("generate_artifact", generate_artifact)

    # Add all agent nodes (each executes independently in parallel)
    graph.add_node("tech_comparator", tech_comparator_node)
    graph.add_node("security_auditor", security_auditor_node)
    graph.add_node("implementation_planner", implementation_planner_node)
    graph.add_node("performance_analyst", performance_analyst_node)
    graph.add_node("code_quality_critic", code_quality_critic_node)
    graph.add_node("trend_validator", trend_validator_node)
    graph.add_node("dependency_mapper", dependency_mapper_node)
    graph.add_node("integration_feasibility", integration_feasibility_node)

    # Define edges
    # Sequential: extract must complete first
    graph.set_entry_point("extract")

    # Fan-out: embedding and supervisor run in parallel after extract
    graph.add_edge("extract", "embedding")
    graph.add_edge("extract", "chunk_and_embed")
    graph.add_edge("extract", "supervisor")

    # Fan-out: Supervisor routes to selected agents dynamically using Send API
    # Conditional edge returns list[Send] objects for parallel execution
    # All agent nodes are potential targets
    graph.add_conditional_edges(
        "supervisor",
        route_to_agents,
        [
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
            "code_quality_critic",
            "trend_validator",
            "dependency_mapper",
            "integration_feasibility",
            "aggregate",  # Fallback if no agents selected
        ],
    )

    # Fan-in: All agent nodes route to aggregate
    # LangGraph automatically waits for all incoming edges before executing aggregate
    agent_nodes = [
        "tech_comparator",
        "security_auditor",
        "implementation_planner",
        "performance_analyst",
        "code_quality_critic",
        "trend_validator",
        "dependency_mapper",
        "integration_feasibility",
    ]
    for agent_node in agent_nodes:
        graph.add_edge(agent_node, "aggregate")

    # When no agents selected, route_to_agents returns Send("aggregate", state)
    # to explicitly route to aggregate (prevents hanging on empty list)

    # Sequential: aggregate -> generate_artifact -> end
    graph.add_edge("aggregate", "generate_artifact")
    graph.add_edge("generate_artifact", END)

    # Compile with checkpointer
    checkpointer = _get_checkpointer()
    compiled_graph = graph.compile(checkpointer=checkpointer)

    # Set step timeout (in seconds) - LangGraph handles cancellation gracefully
    # This prevents any single node from running indefinitely
    compiled_graph.step_timeout = STEP_TIMEOUT

    logger.info(
        "workflow_graph_compiled_with_timeout",
        step_timeout=STEP_TIMEOUT,
    )

    return compiled_graph
