"""Integration tests for error event persistence.

Tests verify that error events are:
1. Emitted when workflow failures occur
2. Persisted to the analysis_progress table
3. Retrievable via the /progress endpoint
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.exceptions import ExtractionErrorCode, JinaReaderError
from app.db.models.analysis import Analysis
from app.db.models.progress import AnalysisProgress
from app.db.session import AsyncSessionLocal
from app.domains.analysis.services.workflow import WorkflowOrchestrator


@pytest.fixture
def requires_database():
    """Skip test if DATABASE_URL is not set."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


async def wait_for_event_persistence(
    analysis_id: uuid.UUID, event_type: str, max_wait: float = 5.0
) -> bool:
    """Wait for an event to be persisted to the database.

    Args:
        analysis_id: UUID of the analysis
        event_type: Type of event to wait for (e.g., "error")
        max_wait: Maximum time to wait in seconds

    Returns:
        True if event was found, False if timeout

    """
    start_time = asyncio.get_event_loop().time()
    while (asyncio.get_event_loop().time() - start_time) < max_wait:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AnalysisProgress)
                .where(AnalysisProgress.analysis_id == analysis_id)
                .where(AnalysisProgress.progress_data["type"].astext == event_type)
                .order_by(AnalysisProgress.created_at.desc())
            )
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()
            if event:
                return True
        await asyncio.sleep(0.1)  # Check every 100ms
    return False


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_event_persisted_on_extraction_failure(requires_database):
    """Test that error event is persisted when extraction fails.

    This test:
    1. Creates an analysis with an invalid URL
    2. Triggers workflow which fails at extraction
    3. Verifies error event is emitted
    4. Verifies error event is stored in analysis_progress table
    5. Verifies error event is retrievable via /progress endpoint
    """
    analysis_uuid = uuid.uuid4()
    analysis_id = str(analysis_uuid)
    test_url = f"https://invalid-url-{analysis_id}.com"  # Unique URL to avoid constraint violations

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=analysis_uuid,
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
            "Extraction failed: network error", error_code=ExtractionErrorCode.NETWORK_ERROR
        )
    )
    mock_jina.close = AsyncMock()

    with patch(
        "app.domains.analysis.workflows.tasks.extract_content.JinaReader"
    ) as mock_jina_class:
        mock_jina_class.return_value = mock_jina

        # Run workflow orchestrator (which will trigger extraction failure)
        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(analysis_uuid, test_url, skill_level="intermediate")

    # Wait for error event to be persisted (with timeout)
    event_found = await wait_for_event_persistence(analysis_uuid, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted to database"

    # Verify error event is stored in analysis_progress table
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AnalysisProgress)
            .where(AnalysisProgress.analysis_id == analysis_uuid)
            .where(AnalysisProgress.progress_data["type"].astext == "error")
            .order_by(AnalysisProgress.created_at.desc())
        )
        result = await session.execute(stmt)
        error_event = result.scalar_one_or_none()

        assert error_event is not None, "Error event should be in analysis_progress table"
        assert error_event.stage == "extraction", "Error event stage should be 'extraction'"
        assert error_event.status == "failed", "Error event status should be 'failed'"

        # Verify event data structure
        event_data = error_event.progress_data
        assert isinstance(event_data, dict), "Progress data should be a dictionary"
        assert event_data.get("type") == "error", "Event type should be 'error'"
        assert event_data.get("status") == "failed", "Event status should be 'failed'"
        assert event_data.get("stage") == "extraction", "Event stage should be 'extraction'"
        assert "error" in event_data, "Event should contain error message"
        assert event_data.get("error_code") == "NETWORK_ERROR", "Event should contain error code"

    # Verify error event is retrievable via repository (simulating /progress endpoint)
    from app.db.repositories.analysis_repository import AnalysisRepository

    async with AsyncSessionLocal() as session:
        repo = AnalysisRepository(session)
        progress_events = await repo.get_progress_events(analysis_uuid)

        # Find error event
        error_events = [
            event
            for event in progress_events
            if isinstance(event.progress_data, dict) and event.progress_data.get("type") == "error"
        ]

        assert len(error_events) > 0, "Error event should be retrievable via repository"
        error_event_record = error_events[0]

        # Verify error event structure matches what /progress endpoint would return
        assert error_event_record.stage == "extraction"
        assert error_event_record.status == "failed"
        assert isinstance(error_event_record.progress_data, dict)
        assert error_event_record.progress_data.get("type") == "error"
        assert error_event_record.progress_data.get("error_code") == "NETWORK_ERROR"
        assert "error" in error_event_record.progress_data

    # Verify analysis status was updated to failed
    async with AsyncSessionLocal() as session:
        stmt = select(Analysis).where(Analysis.id == analysis_uuid)
        result = await session.execute(stmt)
        analysis = result.scalar_one()

        assert analysis.status == "failed", "Analysis status should be 'failed'"
        assert analysis.failed_at_stage == "extraction", "Failed stage should be 'extraction'"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_error_event_contains_error_code(requires_database):
    """Test that error events include error_code when available."""
    analysis_uuid = uuid.uuid4()
    analysis_id = str(analysis_uuid)
    test_url = f"https://invalid-url-{analysis_id}.com"

    # Create Analysis record
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=analysis_uuid,
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()

    # Mock Jina to raise JinaReaderError with specific error code
    mock_jina = MagicMock()
    mock_jina.extract_article = AsyncMock(
        side_effect=JinaReaderError("Page not found", error_code=ExtractionErrorCode.HTTP_404)
    )
    mock_jina.close = AsyncMock()

    with patch(
        "app.domains.analysis.workflows.tasks.extract_content.JinaReader"
    ) as mock_jina_class:
        mock_jina_class.return_value = mock_jina

        orchestrator = WorkflowOrchestrator()
        await orchestrator.run(analysis_uuid, test_url, skill_level="intermediate")

    # Wait for error event
    event_found = await wait_for_event_persistence(analysis_uuid, "error", max_wait=10.0)
    assert event_found, "Error event should be persisted"

    # Verify error_code is in event data
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AnalysisProgress)
            .where(AnalysisProgress.analysis_id == analysis_uuid)
            .where(AnalysisProgress.progress_data["type"].astext == "error")
            .order_by(AnalysisProgress.created_at.desc())
        )
        result = await session.execute(stmt)
        error_event = result.scalar_one()

        event_data = error_event.progress_data
        assert event_data.get("error_code") == "HTTP_404", "Error event should contain error_code"
        assert "error" in event_data, "Error event should contain error message"
