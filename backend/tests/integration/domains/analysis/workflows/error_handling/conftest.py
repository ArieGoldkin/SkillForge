"""Shared fixtures and helpers for error handling integration tests."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from langgraph.types import Send
from sqlalchemy import select

from app.db.models.analysis import Analysis
from app.db.models.progress import AnalysisProgress
from app.db.session import AsyncSessionLocal
from app.domains.analysis.workflows.graph_builder import build_analysis_graph
from app.domains.analysis.workflows.state import AnalysisState


def build_test_graph(
    route_to_agents_mock: Callable[[AnalysisState], Awaitable[list[Send]]] | None = None,
    supervisor_mock: Callable[[AnalysisState], Awaitable[dict[str, object]]] | None = None,
) -> Any:
    """Build test graph with common mocks.

    Args:
        route_to_agents_mock: Mock routing function
        supervisor_mock: Mock supervisor node function

    Returns:
        Compiled graph ready for testing

    """
    return build_analysis_graph(
        route_to_agents_fn=route_to_agents_mock,
        supervisor_node_fn=supervisor_mock,
    )


@pytest.fixture
def mock_downstream_stages():
    """Mock all downstream stages to prevent workflow continuation."""
    from unittest.mock import patch

    with (
        patch(
            "app.domains.analysis.workflows.tasks.aggregate_findings.aggregate_findings",
            return_value={"aggregated_insights": {}},
        ),
        patch(
            "app.domains.analysis.workflows.tasks.generate_artifact.generate_artifact",
            return_value={"artifact_id": str(uuid.uuid4())},
        ),
        patch(
            "app.domains.analysis.workflows.nodes.quality_gate_node.quality_gate_node",
            return_value={"quality_gate_passed": True},
        ),
    ):
        yield


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
        event_type: Type of event to wait for (e.g., "error", "progress")
        max_wait: Maximum time to wait in seconds

    Returns:
        True if event was found, False if timeout

    """
    import time

    # Use time.time() instead of event_loop.time() to avoid issues during cleanup
    start_time = time.time()
    while (time.time() - start_time) < max_wait:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AnalysisProgress)
                .where(AnalysisProgress.analysis_id == analysis_id)
                .where(AnalysisProgress.progress_data["type"].astext == event_type)
                .order_by(AnalysisProgress.created_at.desc())
                .limit(1)  # Get most recent event only
            )
            result = await session.execute(stmt)
            event = result.scalar_one_or_none()
            if event:
                # Small delay to ensure session cleanup completes
                await asyncio.sleep(0.01)
                return True
        await asyncio.sleep(0.1)  # Check every 100ms
    return False


async def create_test_analysis(
    analysis_id: uuid.UUID, test_url: str, initial_status: str = "pending"
) -> None:
    """Create a test analysis record in the database.

    Args:
        analysis_id: UUID for the analysis
        test_url: URL to analyze
        initial_status: Initial status (default: "pending").
                       Use "analyzing" for errors that occur after extraction/embedding.

    """
    async with AsyncSessionLocal() as session:
        analysis = Analysis(
            id=analysis_id,
            url=test_url,
            content_type="article",
            status=initial_status,
        )
        session.add(analysis)
        await session.commit()


