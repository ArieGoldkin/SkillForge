"""Integration tests for abort signal propagation.

Tests verify that when extraction fails (should_abort=True), all subsequent
workflow nodes are skipped and workflow routes to workflow_failed node.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ExtractionErrorCode, JinaReaderError
from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal
from app.domains.analysis.workflows.analysis import create_analysis_workflow
from app.domains.analysis.workflows.state import AnalysisState


@pytest.fixture
def requires_database():
    """Skip test if DATABASE_URL is not set."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_abort_signal_stops_subsequent_nodes(requires_database, reset_engine_connections):
    """Test that extraction failure stops all subsequent nodes.

    When extraction fails:
    1. should_abort=True is set in state
    2. Embedding node should be skipped
    3. Supervisor node should be skipped
    4. Quality gate node should be skipped
    5. Workflow should route to workflow_failed node
    """
    analysis_id = str(uuid.uuid4())
    test_url = f"https://invalid-url-{analysis_id}.com"  # Unique URL to avoid constraint violations

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=uuid.UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Mock Jina to raise JinaReaderError (simulating extraction failure)
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        side_effect=JinaReaderError(
            "Extraction failed", error_code=ExtractionErrorCode.NETWORK_ERROR
        )
    )
    mock_jina.close = AsyncMock()

    # Track which nodes were called
    nodes_called = {
        "embedding": False,
        "supervisor": False,
        "quality_gate": False,
        "aggregate": False,
        "artifact": False,
    }

    # Mock embedding node to track if it's called
    async def mock_embedding_node(state: AnalysisState) -> dict:
        nodes_called["embedding"] = True
        return {"content_embedding": [0.1] * 1536}

    # Mock supervisor node to track if it's called
    async def mock_supervisor_node(state: AnalysisState) -> dict:
        nodes_called["supervisor"] = True
        return {"supervisor_decision": {"agents": ["tech_comparator"]}}

    # Mock quality gate node to track if it's called
    async def mock_quality_gate_node(state: AnalysisState) -> dict:
        nodes_called["quality_gate"] = True
        return {"quality_gate_passed": True}

    # Mock aggregate node to track if it's called
    async def mock_aggregate_node(state: AnalysisState) -> dict:
        nodes_called["aggregate"] = True
        return {"aggregated_insights": {}}

    # Mock artifact node to track if it's called
    async def mock_artifact_node(state: AnalysisState) -> dict:
        nodes_called["artifact"] = True
        return {"artifact_id": str(uuid.uuid4())}

    with (
        patch("app.domains.analysis.workflows.tasks.extract_content.JinaReader") as mock_jina_class,
        patch(
            "app.domains.analysis.workflows.graph_builder._generate_embedding_node",
            side_effect=mock_embedding_node,
        ),
        patch(
            "app.domains.analysis.workflows.graph_builder._supervisor_node",
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
        mock_jina_class.return_value = mock_jina

        # Run workflow
        input_state: dict[str, str] = {
            "url": test_url,
            "analysis_id": analysis_id,
            "skill_level": "intermediate",
        }

        config = {
            "configurable": {
                "thread_id": analysis_id,
            },
        }

        workflow = create_analysis_workflow()
        result = await workflow.ainvoke(input_state, config=config)

        # Verify should_abort is set
        assert result.get("should_abort") is True
        assert result.get("abort_reason") is not None
        assert result.get("extraction_status") == "failed"

        # Verify subsequent nodes were NOT called
        assert nodes_called["embedding"] is False, "Embedding node should be skipped when aborting"
        assert nodes_called["supervisor"] is False, (
            "Supervisor node should be skipped when aborting"
        )
        assert nodes_called["quality_gate"] is False, (
            "Quality gate node should be skipped when aborting"
        )
        assert nodes_called["aggregate"] is False, "Aggregate node should be skipped when aborting"
        assert nodes_called["artifact"] is False, "Artifact node should be skipped when aborting"

        # Verify workflow_status is failed
        assert result.get("workflow_status") == "failed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_abort_signal_routes_to_workflow_failed(requires_database):
    """Test that abort signal routes workflow to workflow_failed node.

    Note: The workflow_failed node is called internally by LangGraph.
    We verify routing by checking the final state and database status.
    """
    analysis_id = str(uuid.uuid4())
    test_url = f"https://invalid-url-{analysis_id}.com"  # Unique URL to avoid constraint violations

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=uuid.UUID(analysis_id),
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Mock Jina to raise error
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        side_effect=JinaReaderError(
            "Extraction failed", error_code=ExtractionErrorCode.NETWORK_ERROR
        )
    )
    mock_jina.close = AsyncMock()

    with patch(
        "app.domains.analysis.workflows.tasks.extract_content.JinaReader"
    ) as mock_jina_class:
        mock_jina_class.return_value = mock_jina

        input_state: dict[str, str] = {
            "url": test_url,
            "analysis_id": analysis_id,
            "skill_level": "intermediate",
        }

        config = {
            "configurable": {
                "thread_id": analysis_id,
            },
        }

        workflow = create_analysis_workflow()
        result = await workflow.ainvoke(input_state, config=config)

        # Verify abort signal is set
        assert result.get("should_abort") is True
        assert result.get("workflow_status") == "failed"
        assert result.get("final_error") is not None

        # Verify database was updated (workflow_failed node persists failure)
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select

            stmt = select(Analysis).where(Analysis.id == uuid.UUID(analysis_id))
            result_db = await session.execute(stmt)
            analysis_db = result_db.scalar_one()

            assert analysis_db.status == "failed"
            assert analysis_db.error_code == "NETWORK_ERROR"
            assert analysis_db.failed_at_stage == "extraction"
