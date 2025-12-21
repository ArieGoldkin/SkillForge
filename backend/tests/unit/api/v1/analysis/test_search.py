import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models.analysis import Analysis
from app.db.repositories.analysis_repository import get_analysis_repository
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def override_get_repo(mock_repo):
    app.dependency_overrides[get_analysis_repository] = lambda: mock_repo
    yield
    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_search_similar_analyses_success(mock_repo, override_get_repo):
    """Test successful search request."""
    # Mock EmbeddingService
    with patch("app.api.v1.analysis.search.EmbeddingService") as mock_embedding_service:
        mock_service_instance = mock_embedding_service.return_value
        mock_service_instance.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        mock_service_instance.close = AsyncMock()

        # Mock repository response
        analysis = Analysis(
            id=uuid.uuid4(),
            url="https://example.com",
            title="Test Analysis",
            content_type="article",
            status="complete",
            created_at=datetime.now(UTC),
        )
        mock_repo.find_similar_analyses.return_value = [analysis]

        response = client.get("/api/v1/search/similar?query=test_query&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["url"] == "https://example.com"

        # Verify calls
        mock_service_instance.generate_embedding.assert_called_once_with("test_query")
        mock_repo.find_similar_analyses.assert_called_once()


@pytest.mark.asyncio
async def test_search_similar_analyses_empty_query(client: TestClient):
    """Test search with empty query returns 422 validation error."""
    response = client.get("/api/v1/search/similar?query=")
    # FastAPI's min_length=1 validation returns 422, not 400
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_similar_analyses_service_error(mock_repo, override_get_repo):
    """Test error handling when embedding service fails."""
    with patch("app.api.v1.analysis.search.EmbeddingService") as mock_embedding_service:
        mock_service_instance = mock_embedding_service.return_value
        mock_service_instance.generate_embedding = AsyncMock(side_effect=Exception("API Error"))

        response = client.get("/api/v1/search/similar?query=test")

        assert response.status_code == 500
        assert "Search failed" in response.json()["detail"]
