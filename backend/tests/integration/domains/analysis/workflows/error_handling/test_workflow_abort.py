"""Integration tests for workflow abort behavior.

Tests verify that when failures occur, abort signals properly stop
subsequent workflow nodes from executing.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import EmbeddingError, WorkflowError
from app.domains.analysis.services.workflow import WorkflowOrchestrator
from app.domains.analysis.workflows.analysis import create_analysis_workflow

from .conftest import create_test_analysis


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embedding_failure_stops_workflow(requires_database, reset_engine_connections):
    """Test that embedding failure stops workflow (abort signal).

    The orchestrator catches WorkflowStageError and handles it gracefully:
    - Status is set to 'failed'
    - Error event is emitted
    - Exception is NOT re-raised (workflow completes gracefully)
    - Subsequent nodes are skipped
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-embedding-abort-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Track which nodes were called
    nodes_called = {
        "supervisor": False,
        "quality_gate": False,
        "aggregate": False,
        "artifact": False,
    }

    # Mock nodes to track calls
    async def mock_supervisor_node(state):
        nodes_called["supervisor"] = True
        return {"supervisor_decision": {"agents": ["tech_comparator"]}}

    async def mock_quality_gate_node(state):
        nodes_called["quality_gate"] = True
        return {"quality_gate_passed": True}

    async def mock_aggregate_node(state):
        nodes_called["aggregate"] = True
        return {"aggregated_insights": {}}

    async def mock_artifact_node(state):
        nodes_called["artifact"] = True
        return {"artifact_id": str(uuid.uuid4())}

    # Mock embedding to fail
    mock_embedding_service = MagicMock()
    mock_embedding_service.generate_embedding = AsyncMock(
        side_effect=EmbeddingError("Embedding failed")
    )
    mock_embedding_service.close = AsyncMock()  # Must be AsyncMock for await

    # Mock extraction to succeed
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
            side_effect=mock_supervisor_node,
        ),
        patch(
            "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
            side_effect=mock_quality_gate_node,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings",
            side_effect=mock_aggregate_node,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_artifact.generate_artifact",
            side_effect=mock_artifact_node,
        ),
    ):
        workflow = create_analysis_workflow()
        orchestrator = WorkflowOrchestrator(workflow=workflow)
        # The orchestrator catches WorkflowStageError and handles it gracefully
        # No exception should be raised
        await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify subsequent nodes were NOT called
    assert nodes_called["supervisor"] is False, "Supervisor should be skipped when embedding fails"
    assert nodes_called["quality_gate"] is False, (
        "Quality gate should be skipped when embedding fails"
    )
    assert nodes_called["aggregate"] is False, "Aggregate should be skipped when embedding fails"
    assert nodes_called["artifact"] is False, "Artifact should be skipped when embedding fails"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_supervisor_failure_stops_workflow(requires_database, reset_engine_connections):
    """Test that supervisor failure stops workflow.

    Note: Under pytest-xdist parallel load, worker crashes can occur if resources
    aren't properly cleaned up. This test uses try/finally to ensure proper cleanup.
    """
    import asyncio

    analysis_id = uuid.uuid4()
    test_url = f"https://test-supervisor-abort-{analysis_id}.com"

    # Supervisor runs after extraction/embedding, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Track nodes
    nodes_called = {"quality_gate": False, "aggregate": False, "artifact": False}

    async def mock_quality_gate_node(state):
        nodes_called["quality_gate"] = True
        return {"quality_gate_passed": True}

    async def mock_aggregate_node(state):
        nodes_called["aggregate"] = True
        return {"aggregated_insights": {}}

    async def mock_artifact_node(state):
        nodes_called["artifact"] = True
        return {"artifact_id": str(uuid.uuid4())}

    # Mock supervisor to fail
    with (
        patch(
            "app.domains.analysis.workflows.nodes.supervisor.supervisor_route",
            side_effect=WorkflowError("Supervisor failed"),
        ),
        patch(
            "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
            side_effect=mock_quality_gate_node,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings",
            side_effect=mock_aggregate_node,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_artifact.generate_artifact",
            side_effect=mock_artifact_node,
        ),
    ):
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
            finally:
                # Allow pending async tasks to complete to prevent worker crashes
                await asyncio.sleep(0.05)

    # Verify subsequent nodes were NOT called
    assert nodes_called["quality_gate"] is False, "Quality gate should be skipped"
    assert nodes_called["aggregate"] is False, "Aggregate should be skipped"
    assert nodes_called["artifact"] is False, "Artifact should be skipped"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_quality_gate_failure_stops_workflow(requires_database, reset_engine_connections):
    """Test that quality gate failure stops workflow."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-quality-gate-abort-{analysis_id}.com"

    # Quality gate runs after supervisor, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Track nodes
    nodes_called = {"aggregate": False, "artifact": False}

    async def mock_aggregate_node(state):
        nodes_called["aggregate"] = True
        return {"aggregated_insights": {}}

    async def mock_artifact_node(state):
        nodes_called["artifact"] = True
        return {"artifact_id": str(uuid.uuid4())}

    # Mock quality gate to fail
    with (
        patch(
            "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
            side_effect=WorkflowError("Quality gate failed"),
        ),
        patch(
            "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings",
            side_effect=mock_aggregate_node,
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_artifact.generate_artifact",
            side_effect=mock_artifact_node,
        ),
    ):
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
        ):
            workflow = create_analysis_workflow()
            orchestrator = WorkflowOrchestrator(workflow=workflow)
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify subsequent nodes were NOT called
    assert nodes_called["aggregate"] is False, "Aggregate should be skipped"
    assert nodes_called["artifact"] is False, "Artifact should be skipped"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_aggregation_failure_stops_workflow(requires_database, reset_engine_connections):
    """Test that aggregation failure stops workflow."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-aggregation-abort-{analysis_id}.com"

    # Aggregation runs after agents, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Track artifact node
    artifact_called = False

    async def mock_artifact_node(state):
        nonlocal artifact_called
        artifact_called = True
        return {"artifact_id": str(uuid.uuid4())}

    # Mock aggregation to fail
    with (
        patch(
            "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings",
            side_effect=WorkflowError("Aggregation failed"),
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_artifact.generate_artifact",
            side_effect=mock_artifact_node,
        ),
    ):
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
                "app.domains.analysis.workflows.agents.tech_comparator.run_tech_comparator",
                return_value={"findings": []},
            ),
        ):
            workflow = create_analysis_workflow()
            orchestrator = WorkflowOrchestrator(workflow=workflow)
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify artifact was NOT called
    assert artifact_called is False, "Artifact should be skipped when aggregation fails"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_failure_does_not_stop_workflow(requires_database, reset_engine_connections):
    """Test that agent failure does NOT stop workflow (agents are non-blocking).

    When an agent fails, the agent node catches the exception and returns empty findings.
    The workflow continues to aggregation even though one agent produced no results.
    This is the expected behavior for resilient workflow execution.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-agent-non-blocking-{analysis_id}.com"

    # Agents run after quality gate, so status should be "analyzing"
    await create_test_analysis(analysis_id, test_url, initial_status="analyzing")

    # Track if aggregation was called (workflow continued)
    aggregation_called = False
    artifact_called = False

    async def mock_aggregate_node(state):
        nonlocal aggregation_called
        aggregation_called = True
        return {"aggregated_insights": {"summary": "Test aggregation"}}

    async def mock_artifact_node(state):
        nonlocal artifact_called
        artifact_called = True
        return {"artifact_id": str(uuid.uuid4())}

    # Mock agent runner to fail (not the node itself - the node catches exceptions)
    # The agent node will catch this and return empty findings
    with (
        patch(
            "app.domains.analysis.workflows.tasks.runners.run_tech_comparator_with_session",
            side_effect=Exception("Tech comparator failed"),
        ),
        patch(
            "app.domains.analysis.workflows.graph_builder.aggregate_findings",
            side_effect=mock_aggregate_node,
        ),
        patch(
            "app.domains.analysis.workflows.graph_builder.generate_artifact",
            side_effect=mock_artifact_node,
        ),
    ):
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
            workflow = create_analysis_workflow()
            orchestrator = WorkflowOrchestrator(workflow=workflow)
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify aggregation WAS called (workflow continued despite agent failure)
    assert aggregation_called is True, (
        "Aggregation should be called even if agent fails (non-blocking)"
    )
    # Verify artifact was also generated (workflow completed fully)
    assert artifact_called is True, (
        "Artifact should be generated even if agent fails (workflow completes)"
    )
