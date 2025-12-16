"""Integration tests for workflow_runner module."""

import asyncio
import uuid
from unittest.mock import patch

import pytest

from app.api.v1.workflow_runner import run_workflow_task
from app.models.analysis import Analysis
from app.domains.analysis.workflows.analysis import analysis_workflow


@pytest.mark.asyncio
async def test_run_workflow_task_generatorexit(
    requires_database, reset_engine_connections, db_session
):
    """Test that workflow status is updated to 'failed' when GeneratorExit occurs.

    This is an integration test using a real database session, which allows
    pytest.raises to properly catch the RuntimeError (converted from GeneratorExit)
    before it escapes the test function. The test verifies that:
    1. The exception is properly caught and converted to RuntimeError
    2. The analysis status is updated to 'failed' in the database
    3. The error handling logic works correctly

    Note: Python's async runtime converts GeneratorExit to RuntimeError in async functions.
    The unified exception handler in workflow_runner normalizes both cases.
    """
    analysis_uuid = uuid.uuid4()

    # Create analysis record
    analysis = Analysis(
        id=analysis_uuid,
        url="https://example.com/article",
        content_type="article",
        status="pending",
    )
    db_session.add(analysis)
    await db_session.commit()

    # Mock workflow to raise GeneratorExit (simulating stream closure)
    # Note: Python converts GeneratorExit in async functions to RuntimeError
    async def mock_workflow_ainvoke(input_state, config):
        """Mock workflow execution that raises GeneratorExit."""
        raise GeneratorExit()

    with patch.object(analysis_workflow, "ainvoke", new=mock_workflow_ainvoke):
        # Run workflow task - expect RuntimeError (converted from GeneratorExit)
        # The workflow runner should catch it and update status to failed
        with pytest.raises(RuntimeError, match="coroutine ignored GeneratorExit"):
            await run_workflow_task(analysis_uuid, "https://example.com/article")

        # Wait a bit for status update (status update happens in exception handler)
        await asyncio.sleep(0.1)

        # Verify status was updated to failed
        await db_session.refresh(analysis)
        assert analysis.status == "failed", "Status should be updated to 'failed' on GeneratorExit"
