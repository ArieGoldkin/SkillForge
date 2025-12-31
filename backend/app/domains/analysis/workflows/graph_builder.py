"""StateGraph workflow builder for analysis pipeline.

This module constructs the LangGraph StateGraph workflow with native
parallel execution patterns using fan-out and fan-in with Send API.
"""

import os
import uuid
from collections.abc import Callable
from typing import Any, cast

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Send

from app.core.config import settings
from app.core.embedding_utils import safe_bool_for_logging
from app.core.exception_utils import enrich_exception
from app.core.exceptions import ExtractionErrorCode, JinaReaderError
from app.core.logging import get_logger
from app.core.timeout_config import STEP_TIMEOUT
from app.db.repositories.analysis_repository import AnalysisRepository
from app.db.repositories.chunk_repository import ChunkRepository
from app.db.session import get_session_factory
from app.domains.analysis.services.context.artifact_store import ArtifactStore
from app.domains.analysis.workflows.nodes.agent_router import route_to_agents
from app.domains.analysis.workflows.nodes.agents import (
    actionable_node,
    audience_fit_node,
    code_quality_critic_node,
    community_pulse_node,
    deep_researcher_node,
    dependency_mapper_node,
    implementation_planner_node,
    integration_feasibility_node,
    key_insights_node,
    knowledge_curator_node,
    learning_path_advisor_node,
    performance_analyst_node,
    pros_cons_node,
    security_auditor_node,
    tech_comparator_node,
    trend_validator_node,
)
from app.domains.analysis.workflows.nodes.inject_context_node import inject_context_node
from app.domains.analysis.workflows.nodes.quality_gate_node import (
    quality_gate_node,
    should_retry_synthesis,
)
from app.domains.analysis.workflows.nodes.supervisor import supervisor_route
from app.domains.analysis.workflows.nodes.tier_aggregate_node import (
    tier1_aggregate,
    tier2_aggregate,
)
from app.domains.analysis.workflows.state import AnalysisState
from app.domains.analysis.workflows.state_accessors import get_extraction_metadata
from app.domains.analysis.workflows.tasks import (
    aggregate_findings,
    chunk_content,
    extract_content,
    generate_artifact,
    generate_embedding,
    generate_embeddings_batch,
    log_chunking_metrics,
    store_embeddings,
)
from app.domains.analysis.workflows.tier_types import (
    TIER_1_AGENTS,
    TIER_2_AGENTS,
    TIER_3_AGENTS,
)
from app.shared.services.extraction.jina_reader import _is_error_page

logger = get_logger(__name__)

# Try to import PostgresSaver dynamically to avoid hard dependency in lint
try:
    import importlib

    _lg_pg = importlib.import_module("langgraph.checkpoint.postgres")
    PostgresSaver = getattr(_lg_pg, "PostgresSaver", None)
except Exception as e:  # noqa: BLE001 - Graceful degradation: PostgresSaver is optional dependency
    logger.debug("postgres_checkpointer_unavailable", error=str(e), exc_info=e)
    PostgresSaver = None

# Try to import RedisSaver dynamically to avoid hard dependency in lint
try:
    import importlib

    _lg_redis = importlib.import_module("langgraph.checkpoint.redis")
    RedisSaver = getattr(_lg_redis, "RedisSaver", None)
except Exception as e:  # noqa: BLE001 - Graceful degradation: RedisSaver is optional dependency
    logger.debug("redis_checkpointer_unavailable", error=str(e), exc_info=e)
    RedisSaver = None


