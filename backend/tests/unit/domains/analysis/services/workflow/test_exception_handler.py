"""Unit tests for workflow exception handler."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.domains.analysis.services.workflow.exception_handler import (
    handle_workflow_exception,
)


@pytest.mark.asyncio
async def test_exception_handler_generator_exit_during_execution():
    """Test GeneratorExit during execution (workflow_completed=False).

    Should call StatusUpdater.update("failed"), emit error, and re-raise.
    """
    analysis_id = uuid.uuid4()
    exc = GeneratorExit()

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            with pytest.raises(GeneratorExit):
                await handle_workflow_exception(exc, analysis_id, workflow_completed=False)

            # Verify status was updated to failed
            mock_status.assert_called_once()
            assert mock_status.call_args[0][0] == analysis_id
            assert mock_status.call_args[0][1] == "failed"

            # Verify error event was emitted
            mock_emit.assert_called_once()
            assert mock_emit.call_args[0][0] == analysis_id
            assert mock_emit.call_args[0][1] == exc


@pytest.mark.asyncio
async def test_exception_handler_generator_exit_during_cleanup():
    """Test GeneratorExit during cleanup (workflow_completed=True).

    Should suppress exception, not call status update, and not raise.
    """
    analysis_id = uuid.uuid4()
    exc = GeneratorExit()

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            # Should not raise exception
            await handle_workflow_exception(exc, analysis_id, workflow_completed=True)

            # Verify status was NOT updated (cleanup is normal)
            mock_status.assert_not_called()

            # Verify error event was NOT emitted (cleanup is normal)
            mock_emit.assert_not_called()


@pytest.mark.asyncio
async def test_exception_handler_converted_generator_exit_during_execution():
    """Test RuntimeError with 'coroutine ignored GeneratorExit' during execution.

    Python's async runtime converts GeneratorExit to RuntimeError in async functions.
    Should treat same as GeneratorExit during execution.
    """
    analysis_id = uuid.uuid4()
    exc = RuntimeError("coroutine ignored GeneratorExit")

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            with pytest.raises(RuntimeError):
                await handle_workflow_exception(exc, analysis_id, workflow_completed=False)

            # Verify status was updated to failed
            mock_status.assert_called_once()
            assert mock_status.call_args[0][0] == analysis_id
            assert mock_status.call_args[0][1] == "failed"

            # Verify error event was emitted
            mock_emit.assert_called_once()
            assert mock_emit.call_args[0][0] == analysis_id
            assert mock_emit.call_args[0][1] == exc


@pytest.mark.asyncio
async def test_exception_handler_converted_generator_exit_during_cleanup():
    """Test RuntimeError with 'coroutine ignored GeneratorExit' during cleanup.

    Should suppress exception, not call status update, and not raise.
    """
    analysis_id = uuid.uuid4()
    exc = RuntimeError("coroutine ignored GeneratorExit")

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            # Should not raise exception
            await handle_workflow_exception(exc, analysis_id, workflow_completed=True)

            # Verify status was NOT updated (cleanup is normal)
            mock_status.assert_not_called()

            # Verify error event was NOT emitted (cleanup is normal)
            mock_emit.assert_not_called()


@pytest.mark.asyncio
async def test_exception_handler_other_runtime_error_during_execution():
    """Test RuntimeError without 'coroutine ignored GeneratorExit' message.

    Should treat as regular exception (not converted GeneratorExit).
    """
    analysis_id = uuid.uuid4()
    exc = RuntimeError("Some other runtime error")

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            with pytest.raises(RuntimeError):
                await handle_workflow_exception(exc, analysis_id, workflow_completed=False)

            # Verify status was updated to failed
            mock_status.assert_called_once()
            assert mock_status.call_args[0][0] == analysis_id
            assert mock_status.call_args[0][1] == "failed"

            # Verify error event was emitted
            mock_emit.assert_called_once()
            assert mock_emit.call_args[0][0] == analysis_id
            assert mock_emit.call_args[0][1] == exc


@pytest.mark.asyncio
async def test_exception_handler_value_error_during_execution():
    """Test ValueError (other exception type) during execution.

    Should call StatusUpdater.update("failed"), emit error, and re-raise.
    """
    analysis_id = uuid.uuid4()
    exc = ValueError("Invalid workflow state")

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            with pytest.raises(ValueError):
                await handle_workflow_exception(exc, analysis_id, workflow_completed=False)

            # Verify status was updated to failed
            mock_status.assert_called_once()
            assert mock_status.call_args[0][0] == analysis_id
            assert mock_status.call_args[0][1] == "failed"

            # Verify error event was emitted
            mock_emit.assert_called_once()
            assert mock_emit.call_args[0][0] == analysis_id
            assert mock_emit.call_args[0][1] == exc


@pytest.mark.asyncio
async def test_exception_handler_key_error_during_execution():
    """Test KeyError (other exception type) during execution.

    Should call StatusUpdater.update("failed"), emit error, and re-raise.
    """
    analysis_id = uuid.uuid4()
    exc = KeyError("missing_field")

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            with pytest.raises(KeyError):
                await handle_workflow_exception(exc, analysis_id, workflow_completed=False)

            # Verify status was updated to failed
            mock_status.assert_called_once()
            assert mock_status.call_args[0][0] == analysis_id
            assert mock_status.call_args[0][1] == "failed"

            # Verify error event was emitted
            mock_emit.assert_called_once()
            assert mock_emit.call_args[0][0] == analysis_id
            assert mock_emit.call_args[0][1] == exc


@pytest.mark.asyncio
async def test_exception_handler_exception_during_cleanup_is_not_suppressed():
    """Test non-GeneratorExit exceptions during cleanup are still treated as errors.

    workflow_completed=True only suppresses GeneratorExit, not other exceptions.
    """
    analysis_id = uuid.uuid4()
    exc = ValueError("Error during cleanup")

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            with pytest.raises(ValueError):
                await handle_workflow_exception(exc, analysis_id, workflow_completed=True)

            # Verify status was updated to failed (even during cleanup)
            mock_status.assert_called_once()
            assert mock_status.call_args[0][0] == analysis_id
            assert mock_status.call_args[0][1] == "failed"

            # Verify error event was emitted
            mock_emit.assert_called_once()
            assert mock_emit.call_args[0][0] == analysis_id
            assert mock_emit.call_args[0][1] == exc


@pytest.mark.asyncio
async def test_exception_handler_partial_match_runtime_error():
    """Test RuntimeError with partial match of 'GeneratorExit' string.

    Only exact match 'coroutine ignored GeneratorExit' should be treated as converted.
    """
    analysis_id = uuid.uuid4()
    exc = RuntimeError("GeneratorExit was found")

    with patch(
        "app.domains.analysis.services.persistence.status_updater.StatusUpdater.update",
        new_callable=AsyncMock,
    ) as mock_status:
        with patch(
            "app.domains.analysis.services.events.workflow_events.WorkflowEventEmitter.emit_error",
            new_callable=AsyncMock,
        ) as mock_emit:
            with pytest.raises(RuntimeError):
                await handle_workflow_exception(exc, analysis_id, workflow_completed=False)

            # Should be treated as regular RuntimeError, not converted GeneratorExit
            mock_status.assert_called_once()
            assert mock_status.call_args[0][0] == analysis_id
            assert mock_status.call_args[0][1] == "failed"
            mock_emit.assert_called_once()
            assert mock_emit.call_args[0][0] == analysis_id
            assert mock_emit.call_args[0][1] == exc

