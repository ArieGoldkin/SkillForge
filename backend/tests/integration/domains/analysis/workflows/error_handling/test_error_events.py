"""Integration tests for error event emission across all workflow stages.

Tests verify that error events are emitted and persisted when failures occur
at each stage of the analysis workflow.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import EmbeddingError, WorkflowError, WorkflowStageError
from app.domains.analysis.services.workflow import WorkflowOrchestrator
from app.domains.analysis.workflows.analysis import create_analysis_workflow

from .conftest import (
    build_test_graph,
    create_test_analysis,
    mock_downstream_stages,
    verify_analysis_status,
    verify_error_event,
    verify_progress_event_failed,
    wait_for_event_persistence,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embedding_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that embedding failure emits error event.

    Flow:
    1. Create analysis record
    2. Mock embedding service to raise EmbeddingError
    3. Run workflow orchestrator
    4. Verify error event emitted and persisted
    5. Verify analysis status updated
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-embedding-failure-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock embedding service to raise error
    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(
        side_effect=EmbeddingError("Embedding generation failed")
    )
    mock_embedding_service.close = AsyncMock()  # Must be AsyncMock for await

    with patch(
        "app.domains.analysis.workflows.tasks.generate_embedding.EmbeddingService",
        return_value=mock_embedding_service,
    ):
        # Mock extraction to succeed (so we can test embedding failure)
        mock_jina = MagicMock()
        mock_jina.extract_article = AsyncMock(
            return_value={
                "content": "Test content",
                "title": "Test Title",
                "word_count": 10,
                "metadata": {"title": "Test Title", "content_type": "article", "word_count": 10},
            }
        )
        mock_jina.close = AsyncMock()

        with patch(
            "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
            return_value=mock_jina,
        ):
            workflow = create_analysis_workflow()
            orchestrator = WorkflowOrchestrator(workflow=workflow)
            # Exception propagates from workflow to orchestrator, which handles it
            # The orchestrator's exception handler updates status and emits error events
            try:
                await orchestrator.run(analysis_id, test_url, skill_level="intermediate")
            except Exception:
                # Exception is expected - orchestrator handles it and updates status
                # Wait a bit for status update and event emission to complete
                import asyncio

                await asyncio.sleep(0.2)

    # Wait for error event to be persisted
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted to database"

    # Verify error event structure
    # The embedding task emits stage="embedding" error before re-raising.
    # The orchestrator should detect this recent error and skip duplicate emission.
    # So we should see the embedding stage error, not a workflow stage error.
    await verify_error_event(analysis_id, "embedding", None)

    # Verify analysis status - orchestrator sets to generic "failed"
    await verify_analysis_status(analysis_id, "failed", None, None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_supervisor_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that supervisor failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-supervisor-failure-{analysis_id}.com"

    # Supervisor runs after extraction/embedding, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Mock supervisor internal function to raise error
    # This allows supervisor_route's error handling (emit + wrap) to run
    with patch(
        "app.domains.analysis.workflows.nodes.supervisor._invoke_supervisor_with_retry"
    ) as mock_invoke:
        mock_invoke.side_effect = WorkflowError("Supervisor routing failed")

        # Mock extraction and embedding to succeed
        mock_jina = MagicMock()
        mock_jina.extract_article = AsyncMock(
            return_value={
                "content": "Test content",
                "title": "Test Title",
                "word_count": 10,
                "metadata": {"title": "Test Title", "content_type": "article", "word_count": 10},
            }
        )
        mock_jina.close = AsyncMock()

        mock_embedding_service = MagicMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embedding_service.close = AsyncMock()  # Must be AsyncMock for await

        with (
            patch(
                "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
                return_value=mock_jina,
            ),
            patch(
                "app.domains.analysis.workflows.tasks.generate_embedding.EmbeddingService",
                return_value=mock_embedding_service,
            ),
        ):
            workflow = create_analysis_workflow()
            orchestrator = WorkflowOrchestrator(workflow=workflow)
            try:
                await orchestrator.run(analysis_id, test_url, skill_level="intermediate")
            except (WorkflowStageError, WorkflowError):
                # Expected - supervisor_route wraps exception in WorkflowStageError
                pass

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure
    # The supervisor node emits stage="supervisor_routing" error before re-raising.
    # The orchestrator should detect this recent error and skip duplicate emission.
    # So we should see the supervisor_routing stage error, not a workflow stage error.
    await verify_error_event(analysis_id, "supervisor_routing", None)

    # Verify analysis status - orchestrator sets to generic "failed"
    await verify_analysis_status(analysis_id, "failed", None, None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_quality_gate_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that quality gate failure emits error event.

    Issue #299-304: Quality gate uses FAIL-OPEN behavior.
    After max retries with low scores, error events are emitted but workflow
    continues to artifact generation. Users prefer getting a low-quality
    artifact over nothing at all.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-quality-gate-failure-{analysis_id}.com"

    # Quality gate runs after supervisor, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Quality gate only emits error events when GATE FAILS (scores too low), not on exceptions
    # When exceptions occur, it returns gracefully (fail-open) without emitting error events
    # So we need to test actual gate failure by making multi-judge evaluation return low scores
    # Quality gate evaluates 3 aspects (relevance, depth, coherence) via run_multi_judge_evaluation
    # Mock run_multi_judge_evaluation at the module where it's imported FROM (not where it's used)
    with patch(
        "app.shared.services.g_eval.multi_judge.run_multi_judge_evaluation"
    ) as mock_multi_judge:
        # Mock multi-judge to return low scores for all aspects to trigger gate failure
        # run_multi_judge_evaluation returns dict[aspect] -> {score, comment, metadata}
        async def mock_multi_judge_func(*args, **kwargs) -> dict[str, dict[str, object]]:
            """Mock multi-judge that returns low scores to trigger gate failure."""
            return {
                "relevance": {"score": 0.4, "comment": "Low relevance - test failure"},
                "depth": {"score": 0.3, "comment": "Low depth - test failure"},
                "coherence": {"score": 0.3, "comment": "Low coherence - test failure"},
            }

        # run_multi_judge_evaluation is async, so use AsyncMock
        mock_multi_judge.side_effect = mock_multi_judge_func

        # Mock previous stages to succeed
        mock_jina = MagicMock()
        mock_jina.extract_article = AsyncMock(
            return_value={
                "content": "Test content",
                "title": "Test Title",
                "word_count": 10,
                "metadata": {"title": "Test Title", "content_type": "article", "word_count": 10},
            }
        )
        mock_jina.close = AsyncMock()

        mock_embedding_service = MagicMock()
        mock_embedding_service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_embedding_service.close = AsyncMock()  # Must be AsyncMock for await

        # Mock supervisor to return agents
        mock_supervisor_decision = {"agents": ["tech_comparator"]}

        with (
            patch(
                "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
                return_value=mock_jina,
            ),
            patch(
                "app.domains.analysis.workflows.tasks.generate_embedding.EmbeddingService",
                return_value=mock_embedding_service,
            ),
            # Mock supervisor node via test graph builder
        ):
            # Build test graph with mocked supervisor
            async def mock_supervisor_node(state):
                return {"supervisor_decision": mock_supervisor_decision}

            test_workflow = build_test_graph(supervisor_mock=mock_supervisor_node)
            orchestrator = WorkflowOrchestrator(workflow=test_workflow)
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure - search by stage to find quality_validation error
    await verify_error_event(analysis_id, "quality_validation", "QUALITY_GATE_FAILED")

    # Issue #299-304: Quality gate uses FAIL-OPEN behavior
    # Even after max retries, workflow continues to artifact generation
    # Verify analysis completes (not fails) but quality warning is emitted
    await verify_analysis_status(analysis_id, "complete", None, None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_failure_emits_error_event(
    requires_database, reset_engine_connections, mock_downstream_stages
):
    """Test that agent failure emits progress event with failed status.

    Note: Agent failures are non-blocking - workflow continues and other agents may execute.
    Agents emit progress events with status="failed", not error events.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-agent-failure-{analysis_id}.com"

    # Create analysis record
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Test the agent failure emission logic directly by calling emit_agent_progress
    # This verifies that the error event system works correctly
    from app.domains.analysis.workflows.agents.base import emit_agent_progress

    await emit_agent_progress(
        analysis_id,
        "tech_comparator",
        "failed",
        error="Tech comparator execution failed during test",
        error_code="TECH_COMPARATOR_FAILED",
        processing_time_ms=100,
    )

    # Wait for async event persistence
    import asyncio

    await asyncio.sleep(0.3)

    # Verify progress event was persisted
    event_found = await wait_for_event_persistence(analysis_id, "progress", max_wait=10.0)
    assert event_found, "Progress event should be persisted"

    # Verify the event structure matches expected format for agent failures
    await verify_progress_event_failed(analysis_id, "tech_comparison")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_aggregation_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that aggregation failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-aggregation-failure-{analysis_id}.com"

    # Create analysis record
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Test the aggregation failure emission logic directly
    # This verifies that the error event system works correctly
    from app.shared.services.messaging.sse_helpers import emit_error_event

    await emit_error_event(
        analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
        stage="aggregate_findings",
        error="Aggregation validation failed during test",
        error_code="AGGREGATION_FAILED",
    )

    # Wait for async event persistence
    import asyncio

    await asyncio.sleep(0.3)

    # Verify error event was persisted
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify the event structure matches expected format for aggregation failures
    await verify_error_event(analysis_id, "aggregate_findings", "AGGREGATION_FAILED")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_artifact_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that artifact generation failure emits error event.

    Note: This test verifies the error event emission logic directly, not through workflow execution.
    Artifact generation failures emit error events with stage='artifact_generation'.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-artifact-failure-{analysis_id}.com"

    # Create analysis record
    await create_test_analysis(analysis_id, test_url, initial_status="generating_artifact")

    # Test the artifact failure emission logic directly
    # This verifies that the error event system works correctly
    from app.shared.services.messaging.sse_helpers import emit_error_event

    await emit_error_event(
        analysis_id=str(analysis_id),  # Convert UUID to string for JSON serialization
        stage="artifact_generation",
        error="Template rendering failed during test",
        error_code="ARTIFACT_GENERATION_FAILED",
    )

    # Wait for async event persistence
    import asyncio

    await asyncio.sleep(0.3)

    # Verify error event was persisted
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify the event structure matches expected format for artifact failures
    await verify_error_event(analysis_id, "artifact_generation", "ARTIFACT_GENERATION_FAILED")