def get_checkpointer():
    """Get checkpointer instance from FastAPI app.state or fallback.

    Issue #624: Returns app-scoped AsyncPostgresSaver initialized in main.py lifespan,
    or creates fallback checkpointer if app.state.checkpointer is not available.

    Checkpointer selection priority:
    1. MemorySaver for tests (PYTEST_CURRENT_TEST is set)
    2. RedisSaver if USE_REDIS_CHECKPOINT=true and REDIS_URL is set
    3. AsyncPostgresSaver from app.state (initialized in lifespan)
    4. MemorySaver as fallback

    Returns:
        Checkpointer instance (AsyncPostgresSaver, RedisSaver, or MemorySaver)

    """
    # Use MemorySaver in tests to avoid database connection hangs
    if os.environ.get("PYTEST_CURRENT_TEST"):
        logger.info("workflow_checkpointer_initialized", type="MemorySaver", reason="test_mode")
        return MemorySaver()

    # Try RedisSaver if enabled and configured
    if settings.USE_REDIS_CHECKPOINT and settings.REDIS_URL and RedisSaver is not None:
        try:
            # RedisSaver.from_conn_string creates a Redis connection pool
            # with automatic TTL-based cleanup of checkpoints
            # TTL format: {"default_ttl": X} where X is in MINUTES
            # Convert seconds to minutes for RedisSaver
            ttl_minutes = settings.REDIS_CHECKPOINT_TTL / 60.0
            checkpointer = RedisSaver.from_conn_string(
                settings.REDIS_URL,
                # Set checkpoint TTL for automatic cleanup
                # RedisSaver expects TTL in minutes via "default_ttl" key
                ttl={"default_ttl": ttl_minutes},
            )
            logger.info(
                "workflow_checkpointer_initialized",
                type="RedisSaver",
                ttl_seconds=settings.REDIS_CHECKPOINT_TTL,
                ttl_minutes=ttl_minutes,
                redis_url=settings.REDIS_URL.split("@")[-1],  # Log host only, not credentials
            )
            return checkpointer
        except (ValueError, ConnectionError) as e:
            logger.warning(
                "workflow_checkpointer_fallback_from_redis",
                error=str(e),
                fallback="AsyncPostgresSaver or MemorySaver",
            )
            # Fall through to AsyncPostgresSaver/MemorySaver

    # Issue #624: AsyncPostgresSaver is initialized in app.state by main.py lifespan
    # For now, we don't have a way to access app.state from graph_builder module
    # (no request context). This will be addressed in a future refactor where
    # the checkpointer is passed explicitly from the orchestrator.
    # Fallback to MemorySaver (development/local mode)
    logger.info(
        "workflow_checkpointer_initialized",
        type="MemorySaver",
        reason="app_state_not_accessible",
    )
    return MemorySaver()


