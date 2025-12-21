"""Unit tests for tutor topics endpoint."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.repositories.analysis_repository import get_analysis_repository
from app.db.repositories.artifact_repository import get_artifact_repository
from app.main import app


class FakeAnalysis(SimpleNamespace):
    """Fake analysis object for testing."""

    id: uuid.UUID
    title: str | None
    url: str
    status: str
    content_type: str
    created_at: datetime


class FakeArtifact(SimpleNamespace):
    """Fake artifact object for testing."""

    id: uuid.UUID
    analysis_id: uuid.UUID
    markdown_content: str
    artifact_metadata: dict[str, Any] | None
    version: int
    created_at: datetime


class FakeAnalysisRepo:
    """Fake analysis repository for testing."""

    def __init__(self) -> None:
        """Initialize the fake repository."""
        self.analyses: dict[uuid.UUID, FakeAnalysis] = {}

    def add_analysis(
        self,
        analysis_id: uuid.UUID,
        title: str | None = "Test Analysis",
    ) -> FakeAnalysis:
        """Add an analysis to the fake repo."""
        analysis = FakeAnalysis(
            id=analysis_id,
            title=title,
            url="https://example.com/test",
            status="completed",
            content_type="article",
            created_at=datetime.now(UTC),
        )
        self.analyses[analysis_id] = analysis
        return analysis

    async def get_by_id(self, analysis_id: uuid.UUID) -> FakeAnalysis | None:
        """Get analysis by ID."""
        return self.analyses.get(analysis_id)

    async def create_analysis(self, **kwargs: Any) -> FakeAnalysis:
        """Create analysis (not used in topics tests)."""
        raise NotImplementedError

    async def find_similar_analyses(self, *args: Any, **kwargs: Any) -> list[FakeAnalysis]:
        """Find similar analyses (not used in topics tests)."""
        return []

    async def stream_all_analyses(self, *args: Any, **kwargs: Any) -> Any:
        """Stream analyses (not used in topics tests)."""
        raise NotImplementedError


class FakeArtifactRepo:
    """Fake artifact repository for testing."""

    def __init__(self) -> None:
        """Initialize the fake repository."""
        self.artifacts: dict[uuid.UUID, FakeArtifact] = {}

    def add_artifact(
        self,
        analysis_id: uuid.UUID,
        artifact_metadata: dict[str, Any] | None = None,
    ) -> FakeArtifact:
        """Add an artifact to the fake repo."""
        artifact = FakeArtifact(
            id=uuid.uuid4(),
            analysis_id=analysis_id,
            markdown_content="# Test Content",
            artifact_metadata=artifact_metadata,
            version=1,
            created_at=datetime.now(UTC),
        )
        self.artifacts[analysis_id] = artifact
        return artifact

    async def get_latest_artifact_by_analysis(self, analysis_id: uuid.UUID) -> FakeArtifact | None:
        """Get latest artifact by analysis ID."""
        return self.artifacts.get(analysis_id)

    async def get_artifact_by_id(self, artifact_id: uuid.UUID) -> FakeArtifact | None:
        """Get artifact by ID (not used in topics tests)."""
        return None

    async def get_artifact_by_analysis_id(self, analysis_id: uuid.UUID) -> FakeArtifact | None:
        """Get artifact by analysis ID."""
        return self.artifacts.get(analysis_id)

    async def create_artifact(self, artifact_data: Any) -> FakeArtifact:
        """Create artifact (not used in topics tests)."""
        raise NotImplementedError

    async def get_artifact_with_analysis(self, artifact_id: uuid.UUID) -> Any:
        """Get artifact with analysis (not used in topics tests)."""
        return None

    async def increment_download_count(self, artifact_id: uuid.UUID) -> None:
        """Increment download count (not used in topics tests)."""
        pass


@pytest.fixture
def fake_analysis_repo() -> FakeAnalysisRepo:
    """Create a fake analysis repository."""
    return FakeAnalysisRepo()


@pytest.fixture
def fake_artifact_repo() -> FakeArtifactRepo:
    """Create a fake artifact repository."""
    return FakeArtifactRepo()


@pytest.fixture
async def async_client(
    fake_analysis_repo: FakeAnalysisRepo,
    fake_artifact_repo: FakeArtifactRepo,
) -> AsyncClient:
    """Async HTTP client with mocked dependencies."""
    app.dependency_overrides[get_analysis_repository] = lambda: fake_analysis_repo
    app.dependency_overrides[get_artifact_repository] = lambda: fake_artifact_repo
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.pop(get_analysis_repository, None)
    app.dependency_overrides.pop(get_artifact_repository, None)


@pytest.mark.asyncio
async def test_get_topics_returns_topics_for_valid_analysis(
    async_client: AsyncClient,
    fake_analysis_repo: FakeAnalysisRepo,
    fake_artifact_repo: FakeArtifactRepo,
) -> None:
    """Test that topics are returned for a valid analysis with artifact."""
    analysis_id = uuid.uuid4()
    fake_analysis_repo.add_analysis(analysis_id, title="LangGraph Tutorial")
    fake_artifact_repo.add_artifact(
        analysis_id,
        artifact_metadata={
            "topics": [
                {"name": "State Management", "description": "Managing workflow state"},
                {"name": "Graph Building", "complexity": "advanced"},
            ]
        },
    )

    response = await async_client.get(f"/api/v1/tutor/analyses/{analysis_id}/topics")

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == str(analysis_id)
    assert data["analysis_title"] == "LangGraph Tutorial"
    assert len(data["topics"]) == 2
    assert data["topics"][0]["name"] == "State Management"
    assert data["topics"][0]["description"] == "Managing workflow state"
    assert data["topics"][1]["name"] == "Graph Building"
    assert data["topics"][1]["complexity"] == "advanced"


@pytest.mark.asyncio
async def test_get_topics_returns_404_for_nonexistent_analysis(
    async_client: AsyncClient,
) -> None:
    """Test that 404 is returned when analysis doesn't exist."""
    fake_analysis_id = uuid.uuid4()

    response = await async_client.get(f"/api/v1/tutor/analyses/{fake_analysis_id}/topics")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_topics_returns_empty_array_if_no_artifact(
    async_client: AsyncClient,
    fake_analysis_repo: FakeAnalysisRepo,
) -> None:
    """Test that empty topics are returned when no artifact exists."""
    analysis_id = uuid.uuid4()
    fake_analysis_repo.add_analysis(analysis_id, title="Analysis Without Artifact")

    response = await async_client.get(f"/api/v1/tutor/analyses/{analysis_id}/topics")

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == str(analysis_id)
    assert data["topics"] == []


