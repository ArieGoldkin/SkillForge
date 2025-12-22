"""Integration tests for SSE event emission and retrieval.

Tests verify that error events are properly emitted to the EventBroadcaster
and are retrievable via the /progress endpoint (simulated via repository).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ExtractionErrorCode, JinaReaderError
from app.db.session import AsyncSessionLocal
from app.domains.analysis.services.workflow import WorkflowOrchestrator

from .conftest import create_test_analysis, wait_for_event_persistence


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_event_emitted_to_broadcaster(requires_database):
    """Test that error events are emitted to EventBroadcaster.

    This test verifies that events are published to the broadcaster,
    making them available for SSE streams.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-sse-emission-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock extraction to fail
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        side_effect=JinaReaderError(
            "Extraction failed", error_code=ExtractionErrorCode.NETWORK_ERROR
        )
    )
    mock_jina.close = AsyncMock()

    with patch(
        "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
        return_value=mock_jina,
    ):
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify error event was persisted (which means it was emitted)
    event_found = await wait_for_event_persistence(analysis_id, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted (emitted to broadcaster)"

    # Verify event is retrievable via repository (simulating /progress endpoint)
    from app.db.repositories.analysis_repository import AnalysisRepository

    async with AsyncSessionLocal() as session:
        repo = AnalysisRepository(session)
        progress_events = await repo.get_progress_events(analysis_id)

        # Find error event
        error_events = [
            event
            for event in progress_events
            if isinstance(event.progress_data, dict) and event.progress_data.get("type") == "error"
        ]

        assert len(error_events) > 0, "Error event should be retrievable via repository"
        error_event = error_events[0]

        # Verify event structure matches SSE schema
        assert error_event.stage == "extraction"
        assert error_event.status == "failed"
        assert isinstance(error_event.progress_data, dict)
        assert error_event.progress_data.get("type") == "error"
        assert error_event.progress_data.get("error_code") == "NETWORK_ERROR"
        assert "error" in error_event.progress_data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_event_retrievable_via_sse_stream(requires_database):
    """Test that error events are retrievable via SSE stream endpoint.

    This test verifies the full flow: error event → database → /progress endpoint.
    """
    analysis_id = uuid.uuid4()
    test_url = f"https://test-sse-stream-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    # Mock extraction to fail
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        side_effect=JinaReaderError(
            "Extraction failed", error_code=ExtractionErrorCode.NETWORK_ERROR
        )
    )
    mock_jina.close = AsyncMock()

    with patch(
        "app.domains.analysis.workflows.tasks.extract_content.JinaReader",
        return_value=mock_jina,
    ):
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(analysis_id, test_url, skill_level="intermediate")

    # Verify event is retrievable via repository (simulating /progress endpoint)
    from app.db.repositories.analysis_repository import AnalysisRepository

    async with AsyncSessionLocal() as session:
        repo = AnalysisRepository(session)
        progress_events = await repo.get_progress_events(analysis_id)

        # Find error event
        error_events = [
            event
            for event in progress_events
            if isinstance(event.progress_data, dict) and event.progress_data.get("type") == "error"
        ]

        assert len(error_events) > 0, "Error event should be retrievable"

        error_event = error_events[0]

        # Verify event format matches SSE schema (what frontend expects)
        event_data = error_event.progress_data
        assert event_data.get("type") == "error"
        assert event_data.get("status") == "failed"
        assert event_data.get("stage") == "extraction"
        assert event_data.get("error_code") == "NETWORK_ERROR"
        assert "error" in event_data
        assert "timestamp" in event_data
        assert "analysis_id" in event_data