async def _extract_content_node(state: AnalysisState) -> dict[str, object]:
    """Extract content from URL or passthrough if already provided.

    This node supports three modes:
    1. URL extraction: Fetch content via JinaReader (normal workflow)
    2. Content passthrough: Skip extraction if raw_content is already in state
       (used for golden dataset regeneration with fixture content)
    3. Skip mode: Skip if skip_extraction flag is set (Issue #544 - retry/rerun support)

    Issue #299-304: Handle Pattern Implementation
    After extraction, creates content_ref for lightweight agent state passing.
    Agents load content on-demand via ArtifactStore instead of receiving full content.

    Issue #441: Initializes abort signal fields to default values.

    Returns only the fields being updated to avoid LangGraph concurrent update errors.
    """
    analysis_id = state.get("analysis_id")

    # Issue #441: Initialize abort signal fields with default values
    # This ensures all workflows start with consistent state
    base_result: dict[str, object] = {
        "should_abort": False,
        "abort_reason": None,
        "extraction_status": "pending",
        "extraction_error_code": None,
    }

    # Issue #544: Skip mode - extraction already done (retry/rerun from analyzing stage)
    # When skip_extraction is set, raw_content and metadata are already loaded from DB
    if state.get("skip_extraction"):
        logger.info(
            "extract_skipped_already_completed",
            analysis_id=analysis_id,
            has_content=bool(state.get("raw_content")),
            has_metadata=bool(get_extraction_metadata(state)),
            reason="retry_from_analyzing_stage",
        )
        # Don't update state - extraction data already loaded by orchestrator
        # Return minimal update to mark extraction as completed
        return {
            "extraction_status": "success",
        }

    # Passthrough mode: Skip extraction if raw_content is already provided
    # This enables regeneration scripts to inject fixture content directly
    if state.get("raw_content"):
        raw_content = state["raw_content"]
        content_type = state.get("content_type", "article")
        logger.info(
            "extract_skipped_content_provided",
            analysis_id=analysis_id,
            content_length=len(raw_content),
            has_metadata=bool(get_extraction_metadata(state)),
        )

        # Create content_ref for Handle Pattern (Issue #299-304)
        content_ref = await _create_content_ref(
            analysis_id=str(analysis_id),
            content=raw_content,
            content_type=content_type,
        )

        return {
            **base_result,
            "raw_content": raw_content,
            "extraction_metadata": get_extraction_metadata(state),
            "content_type": content_type,
            "content_ref": content_ref,
            "extraction_status": "success",
        }

    # Normal mode: Extract content from URL via JinaReader
    url = state["url"]
    analysis_mode = state.get("analysis_mode", "standard")

    # Issue #441: Wrap extraction in try/except to catch JinaReaderError
    try:
        result = await extract_content(url, str(analysis_id or ""), analysis_mode)
    except JinaReaderError as e:
        logger.warning(
            "extraction_failed",
            analysis_id=analysis_id,
            error=str(e),
            error_code=e.error_code.value if e.error_code else None,
        )
        return {
            "should_abort": True,
            "abort_reason": str(e),
            "extraction_status": "failed",
            "extraction_error_code": e.error_code.value
            if e.error_code
            else ExtractionErrorCode.UNKNOWN.value,
        }

    raw_content = result["raw_content"]
    content_type = result["extraction_metadata"].get("content_type", "article")
    title = result["extraction_metadata"].get("title", "")

    # Issue #441: Check if extracted content is an error page BEFORE storing
    if _is_error_page(title, raw_content):
        logger.warning(
            "extraction_error_page_detected",
            analysis_id=analysis_id,
            title=title,
        )
        return {
            "should_abort": True,
            "abort_reason": f"Error page detected: {title}",
            "extraction_status": "failed",
            "extraction_error_code": ExtractionErrorCode.ERROR_PAGE.value,
            # Don't include raw_content or extraction_metadata to avoid storing error page data
        }

    # Create content_ref for Handle Pattern (Issue #299-304)
    content_ref = await _create_content_ref(
        analysis_id=str(analysis_id),
        content=raw_content,
        content_type=content_type,
    )

    # Update analysis.title from extraction_metadata (Fix for "Untitled" issue)
    # Title exists in extraction_metadata but wasn't being persisted to analysis.title
    if title:
        # Clean title: strip "Title:" prefix and whitespace (common extraction artifact)
        import re
        cleaned_title = re.sub(r'^title:\s*', '', title, flags=re.IGNORECASE).strip()
        
        # Only save if title is meaningful (not empty after cleaning)
        if cleaned_title and cleaned_title.lower() != "untitled":
            session_factory = get_session_factory()
            async with session_factory() as session:
                repo = AnalysisRepository(session)
                analysis = await repo.get_by_id(analysis_id, validate=False)
                if analysis and not analysis.title:
                    # Only update if title is currently null
                    analysis.title = cleaned_title
                    await session.commit()
                    logger.info(
                        "analysis_title_updated",
                        analysis_id=str(analysis_id),
                        title=cleaned_title[:100] if len(cleaned_title) > 100 else cleaned_title,
                    )

    # Return only updated fields, not entire state
    return {
        **base_result,
        "raw_content": raw_content,
        "extraction_metadata": result["extraction_metadata"],
        "content_type": content_type,
        "content_ref": content_ref,
        "extraction_status": "success",
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
    # Issue #441: Skip if workflow is aborting
    if state.get("should_abort"):
        logger.debug("generate_embedding_skipped_abort", analysis_id=state.get("analysis_id"))
        return {}

    # Issue #544: Skip if embedding already loaded from DB (retry/rerun from analyzing stage)
    if state.get("skip_embedding"):
        logger.info(
            "generate_embedding_skipped_already_completed",
            analysis_id=state.get("analysis_id"),
            has_embedding=safe_bool_for_logging(state.get("content_embedding")),
            reason="retry_from_analyzing_stage",
        )
        return {}

    # Issue #539: Defensive state access
    content = state.get("raw_content", "")
    analysis_id = state.get("analysis_id")
    if not content or not analysis_id:
        logger.error(
            "generate_embedding_missing_state",
            has_content=bool(content),
            has_analysis_id=bool(analysis_id),
        )
        return {}

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
    # Issue #441: Skip if workflow is aborting
    if state.get("should_abort"):
        logger.debug("chunk_and_embed_skipped_abort", analysis_id=state.get("analysis_id"))
        return {}

    # Gate: Skip chunking if coarse-to-fine is disabled
    if not getattr(settings, "ENABLE_COARSE_TO_FINE", False):
        return {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }

    # Issue #539: Defensive state access
    content = state.get("raw_content", "")
    analysis_id = state.get("analysis_id")
    if not content or not analysis_id:
        logger.error(
            "chunk_and_embed_missing_state",
            has_content=bool(content),
            has_analysis_id=bool(analysis_id),
        )
        return {
            "chunk_counts": {"coarse": 0, "fine": 0, "summaries": 0},
            "dedup_stats": {"kept": 0, "dropped": 0},
        }

    # SSE: chunking started
    from app.shared.services.messaging.sse_helpers import (
        emit_streaming_event,  # local import to avoid cycles
    )

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
    # Issue #441: Skip if workflow is aborting
    from app.domains.analysis.workflows.utils.abort_helpers import check_should_abort

    abort_result = check_should_abort(state)
    if abort_result is None:
        return {}

    # Issue #539: Defensive state access
    content = state.get("raw_content", "")
    content_type = state.get("content_type", "article")
    analysis_id = state.get("analysis_id")
    if not content or not analysis_id:
        logger.error(
            "supervisor_missing_state",
            has_content=bool(content),
            has_analysis_id=bool(analysis_id),
        )
        return {}

    # Issue #436: Pass analysis_mode for tier-based agent filtering
    analysis_mode = state.get("analysis_mode", "standard")
    result = await supervisor_route(content, content_type, analysis_id, analysis_mode=analysis_mode)
    supervisor_decision = result.get("supervisor_decision", {})
    # Return only updated fields, not entire state
    if isinstance(supervisor_decision, dict):
        return {
            "supervisor_decision": supervisor_decision,
        }
    return {}


def _route_after_extraction(state: AnalysisState) -> str:
    """Route after extraction based on abort signal.

    Issue #441: If extraction failed or error page detected, route to
    workflow_failed node instead of continuing to embedding generation.
    """
    should_abort = state.get("should_abort")
    logger.debug(
        "route_after_extraction_decision",
        analysis_id=state.get("analysis_id"),
        should_abort=should_abort,
        route="workflow_failed" if should_abort else "embedding",
    )
    if should_abort:
        return "workflow_failed"
    return "embedding"


async def _workflow_failed_node(state: AnalysisState) -> dict[str, object]:
    """Handle workflow failure by persisting error to database.

    Issue #441: This node is reached when extraction fails or error page is detected.
    It persists the failure to the database and returns state for proper graph termination.
    """
    analysis_id = state.get("analysis_id")
    abort_reason: str = state.get("abort_reason") or "Unknown error"
    error_code: str = state.get("extraction_error_code") or "UNKNOWN"

    logger.error(
        "workflow_aborted",
        analysis_id=analysis_id,
        abort_reason=abort_reason,
        error_code=error_code,
    )

    # Persist failure to database
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            repo = AnalysisRepository(session)
            await repo.mark_failed(
                analysis_id=uuid.UUID(str(analysis_id)),
                error_code=error_code,
                error_message=abort_reason,
                failed_at_stage="extraction",
            )
        logger.info(
            "workflow_failure_persisted",
            analysis_id=analysis_id,
            error_code=error_code,
        )
    except Exception as e:
        # Non-critical: DB failure during error handling must not crash workflow
        enrich_exception(
            e,
            operation="persist_workflow_failure",
            analysis_id=analysis_id,
            error_code=error_code,
        )
        logger.exception(
            "workflow_failure_persistence_error",
            analysis_id=analysis_id,
            error_code=error_code,
            exc_info=e,
        )

    return {
        "workflow_status": "failed",
        "final_error": abort_reason,
    }


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
    from app.shared.services.messaging.sse_helpers import emit_streaming_event

    analysis_id = str(state.get("analysis_id", ""))
    avg_score = float(state.get("quality_gate_avg_score", 0.0) or 0.0)
    quality_scores_raw = state.get("quality_scores", {})
    retry_count = int(state.get("quality_gate_retry_count", 0) or 0)

    # Extract score values from nested structure
    # (e.g., {"relevance": {"score": 0.3, "comment": "..."}})
    # to flat structure (e.g., {"relevance": 0.3})
    quality_scores_flat: dict[str, float] = {}
    if quality_scores_raw:
        for aspect, value in quality_scores_raw.items():
            if isinstance(value, dict) and "score" in value:
                # Type checker needs explicit cast to understand value is dict[str, Any]
                value_dict = cast("dict[str, Any]", value)
                score_val = value_dict.get("score")
                if isinstance(score_val, (int, float)):
                    quality_scores_flat[aspect] = float(score_val)
            elif isinstance(value, (int, float)):
                quality_scores_flat[aspect] = float(value)

    logger.warning(
        "quality_gate_failed_continuing_to_artifact",
        analysis_id=analysis_id,
        avg_score=avg_score,
        retry_count=retry_count,
        quality_scores=quality_scores_flat,
        message="Quality gate failed but continuing to artifact generation (fail-open)",
    )

    # Emit SSE warning event (not error - we're continuing)
    # Status must be valid enum: pending, running, complete, failed, skipped
    await emit_streaming_event(
        "progress",
        analysis_id=analysis_id,
        stage="quality_gate",
        status="complete",  # Gate completed (with low quality warning in details)
        quality_warning="low_quality",  # Preserve warning info in details
        message=(
            f"Quality below threshold after {retry_count} retries "
            f"(score: {avg_score:.2f}). Generating artifact anyway."
        ),
        quality_scores=quality_scores_flat,
    )

    # Return quality metadata but don't mark as failed - let artifact generation continue
    return {
        "quality_gate_passed": False,
        "quality_gate_warning": (
            f"Low quality (avg_score={avg_score:.2f}) after {retry_count} retries"
        ),
    }


# =============================================================================
# Issue #588: Sequential Tier Learning - Tier Routing Functions
# =============================================================================


def _route_to_tier1_agents(state: AnalysisState) -> list[Send]:
    """Route to Tier 1 (foundational) agents based on supervisor decision.

    This function filters the supervisor's selected agents to only include
    Tier 1 agents. If no Tier 1 agents are selected, it routes directly to
    tier1_aggregate to continue the workflow.

    Tier 1 agents (foundational analysis):
    - key_insights: Main themes and technical concepts
    - pros_cons: Strengths and weaknesses
    - audience_fit: Target audience and prerequisites
    - actionable: Practical applications

    Args:
        state: Current workflow state with supervisor_decision

    Returns:
        List of Send objects for Tier 1 agent execution

    """
    # Get selected agents from supervisor decision
    supervisor_decision = state.get("supervisor_decision", {})
    if not isinstance(supervisor_decision, dict):
        supervisor_decision = {}

    # Note: Supervisor uses "agents" key (not "selected_agents") for consistency with agent_router.py
    selected_agents: list[str] = supervisor_decision.get("agents", [])
    if not isinstance(selected_agents, list):
        selected_agents = []

    # Filter for Tier 1 agents
    tier1_agents = [agent for agent in selected_agents if agent in TIER_1_AGENTS]

    analysis_id = state.get("analysis_id")
    logger.info(
        "routing_to_tier1_agents",
        analysis_id=analysis_id,
        selected_agents=selected_agents,
        tier1_agents=tier1_agents,
        tier1_count=len(tier1_agents),
    )

    # If no Tier 1 agents selected, route directly to tier1_aggregate
    if not tier1_agents:
        logger.debug(
            "no_tier1_agents_selected",
            analysis_id=analysis_id,
            routing_to="tier1_aggregate",
        )
        return [Send("tier1_aggregate", state)]

    # Map agent types to node names (some have different names)
    agent_to_node = {
        "key_insights": "key_insights",
        "pros_cons": "pros_cons",
        "audience_fit": "audience_fit",
        "actionable": "actionable",
    }

    # Create Send objects for each Tier 1 agent
    return [Send(agent_to_node.get(agent, agent), state) for agent in tier1_agents]


def _route_to_tier2_agents(state: AnalysisState) -> list[Send]:
    """Route to Tier 2 (technical) agents based on supervisor decision.

    This function filters the supervisor's selected agents to only include
    Tier 2 agents. These agents receive tier1_summary context from previous tier.

    Tier 2 agents (technical deep-dive):
    - tech_comparator, security_auditor, impl_planner, performance_analyst,
    - code_quality_critic, trend_validator, dependency_mapper, integration_feasibility

    Args:
        state: Current workflow state with supervisor_decision and tier1_summary

    Returns:
        List of Send objects for Tier 2 agent execution

    """
    supervisor_decision = state.get("supervisor_decision", {})
    if not isinstance(supervisor_decision, dict):
        supervisor_decision = {}

    # Note: Supervisor uses "agents" key for consistency with agent_router.py
    selected_agents: list[str] = supervisor_decision.get("agents", [])
    if not isinstance(selected_agents, list):
        selected_agents = []

    # Filter for Tier 2 agents
    tier2_agents = [agent for agent in selected_agents if agent in TIER_2_AGENTS]

    analysis_id = state.get("analysis_id")
    has_tier1_summary = bool(state.get("tier1_summary"))

    logger.info(
        "routing_to_tier2_agents",
        analysis_id=analysis_id,
        tier2_agents=tier2_agents,
        tier2_count=len(tier2_agents),
        has_tier1_context=has_tier1_summary,
    )

    # If no Tier 2 agents selected, route directly to tier2_aggregate
    if not tier2_agents:
        logger.debug(
            "no_tier2_agents_selected",
            analysis_id=analysis_id,
            routing_to="tier2_aggregate",
        )
        return [Send("tier2_aggregate", state)]

    # Map agent types to node names
    agent_to_node = {
        "tech_comparator": "tech_comparator",
        "security_auditor": "security_auditor",
        "impl_planner": "implementation_planner",
        "performance_analyst": "performance_analyst",
        "code_quality_critic": "code_quality_critic",
        "trend_validator": "trend_validator",
        "dependency_mapper": "dependency_mapper",
        "integration_feasibility": "integration_feasibility",
    }

    return [Send(agent_to_node.get(agent, agent), state) for agent in tier2_agents]


def _route_to_tier3_agents(state: AnalysisState) -> list[Send]:
    """Route to Tier 3 (research) agents based on supervisor decision.

    This function filters the supervisor's selected agents to only include
    Tier 3 agents. These agents receive tier1_summary + tier2_summary context.

    Tier 3 agents (strategic research):
    - deep_researcher, community_pulse, knowledge_curator, learning_path_advisor

    Args:
        state: Current workflow state with supervisor_decision and tier summaries

    Returns:
        List of Send objects for Tier 3 agent execution

    """
    supervisor_decision = state.get("supervisor_decision", {})
    if not isinstance(supervisor_decision, dict):
        supervisor_decision = {}

    # Note: Supervisor uses "agents" key for consistency with agent_router.py
    selected_agents: list[str] = supervisor_decision.get("agents", [])
    if not isinstance(selected_agents, list):
        selected_agents = []

    # Filter for Tier 3 agents
    tier3_agents = [agent for agent in selected_agents if agent in TIER_3_AGENTS]

    analysis_id = state.get("analysis_id")
    has_tier1_summary = bool(state.get("tier1_summary"))
    has_tier2_summary = bool(state.get("tier2_summary"))

    logger.info(
        "routing_to_tier3_agents",
        analysis_id=analysis_id,
        tier3_agents=tier3_agents,
        tier3_count=len(tier3_agents),
        has_tier1_context=has_tier1_summary,
        has_tier2_context=has_tier2_summary,
    )

    # If no Tier 3 agents selected, route directly to aggregate
    if not tier3_agents:
        logger.debug(
            "no_tier3_agents_selected",
            analysis_id=analysis_id,
            routing_to="aggregate",
        )
        return [Send("aggregate", state)]

    # Map agent types to node names
    agent_to_node = {
        "deep_researcher": "deep_researcher",
        "community_pulse": "community_pulse",
        "knowledge_curator": "knowledge_curator",
        "learning_path_advisor": "learning_path_advisor",
    }

    return [Send(agent_to_node.get(agent, agent), state) for agent in tier3_agents]


def build_analysis_graph(  # noqa: PLR0915 - Many nodes require many statements
    route_to_agents_fn: Callable[[AnalysisState], list[Send]] | None = None,
    checkpointer_override: Any | None = None,
):
    """Build StateGraph workflow with Sequential Tier Learning (Issue #588).

    This function supports dependency injection for testability. Optional parameters
    allow tests to inject mocked routing functions and checkpointers.

    Args:
        route_to_agents_fn: Optional custom routing function for supervisor->agent routing.
            Defaults to route_to_agents from agent_router module. Only used for backward
            compatibility tests; new tiered routing uses _route_to_tier{1,2,3}_agents.
        checkpointer_override: Optional checkpointer instance to use instead of default.
            Defaults to get_checkpointer() which returns app-scoped AsyncPostgresSaver,
            RedisSaver, or MemorySaver. Issue #624: Supports 2025 best practice
            AsyncPostgresSaver with FastAPI lifespan integration.

    Workflow structure (Issue #588: Sequential Tier Learning):
    1. Extract content (sequential)
    2. Generate embedding (sequential)
    3. Fan-out: Chunk + Embed, Inject Context, Supervisor (parallel)
    4. Tier 1: Foundational agents (parallel via Send API)
       - key_insights, pros_cons, audience_fit, actionable
    5. tier1_aggregate: Compress Tier 1 findings to ~500 tokens
    6. Tier 2: Technical agents (parallel, with tier1_summary context)
       - tech_comparator, security_auditor, impl_planner, etc.
    7. tier2_aggregate: Compress Tier 2 findings to ~800 tokens
    8. Tier 3: Research agents (parallel, with tier1+tier2 context)
       - deep_researcher, community_pulse, knowledge_curator, learning_path_advisor
    9. Fan-in: Final aggregate (waits for all Tier 3 nodes)
    10. Quality gate validation (with retry loop)
    11. Generate artifact
    12. End

    Issue #300: inject_context node runs in parallel with chunk_and_embed and supervisor
    to fetch relevant memories from past analyses and make them available to agents.

    Issue #301: quality_gate node validates synthesis quality using LLM-as-judge
    evaluators and triggers retry if quality falls below threshold (up to 2 retries).

    Issue #441: If extraction fails (should_abort=True), workflow routes to workflow_failed
    node which terminates the workflow early. The conditional edge ensures parallel nodes
    only execute when extraction succeeds.

    Issue #588: Sequential Tier Learning enables later-tier agents to build on earlier
    insights via compressed tier summaries, reducing redundant analysis and saving
    15-30% LLM tokens.

    Returns:
        Compiled StateGraph ready for execution (compiled graph type, not StateGraph)

    """
    # Apply dependency injection defaults
    # Use provided functions/objects or fall back to module defaults
    routing_fn = route_to_agents_fn or route_to_agents
    checkpointer = checkpointer_override or get_checkpointer()

    # Create graph with AnalysisState
    # LangGraph lacks type stubs for TypedDict state
    graph = StateGraph(AnalysisState)  # type: ignore[arg-type]

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
    graph.add_node("workflow_failed", _workflow_failed_node)
    graph.add_node("generate_artifact", generate_artifact)

    # Issue #588: Sequential Tier Learning - Tier aggregate nodes
    # These nodes compress findings from each tier before passing to next tier
    graph.add_node("tier1_aggregate", tier1_aggregate)
    graph.add_node("tier2_aggregate", tier2_aggregate)

    # Add all agent nodes (each executes independently in parallel)
    graph.add_node("actionable", actionable_node)
    graph.add_node("audience_fit", audience_fit_node)
    graph.add_node("key_insights", key_insights_node)
    graph.add_node("pros_cons", pros_cons_node)
    graph.add_node("tech_comparator", tech_comparator_node)
    graph.add_node("security_auditor", security_auditor_node)
    graph.add_node("implementation_planner", implementation_planner_node)
    graph.add_node("performance_analyst", performance_analyst_node)
    graph.add_node("code_quality_critic", code_quality_critic_node)
    graph.add_node("trend_validator", trend_validator_node)
    graph.add_node("dependency_mapper", dependency_mapper_node)
    graph.add_node("integration_feasibility", integration_feasibility_node)
    # Tier 3: Research agents (Deep Dive mode) - Issue #501
    graph.add_node("deep_researcher", deep_researcher_node)
    graph.add_node("community_pulse", community_pulse_node)
    graph.add_node("knowledge_curator", knowledge_curator_node)
    graph.add_node("learning_path_advisor", learning_path_advisor_node)

    # Define edges
    # Sequential: extract must complete first
    graph.set_entry_point("extract")

    # Issue #441: Conditional routing after extraction
    # If extraction failed (should_abort=True), route to workflow_failed
    # Otherwise continue to normal workflow (embedding)
    graph.add_conditional_edges(
        "extract",
        _route_after_extraction,
        {
            "embedding": "embedding",
            "workflow_failed": "workflow_failed",
        },
    )

    # Fan-out: chunk_and_embed, inject_context, and supervisor run in parallel after embedding
    # Issue #441: These nodes must run AFTER embedding (not after extract) to respect abort signal
    # The conditional edge above routes to workflow_failed when should_abort=True,
    # so these nodes only execute when extraction succeeds
    graph.add_edge("embedding", "chunk_and_embed")
    graph.add_edge("embedding", "inject_context")
    graph.add_edge("embedding", "supervisor")

    # ==========================================================================
    # Issue #588: Sequential Tier Learning - Tiered Agent Execution
    # ==========================================================================
    # Agents execute in three sequential tiers with inter-tier context passing.
    # Each tier's findings are compressed and passed to the next tier.
    #
    # Flow: Supervisor → Tier1 → tier1_aggregate → Tier2 → tier2_aggregate
    #                  → Tier3 → aggregate → quality_gate → artifact
    # ==========================================================================

    # Tier 1: Supervisor routes to foundational agents
    # Use custom routing if provided (for backward compatibility tests), otherwise use tiered routing
    if route_to_agents_fn is not None:
        # Backward compatibility: use provided routing function for all agents at once
        # This path is used by existing tests that expect all agents to run in parallel
        graph.add_conditional_edges(
            "supervisor",
            routing_fn,
            [
                # Tier 1: Universal agents
                "actionable",
                "audience_fit",
                "key_insights",
                "pros_cons",
                # Tier 2: Validation agents
                "tech_comparator",
                "security_auditor",
                "implementation_planner",
                "performance_analyst",
                "code_quality_critic",
                "trend_validator",
                "dependency_mapper",
                "integration_feasibility",
                # Tier 3: Research agents
                "deep_researcher",
                "community_pulse",
                "knowledge_curator",
                "learning_path_advisor",
                "aggregate",  # Fallback if no agents selected
            ],
        )
        # Fan-in: All agent nodes route to aggregate in backward compatibility mode
        all_agent_nodes = [
            "actionable",
            "audience_fit",
            "key_insights",
            "pros_cons",
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
            "code_quality_critic",
            "trend_validator",
            "dependency_mapper",
            "integration_feasibility",
            "deep_researcher",
            "community_pulse",
            "knowledge_curator",
            "learning_path_advisor",
        ]
        for agent_node in all_agent_nodes:
            graph.add_edge(agent_node, "aggregate")
    else:
        # Issue #588: Sequential Tier Learning - Tiered execution (default behavior)
        # Tier 1: Foundational agents run first
        graph.add_conditional_edges(
            "supervisor",
            _route_to_tier1_agents,
            [
                "actionable",
                "audience_fit",
                "key_insights",
                "pros_cons",
                "tier1_aggregate",  # Fallback if no Tier 1 agents selected
            ],
        )

        # Tier 1 agents route to tier1_aggregate
        tier1_agent_nodes = ["actionable", "audience_fit", "key_insights", "pros_cons"]
        for agent_node in tier1_agent_nodes:
            graph.add_edge(agent_node, "tier1_aggregate")

        # Tier 2: tier1_aggregate routes to technical agents (with tier1 context)
        graph.add_conditional_edges(
            "tier1_aggregate",
            _route_to_tier2_agents,
            [
                "tech_comparator",
                "security_auditor",
                "implementation_planner",
                "performance_analyst",
                "code_quality_critic",
                "trend_validator",
                "dependency_mapper",
                "integration_feasibility",
                "tier2_aggregate",  # Fallback if no Tier 2 agents selected
            ],
        )

        # Tier 2 agents route to tier2_aggregate
        tier2_agent_nodes = [
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "performance_analyst",
            "code_quality_critic",
            "trend_validator",
            "dependency_mapper",
            "integration_feasibility",
        ]
        for agent_node in tier2_agent_nodes:
            graph.add_edge(agent_node, "tier2_aggregate")

        # Tier 3: tier2_aggregate routes to research agents (with tier1+tier2 context)
        graph.add_conditional_edges(
            "tier2_aggregate",
            _route_to_tier3_agents,
            [
                "deep_researcher",
                "community_pulse",
                "knowledge_curator",
                "learning_path_advisor",
                "aggregate",  # Fallback if no Tier 3 agents selected
            ],
        )

        # Tier 3 agents route to final aggregate
        tier3_agent_nodes = [
            "deep_researcher",
            "community_pulse",
            "knowledge_curator",
            "learning_path_advisor",
        ]
        for agent_node in tier3_agent_nodes:
            graph.add_edge(agent_node, "aggregate")

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

    # Issue #441: Workflow failed -> END (extraction failure terminates workflow)
    graph.add_edge("workflow_failed", END)

    # Sequential: generate_artifact -> end
    graph.add_edge("generate_artifact", END)

    # Compile with checkpointer
    # Use the checkpointer (already set to default if not provided via DI)
    compiled_graph = graph.compile(checkpointer=checkpointer)

    # Set step timeout (in seconds) - LangGraph handles cancellation gracefully
    # This prevents any single node from running indefinitely
    compiled_graph.step_timeout = STEP_TIMEOUT

    # Issue #384: Log graph structure metadata for Langfuse visualization
    # This helps Langfuse infer the graph structure from observation timings
    try:
        from app.core.tracing import update_current_trace

        # Extract node names from compiled graph
        # LangGraph's compiled graph has a nodes attribute with node names
        node_names = list(compiled_graph.nodes.keys()) if hasattr(compiled_graph, "nodes") else []

        # Log graph metadata for Langfuse
        update_current_trace(
            metadata={
                "graph_nodes": node_names,
                "graph_node_count": len(node_names),
                "graph_type": "analysis_workflow",
            }
        )

        logger.info(
            "workflow_graph_compiled_with_metadata",
            step_timeout=STEP_TIMEOUT,
            node_count=len(node_names),
            message="Graph structure metadata logged for Langfuse visualization",
        )
    except Exception as e:  # noqa: BLE001 - Graceful degradation: Langfuse tracing is optional telemetry
        logger.debug(
            "workflow_graph_metadata_logging_failed",
            error=str(e),
            exc_info=e,
            message="Graph metadata logging failed, continuing without it",
        )

    logger.info(
        "workflow_graph_compiled_with_timeout",
        step_timeout=STEP_TIMEOUT,
    )

    return compiled_graph
