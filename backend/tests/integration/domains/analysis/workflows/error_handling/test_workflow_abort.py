"""Integration tests for workflow abort behavior.

Tests verify that when failures occur, abort signals properly stop
subsequent workflow nodes from executing.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import EmbeddingError, WorkflowError
from app.domains.analysis.services.workflow import WorkflowOrchestrator

from .conftest import create_test_analysis


@pytest.mark.asyncio
@pytest.mark.integration
async def test_embedding_failure_stops_workflow(requires_database):
    """Test that embedding failure stops workflow (abort signal)."""
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
            "app.domains.analysis.workflows.nodes.supervisor.supervisor_node",
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
        orchestrator = WorkflowOrchestrator()
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
async def test_supervisor_failure_stops_workflow(requires_database):
    """Test that supervisor failure stops workflow."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-supervisor-abort-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

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
            "app.domains.analysis.workflows.nodes.supervisor.supervisor_node",
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
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify subsequent nodes were NOT called
    assert nodes_called["quality_gate"] is False, "Quality gate should be skipped"
    assert nodes_called["aggregate"] is False, "Aggregate should be skipped"
    assert nodes_called["artifact"] is False, "Artifact should be skipped"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_quality_gate_failure_stops_workflow(requires_database):
    """Test that quality gate failure stops workflow."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-quality-gate-abort-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

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
                "app.domains.analysis.workflows.nodes.supervisor.supervisor_node",
                return_value={"supervisor_decision": mock_supervisor_decision},
            ),
        ):
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify subsequent nodes were NOT called
    assert nodes_called["aggregate"] is False, "Aggregate should be skipped"
    assert nodes_called["artifact"] is False, "Artifact should be skipped"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_aggregation_failure_stops_workflow(requires_database):
    """Test that aggregation failure stops workflow."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-aggregation-abort-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

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
                "app.domains.analysis.workflows.nodes.supervisor.supervisor_node",
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

    # Verify artifact was NOT called
    assert artifact_called is False, "Artifact should be skipped when aggregation fails"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_agent_failure_does_not_stop_workflow(requires_database):
    """Test that agent failure does NOT stop workflow (agents are non-blocking).

    When an agent fails, other agents may still execute and workflow continues.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-agent-non-blocking-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Track if aggregation was called (workflow continued)
    aggregation_called = False

    async def mock_aggregate_node(state):
        nonlocal aggregation_called
        aggregation_called = True
        return {"aggregated_insights": {}}

    # Mock agent to fail
    with (
        patch(
            "app.domains.analysis.workflows.agents.tech_comparator.tech_comparator_agent",
            side_effect=WorkflowError("Tech comparator failed"),
        ),
        patch(
            "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings",
            side_effect=mock_aggregate_node,
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
                "app.domains.analysis.workflows.nodes.supervisor.supervisor_node",
                return_value={"supervisor_decision": mock_supervisor_decision},
            ),
            patch(
                "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
                return_value={"quality_gate_passed": True},
            ),
        ):
            orchestrator = WorkflowOrchestrator()
            await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify aggregation WAS called (workflow continued despite agent failure)
    assert aggregation_called is True, (
        "Aggregation should be called even if agent fails (non-blocking)"
    )
