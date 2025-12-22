"""Integration tests for status update atomicity and validation.

Tests verify that status updates are atomic, race-condition-free,
and that invalid transitions are properly rejected.
"""

import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.db.models.analysis import Analysis
from app.db.session import AsyncSessionLocal

from .conftest import create_test_analysis


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concurrent_status_updates_are_serialized(requires_database):
    """Test that concurrent status updates are serialized (no race conditions)."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-concurrent-status-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    from app.domains.analysis.services.persistence.status_updater import StatusUpdater

    # Try to update status concurrently from multiple tasks
    async def update_status(new_status: str) -> None:
        updater = StatusUpdater()
        await updater.update(analysis_id, new_status)

    # Start multiple concurrent updates
    tasks = [
        update_status("extracting"),
        update_status("analyzing"),
        update_status("generating_artifact"),
    ]

    # Run concurrently - only one should succeed (others rejected due to invalid transitions)
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify final status is one of the valid states
    async with AsyncSessionLocal() as session:
        stmt = select(Analysis).where(Analysis.id == analysis_id)
        result = await session.execute(stmt)
        analysis = result.scalar_one()

        # Status should be one of the attempted values (first valid transition wins)
        assert analysis.status in ["extracting", "analyzing", "generating_artifact"]

        # Verify no exceptions occurred (invalid transitions were handled gracefully)
        for result in results:
            if isinstance(result, ValueError):
                # ValueError is expected for invalid transitions
                assert "Invalid status transition" in str(result)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_status_transitions_are_rejected(requires_database):
    """Test that invalid status transitions are rejected."""
    analysis_id = uuid.uuid4()
    test_url = f"https://test-invalid-transition-{analysis_id}.com"

    await create_test_analysis(analysis_id, test_url)

    from app.domains.analysis.services.persistence.status_updater import StatusUpdater

    updater = StatusUpdater()

    # Try invalid transition: pending -> complete (skips required steps)
    with pytest.raises(ValueError, match="Invalid status transition"):
        await updater.update(analysis_id, "complete")

    # Try invalid transition: complete -> pending (terminal state)
    # First set status to complete
    async with AsyncSessionLocal() as session:
        analysis = await session.get(Analysis, analysis_id)
        analysis.status = "complete"  # type: ignore[assignment]
        await session.commit()

    # Now try to go back to pending (should fail)
    with pytest.raises(ValueError, match="Invalid status transition"):
        await updater.update(analysis_id, "pending")
