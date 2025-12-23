"""Integration tests for error event emission across all workflow stages.

Tests verify that error events are emitted and persisted when failures occur
at each stage of the analysis workflow.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langgraph.types import Send

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
                pass

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
    """Test that quality gate failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-quality-gate-failure-{analysis_id}.com"

    # Quality gate runs after supervisor, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Quality gate only emits error events when GATE FAILS (scores too low), not on exceptions
    # When exceptions occur, it returns gracefully (fail-open) without emitting error events
    # So we need to test actual gate failure by making evaluators return low scores
    # Quality gate evaluates 3 aspects (relevance, depth, coherence) in a loop
    # Mock at the point where evaluator is called (after create_quality_evaluator)
    with patch(
        "app.domains.analysis.workflows.nodes.quality_gate_node.create_quality_evaluator"
    ) as mock_evaluator_factory:
        # Mock evaluator to return low scores (below threshold 0.7) to trigger gate failure
        # create_quality_evaluator returns a callable function that takes (run, example) and returns dict
        # We need to return a callable that when called returns low scores
        async def mock_evaluator_func(run: object, example: object) -> dict[str, object]:
            """Mock evaluator that returns low scores to trigger gate failure."""
            return {"score": 0.5, "comment": "Low quality - test failure"}

        # create_quality_evaluator should return this callable
        mock_evaluator_factory.return_value = mock_evaluator_func

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

    # Verify analysis status - orchestrator uses generic "failed" status
    # Note: failed_at_stage may not be set when quality gate fails (workflow continues)
    # Just verify status is failed
    await verify_analysis_status(analysis_id, "failed", None, None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that agent failure emits error event.

    Note: Agent failures are non-blocking - other agents may still execute.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-agent-failure-{analysis_id}.com"

    # Agents run after quality gate, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Mock supervisor to return specific agents
    async def mock_supervisor_node(state):
        return {"supervisor_decision": {"agents": ["tech_comparator"]}}

    # Build test graph with mocked supervisor
    test_workflow = build_test_graph(supervisor_mock=mock_supervisor_node)

    # Create orchestrator with test workflow (required)
    orchestrator = WorkflowOrchestrator(workflow=test_workflow)

    # Mock agent node to fail (tech_comparator_node catches and emits progress event)
    # Mock the runner that tech_comparator_node calls - this will trigger its exception handler
    with (
        patch(
            "app.domains.analysis.workflows.nodes.agents.tech_comparator_node.run_tech_comparator_with_session"
        ) as mock_runner,
        mock_downstream_stages,  # Prevent continuation
        patch(
            "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
            return_value=MagicMock(
                extract_article=AsyncMock(
                    return_value={
                        "content": "Test content",
                        "title": "Test Title",
                        "word_count": 10,
                        "metadata": {
                            "title": "Test Title",
                            "content_type": "article",
                            "word_count": 10,
                        },
                    }
                ),
                close=AsyncMock(),
            ),
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_embedding.EmbeddingService",
            return_value=MagicMock(
                generate_embedding=AsyncMock(return_value=[0.1] * 1536),
                close=AsyncMock(),
            ),
        ),
    ):
        mock_runner.side_effect = WorkflowError("Tech comparator failed")
        await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for event - agents emit progress events with status="failed", not error events
    # Give time for async persistence to complete
    import asyncio

    await asyncio.sleep(0.5)  # Allow async persistence task to complete

    event_found = await wait_for_event_persistence(analysis_id, "progress", max_wait=10.0)
    assert event_found, "Progress event should be persisted"

    # Verify progress event with status="failed" structure
    # Agents emit progress events (not error events) when they fail
    # tech_comparator_node calls run_tech_comparator_with_session which we mocked to raise
    await verify_progress_event_failed(analysis_id, "tech_comparison")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_aggregation_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that aggregation failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-aggregation-failure-{analysis_id}.com"

    # Aggregation runs after agents, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Aggregation emits error events when synthesis fails
    # synthesize_with_llm has fallback tiers, so mock a function that actually raises
    # Mock the validation function to raise - this will trigger aggregation's error handler
    # which emits error event and returns fallback data (workflow continues)
    with patch(
        "app.domains.analysis.workflows.tasks.aggregation.validation.validate_and_parse_findings"
    ) as mock_validate:
        # Raise exception that will be caught by aggregation's error handler
        mock_validate.side_effect = WorkflowError("Validation failed")

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

    # Wait for error event - aggregation emits error events even though workflow continues
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure - use verify_error_event which searches by stage
    # This handles the case where workflow continues and later errors occur
    await verify_error_event(analysis_id, "aggregation", "AGGREGATION_FAILED")

    # Verify analysis status - aggregation errors don't set failed_at_stage because workflow continues
    # The workflow eventually fails elsewhere, so status may be "failed" but failed_at_stage may be None
    # or set to a later stage that caused the final failure
    # Aggregation errors are non-blocking, so status might not be "failed" immediately
    # Just verify error event was emitted (verified above)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_artifact_failure_emits_error_event(requires_database, reset_engine_connections):
    """Test that artifact generation failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-artifact-failure-{analysis_id}.com"

    # Artifact generation runs after aggregation, so status should be "generating_artifact"
    await create_test_analysis(analysis_id, test_url, initial_status="generating_artifact")

    # Mock artifact generation to fail - generate_artifact emits error event and raises WorkflowStageError
    # Mock the template rendering which happens early in generate_artifact
    # Must patch where it's used, not where it's defined
    with patch(
        "app.domains.analysis.workflows.tasks.generate_artifact.render_jinja_template"
    ) as mock_render:
        mock_render.side_effect = WorkflowError("Template rendering failed")

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
            try:
                await orchestrator.run(analysis_id, test_url, skill_level="intermediate")
            except (WorkflowStageError, WorkflowError):
                # Expected - generate_artifact wraps exception in WorkflowStageError
                pass
            except Exception as e:
                # Catch any exception - artifact generation should fail
                pass

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure - use verify_error_event which searches by stage
    # This finds artifact_generation error even if workflow continues and other errors occur
    await verify_error_event(analysis_id, "artifact_generation", "ARTIFACT_GENERATION_FAILED")

    # Verify analysis status - orchestrator sets to "failed" when WorkflowStageError is raised
    await verify_analysis_status(analysis_id, "failed", None, None)
