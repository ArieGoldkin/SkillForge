"""Integration tests for error event emission across all workflow stages.

Tests verify that error events are emitted and persisted when failures occur
at each stage of the analysis workflow.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import EmbeddingError, WorkflowError
from app.domains.analysis.services.workflow import WorkflowOrchestrator

from .conftest import (
    create_test_analysis,
    verify_analysis_status,
    verify_error_event,
    wait_for_event_persistence,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embedding_failure_emits_error_event(requires_database):
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
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for error event to be persisted
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted to database"

    # Verify error event structure
    await verify_error_event(analysis_id, "embedding", None)

    # Verify analysis status
    await verify_analysis_status(analysis_id, "failed", "embedding", None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_supervisor_failure_emits_error_event(requires_database):
    """Test that supervisor failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-supervisor-failure-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock supervisor to raise error
    with patch(
        "app.domains.analysis.workflows.nodes.supervisor.supervisor_route"
    ) as mock_supervisor:
        mock_supervisor.side_effect = WorkflowError("Supervisor routing failed")

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
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure
    await verify_error_event(analysis_id, "supervisor_routing", None)

    # Verify analysis status
    await verify_analysis_status(analysis_id, "failed", "supervisor_routing", None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_quality_gate_failure_emits_error_event(requires_database):
    """Test that quality gate failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-quality-gate-failure-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock quality gate to fail (return gate_passed=False which triggers error event)
    with patch(
        "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node"
    ) as mock_quality_gate:
        # Quality gate node returns dict with quality_gate_passed=False when it fails
        # The node itself doesn't raise, but emits error event
        # For testing, we'll make it raise an exception to simulate failure
        mock_quality_gate.side_effect = WorkflowError("Quality gate failed")

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
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.supervisor_route",
                return_value={"supervisor_decision": mock_supervisor_decision},
            ),
        ):
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure
    await verify_error_event(analysis_id, "quality_validation", None)

    # Verify analysis status
    await verify_analysis_status(analysis_id, "quality_gate_failed", "quality_validation", None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_failure_emits_error_event(requires_database):
    """Test that agent failure emits error event.

    Note: Agent failures are non-blocking - other agents may still execute.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-agent-failure-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock agent to fail (tech_comparator)
    with patch(
        "app.domains.analysis.workflows.agents.tech_comparator.tech_comparator_agent"
    ) as mock_agent:
        mock_agent.side_effect = WorkflowError("Tech comparator failed")

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
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.supervisor_route",
                return_value={"supervisor_decision": mock_supervisor_decision},
            ),
            patch(
                "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
                return_value={"quality_gate_passed": True},
            ),
        ):
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure
    await verify_error_event(analysis_id, "tech_comparison", None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_aggregation_failure_emits_error_event(requires_database):
    """Test that aggregation failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-aggregation-failure-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock aggregation to fail
    with patch(
        "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings"
    ) as mock_aggregate:
        mock_aggregate.side_effect = WorkflowError("Aggregation failed")

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
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.supervisor_route",
                return_value={"supervisor_decision": mock_supervisor_decision},
            ),
            patch(
                "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
                return_value={"quality_gate_passed": True},
            ),
            patch(
                "app.domains.analysis.workflows.agents.tech_comparator.tech_comparator_agent",
                return_value={"findings": []},
            ),
        ):
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure
    await verify_error_event(analysis_id, "aggregation", None)

    # Verify analysis status
    await verify_analysis_status(analysis_id, "failed", "aggregation", None)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_artifact_failure_emits_error_event(requires_database):
    """Test that artifact generation failure emits error event."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-artifact-failure-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock artifact generation to fail
    with patch(
        "app.domains.analysis.workflows.tasks.generate_artifact.generate_artifact"
    ) as mock_artifact:
        mock_artifact.side_effect = WorkflowError("Artifact generation failed")

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
            patch(
                "app.domains.analysis.workflows.nodes.supervisor.supervisor_route",
                return_value={"supervisor_decision": mock_supervisor_decision},
            ),
            patch(
                "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
                return_value={"quality_gate_passed": True},
            ),
            patch(
                "app.domains.analysis.workflows.agents.tech_comparator.tech_comparator_agent",
                return_value={"findings": []},
            ),
            patch(
                "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings",
                return_value={"aggregated_insights": {}},
            ),
        ):
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error event structure
    await verify_error_event(analysis_id, "artifact_generation", None)

    # Verify analysis status
    await verify_analysis_status(analysis_id, "artifact_failed", "artifact_generation", None)