@pytest.mark.asyncio
async def test_get_topics_returns_empty_array_if_no_topics_in_metadata(
    async_client: AsyncClient,
    fake_analysis_repo: FakeAnalysisRepo,
    fake_artifact_repo: FakeArtifactRepo,
) -> None:
    """Test that empty topics are returned when artifact has no topics."""
    analysis_id = uuid.uuid4()
    fake_analysis_repo.add_analysis(analysis_id, title="Analysis With Empty Metadata")
    fake_artifact_repo.add_artifact(
        analysis_id,
        artifact_metadata={"other_field": "value"},  # No topics field
    )

    response = await async_client.get(f"/api/v1/tutor/analyses/{analysis_id}/topics")

    assert response.status_code == 200
    data = response.json()
    assert data["topics"] == []


@pytest.mark.asyncio
async def test_get_topics_handles_string_topics(
    async_client: AsyncClient,
    fake_analysis_repo: FakeAnalysisRepo,
    fake_artifact_repo: FakeArtifactRepo,
) -> None:
    """Test that simple string topics are converted to TutoringTopic format."""
    analysis_id = uuid.uuid4()
    fake_analysis_repo.add_analysis(analysis_id, title="Simple Topics Analysis")
    fake_artifact_repo.add_artifact(
        analysis_id,
        artifact_metadata={
            "topics": ["Python", "FastAPI", "Testing"]  # Simple string array
        },
    )

    response = await async_client.get(f"/api/v1/tutor/analyses/{analysis_id}/topics")

    assert response.status_code == 200
    data = response.json()
    assert len(data["topics"]) == 3
    assert data["topics"][0]["name"] == "Python"
    assert data["topics"][0]["complexity"] == "intermediate"  # Default


@pytest.mark.asyncio
async def test_get_topics_handles_malformed_uuid(
    async_client: AsyncClient,
) -> None:
    """Test that malformed UUID returns 422 validation error."""
    response = await async_client.get("/api/v1/tutor/analyses/not-a-uuid/topics")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_topics_uses_untitled_for_null_title(
    async_client: AsyncClient,
    fake_analysis_repo: FakeAnalysisRepo,
    fake_artifact_repo: FakeArtifactRepo,
) -> None:
    """Test that 'Untitled Analysis' is used when title is None."""
    analysis_id = uuid.uuid4()
    fake_analysis_repo.add_analysis(analysis_id, title=None)
    fake_artifact_repo.add_artifact(analysis_id, artifact_metadata={"topics": []})

    response = await async_client.get(f"/api/v1/tutor/analyses/{analysis_id}/topics")

    assert response.status_code == 200
    data = response.json()
    assert data["analysis_title"] == "Untitled Analysis"
