"""Unit tests for rerun and retry analysis endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status


def create_mock_analysis(
    analysis_id: uuid.UUID,
    status_value: str = "complete",
    retry_count: int = 0,
    url: str = "https://example.com/article",
):
    """Create a mock analysis object."""
    mock_analysis = MagicMock()
    mock_analysis.id = analysis_id
    mock_analysis.status = status_value
    mock_analysis.retry_count = retry_count
    mock_analysis.url = url
    mock_analysis.failed_at_stage = None
    return mock_analysis


def create_mock_artifact(artifact_id: uuid.UUID, analysis_id: uuid.UUID):
    """Create a mock artifact object."""
    mock_artifact = MagicMock()
    mock_artifact.id = artifact_id
    mock_artifact.analysis_id = analysis_id
    return mock_artifact


def create_mock_task():
    """Create a mock asyncio.Task with proper methods."""
    mock_task = MagicMock()
    mock_task.add_done_callback = MagicMock()
    return mock_task


def create_mock_request():
    """Create a mock FastAPI Request object."""
    mock_request = MagicMock()
    mock_request.app.state.background_tasks = set()
    mock_request.app.state.checkpointer = None
    return mock_request


class TestRerunAnalysis:
    """Test cases for POST /api/v1/analyze/{id}/rerun endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_rerun_analysis_success(self, mock_create_task):
        """Test successful rerun of completed analysis."""
        from app.api.v1.analysis.endpoints import rerun_analysis

        analysis_id = uuid.uuid4()
        artifact_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="complete")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_rerun = AsyncMock(return_value=(1, artifact_id))

        mock_artifact_repo = AsyncMock()
        mock_artifact = create_mock_artifact(artifact_id, analysis_id)
        mock_artifact_repo.get_latest_artifact_by_analysis = AsyncMock(return_value=mock_artifact)

        mock_request = create_mock_request()

        response = await rerun_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
            artifact_repo=mock_artifact_repo,
        )

        assert response.analysis_id == str(analysis_id)
        assert response.status == "analyzing"
        assert response.rerun_count == 1
        assert response.previous_artifact_id == str(artifact_id)
        assert "/api/v1/analyze" in response.sse_endpoint
        assert str(analysis_id) in response.sse_endpoint

        mock_analysis_repo.get_by_id.assert_called_once_with(analysis_id)
        mock_artifact_repo.get_latest_artifact_by_analysis.assert_called_once_with(analysis_id)
        mock_analysis_repo.prepare_for_rerun.assert_called_once_with(analysis_id, artifact_id)
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_rerun_analysis_not_found(self):
        """Test rerun returns 404 when analysis not found."""
        from app.api.v1.analysis.endpoints import rerun_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis_repo.get_by_id = AsyncMock(return_value=None)

        mock_artifact_repo = AsyncMock()
        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await rerun_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
                artifact_repo=mock_artifact_repo,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"Analysis {analysis_id} not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_rerun_analysis_not_complete(self):
        """Test rerun returns 400 when status is not complete."""
        from app.api.v1.analysis.endpoints import rerun_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="pending")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)

        mock_artifact_repo = AsyncMock()
        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await rerun_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
                artifact_repo=mock_artifact_repo,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be in 'complete' status to rerun" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_rerun_analysis_failed_status(self):
        """Test rerun returns 400 when analysis is failed."""
        from app.api.v1.analysis.endpoints import rerun_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="failed")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)

        mock_artifact_repo = AsyncMock()
        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await rerun_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
                artifact_repo=mock_artifact_repo,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "must be in 'complete' status to rerun" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_rerun_analysis_no_artifact(self, mock_create_task):
        """Test rerun succeeds when no previous artifact exists."""
        from app.api.v1.analysis.endpoints import rerun_analysis

        analysis_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="complete")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_rerun = AsyncMock(return_value=(1, None))

        mock_artifact_repo = AsyncMock()
        mock_artifact_repo.get_latest_artifact_by_analysis = AsyncMock(return_value=None)

        mock_request = create_mock_request()

        response = await rerun_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
            artifact_repo=mock_artifact_repo,
        )

        assert response.analysis_id == str(analysis_id)
        assert response.status == "analyzing"
        assert response.rerun_count == 1
        assert response.previous_artifact_id is None

        mock_analysis_repo.prepare_for_rerun.assert_called_once_with(analysis_id, None)

    @pytest.mark.asyncio
    async def test_rerun_analysis_preparation_fails(self):
        """Test rerun returns 500 when preparation fails."""
        from app.api.v1.analysis.endpoints import rerun_analysis

        analysis_id = uuid.uuid4()
        artifact_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="complete")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_rerun = AsyncMock(
            side_effect=Exception("Database error")
        )

        mock_artifact_repo = AsyncMock()
        mock_artifact = create_mock_artifact(artifact_id, analysis_id)
        mock_artifact_repo.get_latest_artifact_by_analysis = AsyncMock(return_value=mock_artifact)

        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await rerun_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
                artifact_repo=mock_artifact_repo,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to prepare analysis for rerun" in str(exc_info.value.detail)


