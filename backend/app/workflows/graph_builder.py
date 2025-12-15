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
from app.services.context.artifact_store import ArtifactStore
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
from app.workflows.nodes.inject_context_node import inject_context_node
from app.workflows.nodes.quality_gate_node import quality_gate_node, should_retry_synthesis
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
    """Extract content from URL or passthrough if already provided.

    This node supports two modes:
    1. URL extraction: Fetch content via JinaReader (normal workflow)
    2. Content passthrough: Skip extraction if raw_content is already in state
       (used for golden dataset regeneration with fixture content)

    Issue #299-304: Handle Pattern Implementation
    After extraction, creates content_ref for lightweight agent state passing.
    Agents load content on-demand via ArtifactStore instead of receiving full content.

    Returns only the fields being updated to avoid LangGraph concurrent update errors.
    """
    analysis_id = state.get("analysis_id")

    # Passthrough mode: Skip extraction if raw_content is already provided
    # This enables regeneration scripts to inject fixture content directly
    if state.get("raw_content"):
        raw_content = state["raw_content"]
        content_type = state.get("content_type", "article")
        logger.info(
            "extract_skipped_content_provided",
            analysis_id=analysis_id,
            content_length=len(raw_content),
            has_metadata=bool(state.get("extraction_metadata")),
        )

        # Create content_ref for Handle Pattern (Issue #299-304)
        content_ref = await _create_content_ref(
            analysis_id=str(analysis_id),
            content=raw_content,
            content_type=content_type,
        )

        return {
            "raw_content": raw_content,
            "extraction_metadata": state.get("extraction_metadata", {}),
            "content_type": content_type,
            "content_ref": content_ref,
        }

    # Normal mode: Extract content from URL via JinaReader
    url = state["url"]
    result = await extract_content(url, str(analysis_id or ""))
    raw_content = result["raw_content"]
    content_type = result["extraction_metadata"].get("content_type", "article")

    # Create content_ref for Handle Pattern (Issue #299-304)
    content_ref = await _create_content_ref(
        analysis_id=str(analysis_id),
        content=raw_content,
        content_type=content_type,
    )

    # Return only updated fields, not entire state
    return {
        "raw_content": raw_content,
        "extraction_metadata": result["extraction_metadata"],
        "content_type": content_type,
        "content_ref": content_ref,
    }


async def _create_content_ref(
    analysis_id: str,
    content: str,
    content_type: str,
) -> dict | None:
    """Create content_ref using ArtifactStore for Handle Pattern.

    Args:
        analysis_id: Analysis UUID string
        content: Raw content to store
        content_type: Content type (article, video, repo)

    Returns:
        ArtifactRef dict or None if creation fails

    """
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            store = ArtifactStore(session)
            artifact_ref = await store.create_ref(
                analysis_id=analysis_id,
                content=content,
                content_type=f"text/{content_type}",
            )
            logger.info(
                "content_ref_created",
                analysis_id=analysis_id,
                uri=artifact_ref.uri,
                size_bytes=artifact_ref.size_bytes,
                sections=artifact_ref.available_sections,
            )
            return artifact_ref.model_dump()
    except Exception as e:  # noqa: BLE001 - Graceful fallback, must not break workflow
        logger.warning(
            "content_ref_creation_failed",
            analysis_id=analysis_id,
            error=str(e),
            fallback="agents_will_use_raw_content",
        )
        return None


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
    """Chunk content and generate embeddings for coarse/fine (and summaries).

    This node is gated by ENABLE_COARSE_TO_FINE config flag. When disabled,
    it returns empty results without doing any work (preserving the legacy
    single-embedding behavior).
    """
    # Gate: Skip chunking if coarse-to-fine is disabled
    if not getattr(settings, "ENABLE_COARSE_TO_FINE", False):
        return {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }

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


async def _increment_retry_node(state: AnalysisState) -> dict[str, object]:
    """Increment quality gate retry counter.

    This node is executed when quality gate fails and retry is needed.
    It increments the retry counter before routing back to aggregation.

    Returns only the fields being updated to avoid LangGraph concurrent update errors.
    """
    retry_count = state.get("quality_gate_retry_count", 0)
    new_retry_count = retry_count + 1

    logger.info(
        "quality_gate_retry_incremented",
        analysis_id=state.get("analysis_id"),
        old_retry_count=retry_count,
        new_retry_count=new_retry_count,
    )

    return {
        "quality_gate_retry_count": new_retry_count,
    }


