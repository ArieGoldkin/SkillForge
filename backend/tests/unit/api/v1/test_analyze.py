"""Unit tests for analyze API endpoints."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.unit


def create_mock_task():
    """Create a mock asyncio.Task with proper methods."""
    mock_task = MagicMock()
    mock_task.add_done_callback = MagicMock()
    return mock_task


def create_mock_db_session() -> AsyncMock:
    """Create a mocked AsyncSession for unit tests.

    This avoids requiring a real database connection in unit tests.
    The mock session supports:
    - db.add() - no-op
    - db.commit() - returns successfully
    - db.refresh() - no-op
    - db.rollback() - returns successfully
    """
    mock_session = AsyncMock(spec=AsyncSession)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.rollback = AsyncMock()
    return mock_session


def create_mock_analysis_repo() -> AsyncMock:
    """Create a mocked analysis repository for unit tests."""
    mock_repo = AsyncMock()
    mock_repo.create_analysis = AsyncMock()
    return mock_repo


class TestCreateAnalysis:
    """Test cases for POST /api/v1/analyze endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.analyze.asyncio.create_task")
    @patch("app.api.v1.analyze.detect_content_type")
    async def test_create_analysis_success(
        self,
        mock_detect_type,
        mock_create_task,
    ):
        """Test successful analysis creation by calling endpoint directly."""
        from app.api.v1.analyze import create_analysis
        from app.domains.analysis.schemas.api import AnalyzeRequest

        # Setup mocks
        analysis_uuid = uuid.uuid4()
        mock_detect_type.return_value = "article"
        # Mock create_task to return a proper mock task (prevents background task from running)
        mock_create_task.return_value = create_mock_task()

        # Create mocked repository (no real DB connection needed for unit tests)
        mock_repo = create_mock_analysis_repo()

        # Create request
        request = AnalyzeRequest(url="https://example.com/article")

        # Mock UUID generation
        with patch("app.api.v1.analyze.uuid.uuid4", return_value=analysis_uuid):
            # Call endpoint directly with mocked database session
            response = await create_analysis(request, analysis_repo=mock_repo)

        # Assertions
        assert response.analysis_id == str(analysis_uuid)
        assert response.url == "https://example.com/article"
        assert response.content_type == "article"
        assert response.status == "pending"
        assert "/api/v1/analyze" in response.sse_endpoint
        assert str(analysis_uuid) in response.sse_endpoint

        # Verify workflow was started
        mock_create_task.assert_called_once()

    def test_create_analysis_invalid_url(self, client: TestClient):
        """Test that invalid URL returns 422."""
        response = client.post(
            "/api/v1/analyze",
            json={"url": "not-a-valid-url"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    @patch("app.api.v1.analyze.detect_content_type")
    def test_create_analysis_content_type_detection_fails(
        self, mock_detect_type, client: TestClient
    ):
        """Test that content type detection failure returns 422."""
        from app.shared.services.extraction.content_type import ContentTypeError

        mock_detect_type.side_effect = ContentTypeError("Invalid URL format")

        response = client.post(
            "/api/v1/analyze",
            json={"url": "https://example.com/article"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "Invalid URL format" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.api.v1.analyze.asyncio.create_task")
    @patch("app.api.v1.analyze.detect_content_type")
    @patch("app.api.v1.analyze.normalize_analysis_id_to_uuid")
    async def test_create_analysis_custom_id(
        self,
        mock_normalize_id,
        mock_detect_type,
        mock_create_task,
    ):
        """Test that custom analysis_id in request is used."""
        from app.api.v1.analyze import create_analysis
        from app.domains.analysis.schemas.api import AnalyzeRequest

        analysis_uuid = uuid.uuid4()
        mock_normalize_id.return_value = analysis_uuid
        mock_detect_type.return_value = "article"
        mock_create_task.return_value = create_mock_task()

        # Create mocked repository (no real DB connection needed for unit tests)
        mock_repo = create_mock_analysis_repo()

        request = AnalyzeRequest(
            url="https://example.com/article",
            analysis_id="custom-id-123",
        )

        response = await create_analysis(request, analysis_repo=mock_repo)

        mock_normalize_id.assert_called_once_with("custom-id-123")
        assert response.analysis_id == str(analysis_uuid)

    @patch("app.api.v1.analyze.detect_content_type")
    @patch("app.api.v1.analyze.normalize_analysis_id_to_uuid")
    def test_create_analysis_invalid_custom_id(
        self,
        mock_normalize_id,
        mock_detect_type,
        client: TestClient,
    ):
        """Test that invalid custom analysis_id returns 422."""
        mock_detect_type.return_value = "article"
        mock_normalize_id.side_effect = ValueError("Invalid UUID format")

        response = client.post(
            "/api/v1/analyze",
            json={
                "url": "https://example.com/article",
                "analysis_id": "invalid-id",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert "Invalid analysis_id format" in response.json()["detail"]

    @pytest.mark.asyncio
    @patch("app.api.v1.analyze.asyncio.create_task")
    @patch("app.api.v1.analyze.detect_content_type")
    async def test_create_analysis_content_type_detection(self, mock_detect_type, mock_create_task):
        """Test content type detection for different URL types."""
        from app.api.v1.analyze import create_analysis
        from app.domains.analysis.schemas.api import AnalyzeRequest

        mock_create_task.return_value = create_mock_task()

        # Create mocked database session (no real DB connection needed for unit tests)
        mock_repo = create_mock_analysis_repo()

        test_cases = [
            ("https://example.com/article", "article"),
            ("https://youtube.com/watch?v=123", "video"),
            ("https://github.com/user/repo", "repo"),
        ]

        for url, expected_type in test_cases:
            # Generate unique UUID for each test case
            test_uuid = uuid.uuid4()
            with patch("app.api.v1.analyze.uuid.uuid4", return_value=test_uuid):
                mock_detect_type.return_value = expected_type
                request = AnalyzeRequest(url=url)
                response = await create_analysis(request, analysis_repo=mock_repo)
                assert response.content_type == expected_type

    @pytest.mark.asyncio
    @patch("app.api.v1.analyze.detect_content_type")
    async def test_create_analysis_database_error(self, mock_detect_type):
        """Test that database errors are handled gracefully."""
        from fastapi import HTTPException

        from app.api.v1.analyze import create_analysis
        from app.domains.analysis.schemas.api import AnalyzeRequest

        mock_detect_type.return_value = "article"

        # Create mocked repository (no real DB connection needed for unit tests)
        mock_repo = create_mock_analysis_repo()

        # Make create_analysis raise an exception to test error handling
        mock_repo.create_analysis.side_effect = Exception("Database connection failed")

        request = AnalyzeRequest(url="https://example.com/article")

        with pytest.raises(HTTPException) as exc_info:
            await create_analysis(request, analysis_repo=mock_repo)

        # Should raise 500 for database errors
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to create analysis record" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.v1.analyze.asyncio.create_task")
    @patch("app.api.v1.analyze.detect_content_type")
    async def test_create_analysis_sse_endpoint_format(
        self,
        mock_detect_type,
        mock_create_task,
    ):
        """Test that SSE endpoint URL is in correct format."""
        from app.api.v1.analyze import create_analysis
        from app.domains.analysis.schemas.api import AnalyzeRequest

        analysis_uuid = uuid.uuid4()
        mock_detect_type.return_value = "article"
        mock_create_task.return_value = create_mock_task()

        # Create mocked database session (no real DB connection needed for unit tests)
        mock_repo = create_mock_analysis_repo()

        request = AnalyzeRequest(url="https://example.com/article")

        with patch("app.api.v1.analyze.uuid.uuid4", return_value=analysis_uuid):
            response = await create_analysis(request, analysis_repo=mock_repo)

        assert response.sse_endpoint.startswith("/api/v1/analyze/")
        assert response.sse_endpoint.endswith("/stream")
        assert str(analysis_uuid) in response.sse_endpoint