class TestRetryAnalysis:
    """Test cases for POST /api/v1/analyze/{id}/retry endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_retry_analysis_success_extraction_failed(self, mock_create_task):
        """Test successful retry of extraction_failed analysis."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="extraction_failed")
        mock_analysis.failed_at_stage = "extraction"
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_retry = AsyncMock()

        updated_analysis = create_mock_analysis(analysis_id, status_value="pending", retry_count=1)
        mock_analysis_repo.get_by_id.side_effect = [mock_analysis, updated_analysis]

        mock_request = create_mock_request()

        response = await retry_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
        )

        assert response.analysis_id == str(analysis_id)
        assert response.status == "pending"
        assert response.retry_count == 1
        assert "/api/v1/analyze" in response.sse_endpoint
        assert str(analysis_id) in response.sse_endpoint

        mock_analysis_repo.prepare_for_retry.assert_called_once_with(analysis_id, "pending")
        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_retry_analysis_success_analysis_failed(self, mock_create_task):
        """Test successful retry of analysis_failed analysis."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="analysis_failed")
        mock_analysis.failed_at_stage = "supervisor"
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_retry = AsyncMock()

        updated_analysis = create_mock_analysis(
            analysis_id, status_value="analyzing", retry_count=1
        )
        mock_analysis_repo.get_by_id.side_effect = [mock_analysis, updated_analysis]

        mock_request = create_mock_request()

        response = await retry_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
        )

        assert response.analysis_id == str(analysis_id)
        assert response.status == "analyzing"
        assert response.retry_count == 1

        mock_analysis_repo.prepare_for_retry.assert_called_once_with(analysis_id, "analyzing")

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_retry_analysis_success_artifact_failed(self, mock_create_task):
        """Test successful retry of artifact_failed analysis."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="artifact_failed")
        mock_analysis.failed_at_stage = "artifact_generation"
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_retry = AsyncMock()

        updated_analysis = create_mock_analysis(
            analysis_id, status_value="generating_artifact", retry_count=1
        )
        mock_analysis_repo.get_by_id.side_effect = [mock_analysis, updated_analysis]

        mock_request = create_mock_request()

        response = await retry_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
        )

        assert response.analysis_id == str(analysis_id)
        assert response.status == "generating_artifact"
        assert response.retry_count == 1

        mock_analysis_repo.prepare_for_retry.assert_called_once_with(
            analysis_id, "generating_artifact"
        )

    @pytest.mark.asyncio
    async def test_retry_analysis_not_found(self):
        """Test retry returns 404 when analysis not found."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis_repo.get_by_id = AsyncMock(return_value=None)

        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await retry_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"Analysis {analysis_id} not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_retry_analysis_not_retryable_pending(self):
        """Test retry returns 400 when status is pending (not retryable)."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="pending")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)

        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await retry_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "is not retryable" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_retry_analysis_not_retryable_complete(self):
        """Test retry returns 400 when status is complete (not retryable)."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="complete")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)

        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await retry_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "is not retryable" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_retry_analysis_limit_exceeded(self):
        """Test retry returns 400 when retry limit exceeded."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(
            analysis_id, status_value="extraction_failed", retry_count=3
        )
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)

        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await retry_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Retry limit exceeded" in str(exc_info.value.detail)
        assert "3/3" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_retry_analysis_preparation_fails(self):
        """Test retry returns 500 when preparation fails."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="extraction_failed")
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_retry = AsyncMock(side_effect=Exception("Database error"))

        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await retry_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to prepare analysis for retry" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_retry_analysis_analysis_disappeared(self):
        """Test retry returns 500 when analysis disappears after preparation."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="extraction_failed")
        mock_analysis_repo.get_by_id = AsyncMock(side_effect=[mock_analysis, None])
        mock_analysis_repo.prepare_for_retry = AsyncMock()

        mock_request = create_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await retry_analysis(
                analysis_id=analysis_id,
                fastapi_request=mock_request,
                analysis_repo=mock_analysis_repo,
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Analysis disappeared after retry preparation" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_retry_analysis_quality_gate_failed(self, mock_create_task):
        """Test retry of quality_gate_failed analysis restarts from generating_artifact."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="quality_gate_failed")
        mock_analysis.failed_at_stage = "quality_gate"
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_retry = AsyncMock()

        updated_analysis = create_mock_analysis(
            analysis_id, status_value="generating_artifact", retry_count=1
        )
        mock_analysis_repo.get_by_id.side_effect = [mock_analysis, updated_analysis]

        mock_request = create_mock_request()

        response = await retry_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
        )

        assert response.status == "generating_artifact"
        mock_analysis_repo.prepare_for_retry.assert_called_once_with(
            analysis_id, "generating_artifact"
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_retry_analysis_generic_failed(self, mock_create_task):
        """Test retry of generic failed analysis defaults to analyzing stage."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(analysis_id, status_value="failed")
        mock_analysis.failed_at_stage = None
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_retry = AsyncMock()

        updated_analysis = create_mock_analysis(
            analysis_id, status_value="analyzing", retry_count=1
        )
        mock_analysis_repo.get_by_id.side_effect = [mock_analysis, updated_analysis]

        mock_request = create_mock_request()

        response = await retry_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
        )

        assert response.status == "analyzing"
        mock_analysis_repo.prepare_for_retry.assert_called_once_with(analysis_id, "analyzing")

    @pytest.mark.asyncio
    @patch("app.api.v1.analysis.endpoints.asyncio.create_task")
    async def test_retry_analysis_multiple_retries(self, mock_create_task):
        """Test retry count increments correctly across multiple retries."""
        from app.api.v1.analysis.endpoints import retry_analysis

        analysis_id = uuid.uuid4()

        mock_create_task.return_value = create_mock_task()

        mock_analysis_repo = AsyncMock()
        mock_analysis = create_mock_analysis(
            analysis_id, status_value="extraction_failed", retry_count=1
        )
        mock_analysis_repo.get_by_id = AsyncMock(return_value=mock_analysis)
        mock_analysis_repo.prepare_for_retry = AsyncMock()

        updated_analysis = create_mock_analysis(analysis_id, status_value="pending", retry_count=2)
        mock_analysis_repo.get_by_id.side_effect = [mock_analysis, updated_analysis]

        mock_request = create_mock_request()

        response = await retry_analysis(
            analysis_id=analysis_id,
            fastapi_request=mock_request,
            analysis_repo=mock_analysis_repo,
        )

        assert response.retry_count == 2