async def _quality_gate_fail_node(state: AnalysisState) -> dict[str, object]:
    """Handle quality gate failure after max retries (fail-open: still generate artifact).

    This node runs when quality gate has exhausted retries and quality is still
    too low. It logs the failure and emits a warning SSE event, but CONTINUES
    to artifact generation so users always get something.

    Issue #299-304: Changed from FAIL-CLOSED to FAIL-OPEN behavior.
    Users prefer getting a low-quality artifact over nothing at all.
    The quality warning is logged and can be shown in the UI.
    """
    from app.services.sse_helpers import emit_streaming_event

    analysis_id = str(state.get("analysis_id", ""))
    avg_score = float(state.get("quality_gate_avg_score", 0.0) or 0.0)
    quality_scores: dict[str, dict[str, object]] = state.get("quality_scores", {}) or {}  # type: ignore[assignment]
    retry_count = int(state.get("quality_gate_retry_count", 0) or 0)

    logger.warning(
        "quality_gate_failed_continuing_to_artifact",
        analysis_id=analysis_id,
        avg_score=avg_score,
        retry_count=retry_count,
        quality_scores={k: v.get("score") for k, v in quality_scores.items()},
        message="Quality gate failed but continuing to artifact generation (fail-open)",
    )

    # Emit SSE warning event (not error - we're continuing)
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="quality_gate",
        status="low_quality",
        message=(
            f"Quality below threshold after {retry_count} retries "
            f"(score: {avg_score:.2f}). Generating artifact anyway."
        ),
        quality_scores={k: v.get("score") for k, v in quality_scores.items()},
    )

    # Return quality metadata but don't mark as failed - let artifact generation continue
    return {
        "quality_gate_passed": False,
        "quality_gate_warning": f"Low quality (avg_score={avg_score:.2f}) after {retry_count} retries",
    }


def build_analysis_graph():
    """Build StateGraph workflow with native parallel execution using Send API.

    Workflow structure:
    1. Extract content (sequential)
    2. Fan-out: Embedding + Supervisor + Inject Context (parallel)
    3. Fan-out: Selected agents (native LangGraph parallel via Send API)
    4. Fan-in: Aggregate findings (waits for all agent nodes)
    5. Quality gate validation (with retry loop)
       - If quality < threshold and retries available: increment_retry -> aggregate
       - If quality passes or max retries: continue -> generate_artifact
    6. Generate artifact
    7. End

    Issue #300: inject_context node runs in parallel with embedding and supervisor
    to fetch relevant memories from past analyses and make them available to agents.

    Issue #301: quality_gate node validates synthesis quality using LLM-as-judge
    evaluators and triggers retry if quality falls below threshold (up to 2 retries).

    Returns:
        Compiled StateGraph ready for execution (compiled graph type, not StateGraph)

    """
    # Create graph with AnalysisState
    graph = StateGraph(AnalysisState)

    # Add workflow nodes
    graph.add_node("extract", _extract_content_node)
    graph.add_node("embedding", _generate_embedding_node)
    graph.add_node("chunk_and_embed", _chunk_and_embed_node)
    graph.add_node("inject_context", inject_context_node)
    graph.add_node("supervisor", _supervisor_node)
    graph.add_node("aggregate", aggregate_findings)
    graph.add_node("quality_gate", quality_gate_node)
    graph.add_node("increment_retry", _increment_retry_node)
    graph.add_node("quality_gate_fail", _quality_gate_fail_node)
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

    # Fan-out: embedding, chunk_and_embed, inject_context, and supervisor run in parallel after extract
    graph.add_edge("extract", "embedding")
    graph.add_edge("extract", "chunk_and_embed")
    graph.add_edge("extract", "inject_context")
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

    # Quality gate: aggregate -> quality_gate (validation)
    graph.add_edge("aggregate", "quality_gate")

    # Conditional: quality_gate decides to retry, continue, or fail
    # - "retry_synthesis": increment retry counter and loop back to aggregate
    # - "continue": proceed to artifact generation
    # - "fail": quality too low after max retries, fail the analysis (fail-closed)
    graph.add_conditional_edges(
        "quality_gate",
        should_retry_synthesis,
        {
            "retry_synthesis": "increment_retry",
            "continue": "generate_artifact",
            "fail": "quality_gate_fail",
        },
    )

    # Retry loop: increment_retry -> aggregate
    graph.add_edge("increment_retry", "aggregate")

    # Quality gate fail: quality_gate_fail -> generate_artifact (fail-open behavior)
    # Issue #299-304: Always generate artifact even with low quality
    # Users prefer getting something over nothing
    graph.add_edge("quality_gate_fail", "generate_artifact")

    # Sequential: generate_artifact -> end
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
