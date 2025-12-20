"""Unit tests for artifact endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.analysis.artifacts import router
from app.db.repositories.artifact_repository import get_artifact_repository


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def mock_repo():
    """Create mock artifact repository."""
    return AsyncMock()


@pytest.fixture
def client(app, mock_repo):
    """Create test client with mocked repository."""
    app.dependency_overrides[get_artifact_repository] = lambda: mock_repo
    return TestClient(app)


@pytest.fixture
def mock_artifact():
    """Create mock artifact object."""
    artifact = MagicMock()
    artifact.id = uuid4()
    artifact.analysis_id = uuid4()
    artifact.markdown_content = "# Test Artifact\n\nContent here"
    artifact.artifact_metadata = {"title": "Test", "topics": ["python"]}
    artifact.trace_id = "test-trace-id-123"
    artifact.created_at = datetime.now(UTC)
    artifact.download_count = 5
    return artifact


@pytest.fixture
def mock_analysis():
    """Create mock analysis object with extraction metadata."""
    analysis = MagicMock()
    analysis.id = uuid4()
    analysis.extraction_metadata = {"title": "Test Analysis Title", "source": "test"}
    return analysis


class TestGetArtifactByAnalysis:
    """Tests for GET /analyze/{analysis_id}/artifact endpoint."""

    def test_get_artifact_success(self, client, mock_repo, mock_artifact):
        """Test successful artifact retrieval returns proper response structure."""
        mock_repo.get_latest_artifact_by_analysis.return_value = mock_artifact

        response = client.get(f"/api/v1/analyze/{mock_artifact.analysis_id}/artifact")

        assert response.status_code == 200
        data = response.json()
        # Verify all expected fields are present
        assert data["artifact_id"] == str(mock_artifact.id)
        assert data["analysis_id"] == str(mock_artifact.analysis_id)
        assert data["markdown_content"] == mock_artifact.markdown_content
        assert data["artifact_metadata"] == mock_artifact.artifact_metadata
        assert data["trace_id"] == mock_artifact.trace_id
        assert "created_at" in data

    def test_get_artifact_not_found(self, client, mock_repo):
        """Test 404 when artifact not found for analysis."""
        mock_repo.get_latest_artifact_by_analysis.return_value = None
        analysis_id = uuid4()

        response = client.get(f"/api/v1/analyze/{analysis_id}/artifact")

        assert response.status_code == 404
        assert "No artifact found" in response.json()["detail"]
        # Verify the analysis_id is in the error message
        assert str(analysis_id) in response.json()["detail"]

    def test_get_artifact_null_content_returns_empty_string(self, client, mock_repo, mock_artifact):
        """Test that null markdown content returns empty string, not null."""
        mock_artifact.markdown_content = None
        mock_repo.get_latest_artifact_by_analysis.return_value = mock_artifact

        response = client.get(f"/api/v1/analyze/{mock_artifact.analysis_id}/artifact")

        assert response.status_code == 200
        # Null content should be converted to empty string per endpoint logic
        assert response.json()["markdown_content"] == ""

    def test_get_artifact_null_metadata(self, client, mock_repo, mock_artifact):
        """Test handling of null artifact metadata."""
        mock_artifact.artifact_metadata = None
        mock_repo.get_latest_artifact_by_analysis.return_value = mock_artifact

        response = client.get(f"/api/v1/analyze/{mock_artifact.analysis_id}/artifact")

        assert response.status_code == 200
        assert response.json()["artifact_metadata"] is None

    def test_get_artifact_calls_repository_with_correct_id(self, client, mock_repo, mock_artifact):
        """Test that repository is called with the correct analysis ID."""
        mock_repo.get_latest_artifact_by_analysis.return_value = mock_artifact
        analysis_id = mock_artifact.analysis_id

        client.get(f"/api/v1/analyze/{analysis_id}/artifact")

        mock_repo.get_latest_artifact_by_analysis.assert_awaited_once_with(analysis_id)

    def test_get_artifact_null_trace_id(self, client, mock_repo, mock_artifact):
        """Test handling of null trace_id for old artifacts."""
        mock_artifact.trace_id = None
        mock_repo.get_latest_artifact_by_analysis.return_value = mock_artifact

        response = client.get(f"/api/v1/analyze/{mock_artifact.analysis_id}/artifact")

        assert response.status_code == 200
        assert response.json()["trace_id"] is None


class TestGetArtifactById:
    """Tests for GET /artifacts/{artifact_id} endpoint."""

    def test_get_artifact_by_id_success(self, client, mock_repo, mock_artifact):
        """Test successful artifact retrieval by ID returns proper response structure."""
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}")

        assert response.status_code == 200
        data = response.json()
        # Verify all expected fields are present
        assert data["artifact_id"] == str(mock_artifact.id)
        assert data["analysis_id"] == str(mock_artifact.analysis_id)
        assert data["markdown_content"] == mock_artifact.markdown_content
        assert data["artifact_metadata"] == mock_artifact.artifact_metadata
        assert data["trace_id"] == mock_artifact.trace_id
        assert "created_at" in data

    def test_get_artifact_by_id_not_found(self, client, mock_repo):
        """Test 404 when artifact not found by ID."""
        mock_repo.get_artifact_by_id.return_value = None
        artifact_id = uuid4()

        response = client.get(f"/api/v1/artifacts/{artifact_id}")

        assert response.status_code == 404
        assert "Artifact" in response.json()["detail"]
        assert str(artifact_id) in response.json()["detail"]

    def test_get_artifact_by_id_null_content(self, client, mock_repo, mock_artifact):
        """Test that null markdown content returns empty string, not null."""
        mock_artifact.markdown_content = None
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}")

        assert response.status_code == 200
        # Null content should be converted to empty string per endpoint logic
        assert response.json()["markdown_content"] == ""

    def test_get_artifact_by_id_null_metadata(self, client, mock_repo, mock_artifact):
        """Test handling of null artifact metadata."""
        mock_artifact.artifact_metadata = None
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}")

        assert response.status_code == 200
        assert response.json()["artifact_metadata"] is None

    def test_get_artifact_by_id_calls_repository_with_correct_id(
        self, client, mock_repo, mock_artifact
    ):
        """Test that repository is called with the correct artifact ID."""
        mock_repo.get_artifact_by_id.return_value = mock_artifact
        artifact_id = mock_artifact.id

        client.get(f"/api/v1/artifacts/{artifact_id}")

        mock_repo.get_artifact_by_id.assert_awaited_once_with(artifact_id)

    def test_get_artifact_by_id_null_trace_id(self, client, mock_repo, mock_artifact):
        """Test handling of null trace_id for old artifacts."""
        mock_artifact.trace_id = None
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}")

        assert response.status_code == 200
        assert response.json()["trace_id"] is None


class TestDownloadArtifact:
    """Tests for GET /artifacts/{artifact_id}/download endpoint."""

    def test_download_artifact_success(self, client, mock_repo, mock_artifact, mock_analysis):
        """Test successful artifact download returns markdown file."""
        # Repository returns tuple (artifact, analysis)
        mock_repo.get_artifact_with_analysis.return_value = (mock_artifact, mock_analysis)
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}/download")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/markdown; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        # Verify content matches artifact markdown
        assert response.content == mock_artifact.markdown_content.encode()

    def test_download_artifact_not_found(self, client, mock_repo):
        """Test 404 when artifact doesn't exist."""
        # Repository returns None when not found
        mock_repo.get_artifact_with_analysis.return_value = None
        artifact_id = uuid4()

        response = client.get(f"/api/v1/artifacts/{artifact_id}/download")

        assert response.status_code == 404
        assert str(artifact_id) in response.json()["detail"]

    def test_download_increments_count(self, client, mock_repo, mock_artifact, mock_analysis):
        """Test that download increments the download count for analytics."""
        mock_repo.get_artifact_with_analysis.return_value = (mock_artifact, mock_analysis)
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        client.get(f"/api/v1/artifacts/{mock_artifact.id}/download")

        mock_repo.increment_download_count.assert_awaited_once_with(mock_artifact.id)

    def test_download_null_content_returns_empty_bytes(
        self, client, mock_repo, mock_artifact, mock_analysis
    ):
        """Test download with null content returns empty response."""
        mock_artifact.markdown_content = None
        mock_repo.get_artifact_with_analysis.return_value = (mock_artifact, mock_analysis)
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}/download")

        assert response.status_code == 200
        assert response.content == b""

    def test_download_filename_from_analysis_title(
        self, client, mock_repo, mock_artifact, mock_analysis
    ):
        """Test that filename is generated from analysis extraction_metadata title."""
        mock_repo.get_artifact_with_analysis.return_value = (mock_artifact, mock_analysis)
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}/download")

        # Filename should be derived from title in extraction_metadata
        content_disposition = response.headers["content-disposition"]
        assert "attachment" in content_disposition
        assert ".md" in content_disposition

    def test_download_missing_extraction_metadata(
        self, client, mock_repo, mock_artifact, mock_analysis
    ):
        """Test download when analysis has no extraction_metadata."""
        mock_analysis.extraction_metadata = None
        mock_repo.get_artifact_with_analysis.return_value = (mock_artifact, mock_analysis)
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}/download")

        # Should still succeed with fallback filename
        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]

    def test_download_extraction_metadata_missing_title(
        self, client, mock_repo, mock_artifact, mock_analysis
    ):
        """Test download when extraction_metadata exists but has no title."""
        mock_analysis.extraction_metadata = {"source": "url", "author": "test"}
        mock_repo.get_artifact_with_analysis.return_value = (mock_artifact, mock_analysis)
        mock_repo.get_artifact_by_id.return_value = mock_artifact

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}/download")

        # Should succeed with fallback filename
        assert response.status_code == 200
        assert ".md" in response.headers["content-disposition"]

    def test_download_handles_database_error(self, client, mock_repo, mock_artifact):
        """Test that database errors return 500."""
        mock_repo.get_artifact_with_analysis.side_effect = Exception("Database connection failed")

        response = client.get(f"/api/v1/artifacts/{mock_artifact.id}/download")

        assert response.status_code == 500
        assert "Failed to download artifact" in response.json()["detail"]

    def test_download_calls_repository_with_correct_id(
        self, client, mock_repo, mock_artifact, mock_analysis
    ):
        """Test that repository is called with correct artifact ID."""
        mock_repo.get_artifact_with_analysis.return_value = (mock_artifact, mock_analysis)
        mock_repo.get_artifact_by_id.return_value = mock_artifact
        artifact_id = mock_artifact.id

        client.get(f"/api/v1/artifacts/{artifact_id}/download")

        mock_repo.get_artifact_with_analysis.assert_awaited_once_with(artifact_id)
