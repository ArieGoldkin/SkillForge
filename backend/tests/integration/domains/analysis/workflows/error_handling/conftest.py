"""Shared fixtures and helpers for error handling integration tests."""

import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.db.models.analysis import Analysis
from app.db.models.progress import AnalysisProgress
from app.db.session import AsyncSessionLocal


@pytest.fixture
def requires_database():
    """Skip test if DATABASE_URL is not set."""
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("DATABASE_URL not configured")


async def wait_for_event_persistence(
    analysis_id: uuid.UUID, event_type: str, max_wait: float = 10.0
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


async def create_test_analysis(analysis_id: uuid.UUID, test_url: str) -> None:
    """Create a test analysis record in the database."""
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=analysis_id,
            url=test_url,
            content_type="article",
            status="pending",
        )
        session.add(analysis)
        await session.commit()


async def verify_error_event(
    analysis_id: uuid.UUID,
    expected_stage: str,
    expected_error_code: str | None = None,
) -> AnalysisProgress:
    """Verify error event exists and has correct structure."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(AnalysisProgress)
            .where(AnalysisProgress.analysis_id == analysis_id)
            .where(AnalysisProgress.progress_data["type"].astext == "error")
            .order_by(AnalysisProgress.created_at.desc())
        )
        result = await session.execute(stmt)
        error_event = result.scalar_one_or_none()

        assert error_event is not None, f"Error event should exist for stage {expected_stage}"
        assert error_event.stage == expected_stage, f"Error event stage should be {expected_stage}"
        assert error_event.status == "failed", "Error event status should be 'failed'"

        # Verify event data structure
        event_data = error_event.progress_data
        assert isinstance(event_data, dict), "Progress data should be a dictionary"
        assert event_data.get("type") == "error", "Event type should be 'error'"
        assert event_data.get("status") == "failed", "Event status should be 'failed'"
        assert event_data.get("stage") == expected_stage, f"Event stage should be {expected_stage}"
        assert "error" in event_data, "Event should contain error message"

        if expected_error_code:
            assert event_data.get("error_code") == expected_error_code, (
                f"Event should contain error_code {expected_error_code}"
            )

        return error_event


async def verify_analysis_status(
    analysis_id: uuid.UUID,
    expected_status: str,
    expected_failed_stage: str | None = None,
    expected_error_code: str | None = None,
) -> None:
    """Verify analysis status was updated correctly."""
    async with AsyncSessionLocal() as session:
        stmt = select(Analysis).where(Analysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one()

        assert analysis.status == expected_status, f"Analysis status should be {expected_status}"

        if expected_failed_stage:
            assert analysis.failed_at_stage == expected_failed_stage, (
                f"Failed stage should be {expected_failed_stage}"
            )

        if expected_error_code:
            assert analysis.error_code == expected_error_code, (
                f"Error code should be {expected_error_code}"
            )