async def verify_error_event(
    analysis_id: uuid.UUID,
    expected_stage: str,
    expected_error_code: str | None = None,
) -> AnalysisProgress:
    """Verify error event exists and has correct structure.

    IMPORTANT: Error events are type="error" with status="failed".
    This is different from progress events with status="failed".

    If multiple error events exist (workflow may continue past non-blocking errors),
    searches for the specific stage error rather than just checking the most recent.
    """
    async with AsyncSessionLocal() as session:
        # First try to find the specific stage error event
        stmt = (
            select(AnalysisProgress)
            .where(AnalysisProgress.analysis_id == analysis_id)
            .where(AnalysisProgress.progress_data["type"].astext == "error")
            .where(AnalysisProgress.stage == expected_stage)
            .order_by(AnalysisProgress.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        error_event = result.scalar_one_or_none()

        # If not found by stage, try most recent (for backward compatibility)
        if error_event is None:
            stmt = (
                select(AnalysisProgress)
                .where(AnalysisProgress.analysis_id == analysis_id)
                .where(AnalysisProgress.progress_data["type"].astext == "error")
                .order_by(AnalysisProgress.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            error_event = result.scalar_one_or_none()

        if error_event is None:
            # Get all events for debugging
            all_events_stmt = (
                select(AnalysisProgress)
                .where(AnalysisProgress.analysis_id == analysis_id)
                .order_by(AnalysisProgress.created_at.desc())
                .limit(20)
            )
            result = await session.execute(all_events_stmt)
            all_events = result.scalars().all()

            event_summary = [
                f"  - {e.created_at}: {e.stage} / {e.status} / {e.progress_data.get('type')}"
                for e in all_events
            ]
            raise AssertionError(
                f"Error event not found for stage '{expected_stage}'.\n"
                f"Expected: type='error', stage='{expected_stage}'\n"
                f"Found {len(all_events)} events:\n" + "\n".join(event_summary)
            )
        assert error_event.stage == expected_stage, (
            f"Error event stage should be {expected_stage}, got {error_event.stage}. "
            f"This may indicate the workflow continued past the expected failure point."
        )
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


async def verify_progress_event_failed(
    analysis_id: uuid.UUID,
    expected_stage: str,
) -> AnalysisProgress:
    """Verify progress event with status="failed" exists.

    Some nodes (like agents) emit progress events with status="failed"
    instead of error events. This helper verifies those.

    Args:
        analysis_id: UUID of the analysis
        expected_stage: Expected stage name

    Returns:
        The progress event that was found

    """
    async with AsyncSessionLocal() as session:
        # Find progress event with status="failed" for the expected stage
        # Progress events store status in BOTH the status column AND progress_data JSONB
        # Try status column first (faster), then fall back to JSONB query
        stmt = (
            select(AnalysisProgress)
            .where(AnalysisProgress.analysis_id == analysis_id)
            .where(AnalysisProgress.stage == expected_stage)
            .where(AnalysisProgress.status == "failed")  # status column
            .order_by(AnalysisProgress.created_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        progress_event = result.scalar_one_or_none()

        # If not found by status column, try JSONB query
        # Some events might have different status in column vs data
        if progress_event is None:
            stmt = (
                select(AnalysisProgress)
                .where(AnalysisProgress.analysis_id == analysis_id)
                .where(AnalysisProgress.stage == expected_stage)
                .where(AnalysisProgress.progress_data["type"].astext == "progress")
                .where(AnalysisProgress.progress_data["status"].astext == "failed")
                .order_by(AnalysisProgress.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            progress_event = result.scalar_one_or_none()

        # If still not found, list all events for this stage for debugging
        if progress_event is None:
            # Debug: Get all events for this stage to see what we have
            debug_stmt = (
                select(AnalysisProgress)
                .where(AnalysisProgress.analysis_id == analysis_id)
                .where(AnalysisProgress.stage == expected_stage)
                .order_by(AnalysisProgress.created_at.desc())
                .limit(5)
            )
            debug_result = await session.execute(debug_stmt)
            debug_events = debug_result.scalars().all()
            event_summary = [
                f"Status: {e.status}, Type: {e.progress_data.get('type')}, Data Status: {e.progress_data.get('status')}"
                for e in debug_events
            ]
            assert progress_event is not None, (
                f"Progress event with status='failed' should exist for stage {expected_stage}. "
                f"Found {len(debug_events)} events for this stage: {event_summary}. "
                f"Check if agent node actually emitted the event with status='failed'."
            )
        assert progress_event.stage == expected_stage, (
            f"Progress event stage should be {expected_stage}, got {progress_event.stage}"
        )
        assert progress_event.status == "failed", "Progress event status should be 'failed'"

        # Verify event data structure
        event_data = progress_event.progress_data
        assert isinstance(event_data, dict), "Progress data should be a dictionary"
        assert event_data.get("type") == "progress", "Event type should be 'progress'"
        assert event_data.get("status") == "failed", "Event status should be 'failed'"
        assert event_data.get("stage") == expected_stage, f"Event stage should be {expected_stage}"
        assert "error" in event_data, "Event should contain error message"

        return progress_event


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
        analysis = result.scalar_one_or_none()

        assert analysis is not None, f"Analysis {analysis_id} should exist"
        assert analysis.status == expected_status, f"Analysis status should be {expected_status}"

        if expected_failed_stage:
            assert analysis.failed_at_stage == expected_failed_stage, (
                f"Failed stage should be {expected_failed_stage}"
            )

        if expected_error_code:
            assert analysis.error_code == expected_error_code, (
                f"Error code should be {expected_error_code}"
            )
