"""Unit tests for status-aware WorkflowOrchestrator.

These tests use dependency injection to provide mock workflows to the orchestrator,
following the refactored pattern where WorkflowOrchestrator requires explicit
workflow injection (no singleton).
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.schemas.api import AnalysisStatus
from app.domains.analysis.services.events import WorkflowEventEmitter
from app.domains.analysis.services.persistence import DataPersister, StatusUpdater
from app.domains.analysis.services.workflow.orchestrator import WorkflowOrchestrator


@pytest.fixture
def mock_workflow():
    """Create a mock workflow for testing."""
    workflow = MagicMock()
    workflow.ainvoke = AsyncMock()
    return workflow


@pytest.fixture
def orchestrator(mock_workflow):
    """Create orchestrator instance with mocked workflow for tests.

    Uses dependency injection pattern - the mock workflow is injected
    directly into the orchestrator constructor.
    """
    return WorkflowOrchestrator(workflow=mock_workflow)


@pytest.fixture
def mock_analysis_id():
    """Create test analysis ID."""
    return uuid.uuid4()


@pytest.fixture
def valid_completed_result():
    """Create valid completed workflow result."""
    return {
        "content_ref": {
            "uri": "analysis://12345678-1234-1234-1234-123456789abc/content",
            "summary": "Test summary",
            "size_bytes": 1000,
            "content_type": "text/plain",
        },
        "raw_content": "Test content",
        "extraction_metadata": {
            "title": "Test Article",
            "word_count": 1000,
            "char_count": 5000,
        },
        "content_embedding": [0.1] * 1536,
        "workflow_status": "completed",
    }


@pytest.fixture
def failed_result():
    """Create failed workflow result."""
    return {
        "workflow_status": "failed",
        "final_error": "Extraction failed",
    }


# ============================================================================
# Status-Aware Validation Tests
# ============================================================================


@pytest.mark.asyncio
async def test_orchestrator_failed_workflow_skips_validation(
    orchestrator, mock_workflow, mock_analysis_id, failed_result
):
    """Test failed workflows skip validation."""
    mock_persister = AsyncMock(spec=DataPersister)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow to return failed result
    mock_workflow.ainvoke = AsyncMock(return_value=failed_result)

    await orchestrator.run(mock_analysis_id, "https://example.com")

    # Should not call validator or persister for failed workflows
    mock_persister.persist.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrator_completed_workflow_validates(
    orchestrator, mock_workflow, mock_analysis_id, valid_completed_result
):
    """Test completed workflows validated."""
    mock_persister = AsyncMock(spec=DataPersister)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow to return valid result
    mock_workflow.ainvoke = AsyncMock(return_value=valid_completed_result)

    # Mock artifact repository
    mock_artifact = MagicMock()
    mock_artifact.id = uuid.uuid4()
    mock_repo_instance = MagicMock()
    mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repo_instance,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal"
        ) as mock_session_local,
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        await orchestrator.run(mock_analysis_id, "https://example.com")

        # Should call persister with validated data
        mock_persister.persist.assert_called_once()
        call_args = mock_persister.persist.call_args
        assert call_args[0][0] == mock_analysis_id
        # Second arg should be dict (model_dump() result)


@pytest.mark.asyncio
async def test_orchestrator_validation_failure_updates_status(
    orchestrator, mock_workflow, mock_analysis_id
):
    """Test validation failure updates status."""
    invalid_result = {
        "raw_content": "",  # Invalid - empty
        "workflow_status": "completed",
    }

    mock_persister = AsyncMock(spec=DataPersister)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=invalid_result)

    await orchestrator.run(mock_analysis_id, "https://example.com")

    # Should update status to failed (generic "failed" to avoid state transition issues)
    mock_status.update.assert_called_with(mock_analysis_id, "failed")
    # Should emit error
    mock_emitter.emit_error.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_validation_failure_emits_error(
    orchestrator, mock_workflow, mock_analysis_id
):
    """Test validation failure emits error."""
    invalid_result = {
        "raw_content": "",
        "workflow_status": "completed",
    }

    mock_persister = AsyncMock(spec=DataPersister)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=invalid_result)

    await orchestrator.run(mock_analysis_id, "https://example.com")

    # Should emit error event
    mock_emitter.emit_error.assert_called_once()
    error_arg = mock_emitter.emit_error.call_args[0][1]
    assert isinstance(error_arg, ValueError)


@pytest.mark.asyncio
async def test_orchestrator_valid_workflow_persists(
    orchestrator, mock_workflow, mock_analysis_id, valid_completed_result
):
    """Test valid workflow persists."""
    mock_persister = AsyncMock(spec=DataPersister)
    mock_persister.persist = AsyncMock(return_value=True)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=valid_completed_result)

    # Mock artifact
    mock_artifact = MagicMock()
    mock_artifact.id = uuid.uuid4()
    mock_repo_instance = MagicMock()
    mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repo_instance,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal"
        ) as mock_session_local,
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        await orchestrator.run(mock_analysis_id, "https://example.com")

        # Should persist
        mock_persister.persist.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_invalid_status_handled(
    orchestrator, mock_workflow, mock_analysis_id
):
    """Test invalid status handled."""
    invalid_result = {
        "workflow_status": "invalid_status",
    }

    mock_persister = AsyncMock(spec=DataPersister)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=invalid_result)

    await orchestrator.run(mock_analysis_id, "https://example.com")

    # Should update status to failed (generic "failed" to avoid state transition issues)
    mock_status.update.assert_called_with(mock_analysis_id, "failed")
    # Should emit error
    mock_emitter.emit_error.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_missing_status_handled(
    orchestrator, mock_workflow, mock_analysis_id
):
    """Test missing status handled."""
    result_without_status = {
        "raw_content": "Test content",
    }

    mock_persister = AsyncMock(spec=DataPersister)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=result_without_status)

    await orchestrator.run(mock_analysis_id, "https://example.com")

    # Should handle missing status as invalid (generic "failed" to avoid state transition issues)
    mock_status.update.assert_called_with(mock_analysis_id, "failed")


@pytest.mark.asyncio
async def test_orchestrator_error_propagation(
    orchestrator, mock_workflow, mock_analysis_id, valid_completed_result
):
    """Test errors propagate correctly."""
    mock_persister = AsyncMock(spec=DataPersister)
    mock_persister.persist = AsyncMock(side_effect=RuntimeError("DB error"))
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=valid_completed_result)

    mock_artifact = MagicMock()
    mock_artifact.id = uuid.uuid4()
    mock_repo_instance = MagicMock()
    mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repo_instance,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal"
        ) as mock_session_local,
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        await orchestrator.run(mock_analysis_id, "https://example.com")

        # Should update status and emit error
        mock_status.update.assert_called()
        mock_emitter.emit_error.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_status_updater_called(
    orchestrator, mock_workflow, mock_analysis_id, valid_completed_result
):
    """Test status updater called correctly."""
    mock_persister = AsyncMock(spec=DataPersister)
    mock_persister.persist = AsyncMock(return_value=True)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=valid_completed_result)

    mock_artifact = MagicMock()
    mock_artifact.id = uuid.uuid4()
    mock_repo_instance = MagicMock()
    mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repo_instance,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal"
        ) as mock_session_local,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.get_current_trace_id",
            return_value="trace-123",
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        await orchestrator.run(mock_analysis_id, "https://example.com")

        # Should update status to complete
        mock_status.update.assert_called_with(mock_analysis_id, AnalysisStatus.COMPLETE.value)


@pytest.mark.asyncio
async def test_orchestrator_event_emitter_called(
    orchestrator, mock_workflow, mock_analysis_id, valid_completed_result
):
    """Test event emitter called correctly."""
    mock_persister = AsyncMock(spec=DataPersister)
    mock_persister.persist = AsyncMock(return_value=True)
    mock_status = AsyncMock(spec=StatusUpdater)
    mock_emitter = AsyncMock(spec=WorkflowEventEmitter)

    orchestrator.data_persister = mock_persister
    orchestrator.status_updater = mock_status
    orchestrator.event_emitter = mock_emitter

    # Configure injected mock workflow
    mock_workflow.ainvoke = AsyncMock(return_value=valid_completed_result)

    mock_artifact = MagicMock()
    mock_artifact.id = uuid.uuid4()
    mock_repo_instance = MagicMock()
    mock_repo_instance.get_artifact_by_analysis_id = AsyncMock(return_value=mock_artifact)

    with (
        patch(
            "app.domains.analysis.services.workflow.orchestrator.ArtifactRepository",
            return_value=mock_repo_instance,
        ),
        patch(
            "app.domains.analysis.services.workflow.orchestrator.AsyncSessionLocal"
        ) as mock_session_local,
        patch(
            "app.domains.analysis.services.workflow.orchestrator.get_current_trace_id",
            return_value="trace-123",
        ),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_local.return_value = mock_session

        await orchestrator.run(mock_analysis_id, "https://example.com")

        # Should emit completion event
        mock_emitter.emit_completion.assert_called_once()


# ============================================================================
# validate_content_exists Tests
# ============================================================================


@pytest.mark.asyncio
async def test_validate_content_exists_valid_uri(orchestrator, db_session):
    """Test valid URI returns True."""
    from app.db.repositories.analysis_repository import AnalysisRepository
    from app.domains.analysis.schemas.workflow_result import (
        ContentRef,
        ExtractionMetadata,
        WorkflowResult,
    )

    # Create test analysis with content (use unique URL)
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    analysis = await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/test-{analysis_id}",
        content_type="article",
        status="pending",  # Start as pending (constraint requires content for complete)
    )
    analysis.raw_content = "Test content"
    analysis.extraction_metadata = {"title": "Test"}  # Required for complete status
    await db_session.commit()

    # Now set to complete (constraint allows this since we have content and metadata)
    analysis.status = "complete"
    await db_session.commit()

    # Create WorkflowResult with content_ref pointing to this analysis
    content_ref = ContentRef(
        uri=f"analysis://{analysis_id}/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    workflow_result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    # Validate content exists
    exists = await workflow_result.validate_content_exists(db_session)
    assert exists is True


@pytest.mark.asyncio
async def test_validate_content_exists_invalid_uri(orchestrator, db_session):
    """Test invalid URI format returns False."""
    from app.domains.analysis.schemas.workflow_result import (
        ContentRef,
        ExtractionMetadata,
        WorkflowResult,
    )

    # Use valid UUID format but wrong structure (missing /content)
    invalid_id = uuid.uuid4()
    # This will fail Pydantic validation, so we need to test the method directly
    # by creating a WorkflowResult with a manually constructed invalid URI
    # Actually, we can't create ContentRef with invalid URI due to validation
    # So we test the method logic directly by mocking

    # Create valid one first, then test the method with invalid URI parts
    content_ref = ContentRef(
        uri=f"analysis://{invalid_id}/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    workflow_result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    # Manually set invalid URI to test validation logic
    workflow_result.content_ref.uri = "invalid://uri"

    # Should return False for invalid URI format
    exists = await workflow_result.validate_content_exists(db_session)
    assert exists is False


@pytest.mark.asyncio
async def test_validate_content_exists_missing_analysis(orchestrator, db_session):
    """Test missing analysis returns False."""
    from app.domains.analysis.schemas.workflow_result import (
        ContentRef,
        ExtractionMetadata,
        WorkflowResult,
    )

    missing_id = uuid.uuid4()
    content_ref = ContentRef(
        uri=f"analysis://{missing_id}/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    workflow_result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    exists = await workflow_result.validate_content_exists(db_session)
    assert exists is False


@pytest.mark.asyncio
async def test_validate_content_exists_empty_content(orchestrator, db_session):
    """Test empty content returns False."""
    from app.db.repositories.analysis_repository import AnalysisRepository
    from app.domains.analysis.schemas.workflow_result import (
        ContentRef,
        ExtractionMetadata,
        WorkflowResult,
    )

    # Create analysis without content (use unique URL)
    repo = AnalysisRepository(session=db_session)
    analysis_id = uuid.uuid4()
    await repo.create_analysis(
        analysis_id=analysis_id,
        url=f"https://example.com/test-empty-{analysis_id}",
        content_type="article",
        status="pending",
    )

    content_ref = ContentRef(
        uri=f"analysis://{analysis_id}/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    workflow_result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    exists = await workflow_result.validate_content_exists(db_session)
    assert exists is False


@pytest.mark.asyncio
async def test_validate_content_exists_uuid_parsing(orchestrator, db_session):
    """Test UUID parsing works."""
    from app.domains.analysis.schemas.workflow_result import (
        ContentRef,
        ExtractionMetadata,
        WorkflowResult,
    )

    # Create with valid UUID format first
    valid_id = uuid.uuid4()
    content_ref = ContentRef(
        uri=f"analysis://{valid_id}/content",
        summary="Test summary",
        size_bytes=1000,
        content_type="text/plain",
    )
    metadata = ExtractionMetadata(
        title="Test",
        word_count=1000,
        char_count=5000,
    )
    workflow_result = WorkflowResult(
        content_ref=content_ref,
        raw_content="Test content",
        extraction_metadata=metadata,
        content_embedding=[0.1] * 1536,
    )

    # Manually set invalid UUID to test parsing
    workflow_result.content_ref.uri = "analysis://not-a-valid-uuid-format/content"

    # Should return False when UUID parsing fails
    exists = await workflow_result.validate_content_exists(db_session)
    assert exists is False
