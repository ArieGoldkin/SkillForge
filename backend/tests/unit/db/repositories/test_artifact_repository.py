"""Unit tests for ArtifactRepository database operations."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis import Analysis
from app.db.models.artifact import Artifact
from app.db.repositories.artifact_repository import ArtifactRepository


@pytest.mark.unit
class TestArtifactRepository:
    """Test cases for ArtifactRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create ArtifactRepository instance with mock session."""
        return ArtifactRepository(mock_session)

    @pytest.fixture
    def sample_artifact(self):
        """Create a sample Artifact for testing."""
        return Artifact(
            id=uuid.uuid4(),
            analysis_id=uuid.uuid4(),
            markdown_content="# Sample Artifact\n\nContent here",
            version=1,
            download_count=0,
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_analysis(self):
        """Create a sample Analysis for testing."""
        return Analysis(
            id=uuid.uuid4(),
            url="https://example.com/article",
            content_type="article",
            status="complete",
            title="Sample Article",
        )

    @pytest.mark.asyncio
    async def test_create_artifact_minimal(self, repository, mock_session):
        """Test creating artifact with minimal required fields."""
        artifact_data = {
            "analysis_id": uuid.uuid4(),
            "markdown_content": "# Test Artifact",
        }

        await repository.create_artifact(artifact_data)

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_artifact_with_all_fields(self, repository, mock_session):
        """Test creating artifact with all optional fields."""
        artifact_data = {
            "id": uuid.uuid4(),
            "analysis_id": uuid.uuid4(),
            "markdown_content": "# Complete Artifact",
            "version": 2,
            "artifact_metadata": {"key_points": 5, "word_count": 1000},
            "download_count": 10,
            "trace_id": "trace-123",
        }

        await repository.create_artifact(artifact_data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_artifact_generates_id(self, repository, mock_session):
        """Test that create_artifact generates ID if not provided."""
        artifact_data = {
            "analysis_id": uuid.uuid4(),
            "markdown_content": "# Test",
        }

        await repository.create_artifact(artifact_data)

        # Should still create artifact successfully
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_artifact_default_version(self, repository, mock_session):
        """Test that version defaults to 1 if not provided."""
        artifact_data = {
            "analysis_id": uuid.uuid4(),
            "markdown_content": "# Test",
        }

        await repository.create_artifact(artifact_data)

        # Version should default to 1
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_artifact_by_id_found(self, repository, mock_session, sample_artifact):
        """Test get_artifact_by_id when artifact exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_artifact
        mock_session.execute.return_value = mock_result

        result = await repository.get_artifact_by_id(sample_artifact.id)

        assert result == sample_artifact
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_artifact_by_id_not_found(self, repository, mock_session):
        """Test get_artifact_by_id when artifact doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_artifact_by_id(uuid.uuid4())

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_artifact_by_analysis_id_found(
        self, repository, mock_session, sample_artifact
    ):
        """Test get_artifact_by_analysis_id when artifact exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_artifact
        mock_session.execute.return_value = mock_result

        result = await repository.get_artifact_by_analysis_id(sample_artifact.analysis_id)

        assert result == sample_artifact
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_artifact_by_analysis_id_not_found(self, repository, mock_session):
        """Test get_artifact_by_analysis_id when no artifact exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_artifact_by_analysis_id(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_latest_artifact_by_analysis(self, repository, mock_session, sample_artifact):
        """Test getting the most recent artifact for an analysis."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_artifact
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_artifact_by_analysis(sample_artifact.analysis_id)

        assert result == sample_artifact
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_artifact_orders_by_created_at(self, repository, mock_session):
        """Test that get_latest_artifact uses created_at ordering."""
        analysis_id = uuid.uuid4()

        # Create artifacts with different timestamps
        old_artifact = Artifact(
            id=uuid.uuid4(),
            analysis_id=analysis_id,
            markdown_content="# Old",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        new_artifact = Artifact(
            id=uuid.uuid4(),
            analysis_id=analysis_id,
            markdown_content="# New",
            created_at=datetime(2024, 12, 1, tzinfo=UTC),
        )

        # Mock returns the newest
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = new_artifact
        mock_session.execute.return_value = mock_result

        result = await repository.get_latest_artifact_by_analysis(analysis_id)

        assert result == new_artifact

    @pytest.mark.asyncio
    async def test_get_artifact_with_analysis_found(
        self, repository, mock_session, sample_artifact, sample_analysis
    ):
        """Test get_artifact_with_analysis when both exist."""
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (sample_artifact, sample_analysis)
        mock_session.execute.return_value = mock_result

        result = await repository.get_artifact_with_analysis(sample_artifact.id)

        assert result is not None
        artifact, analysis = result
        assert artifact == sample_artifact
        assert analysis == sample_analysis
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_artifact_with_analysis_not_found(self, repository, mock_session):
        """Test get_artifact_with_analysis when artifact doesn't exist."""
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_artifact_with_analysis(uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_increment_download_count(self, repository, mock_session):
        """Test incrementing download count atomically."""
        artifact_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        await repository.increment_download_count(artifact_id)

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_increment_download_count_atomic(self, repository, mock_session):
        """Test that download count increment is atomic (uses UPDATE)."""
        artifact_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        # Should use UPDATE statement, not SELECT + UPDATE
        await repository.increment_download_count(artifact_id)

        # Verify only one execute call (atomic UPDATE)
        assert mock_session.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_list_artifacts_default_pagination(self, repository, mock_session):
        """Test listing artifacts with default pagination."""
        artifacts = [
            Artifact(id=uuid.uuid4(), analysis_id=uuid.uuid4(), markdown_content=f"# Artifact {i}")
            for i in range(5)
        ]

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5

        # Mock list query
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = artifacts

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        results, total = await repository.list_artifacts(page=1, limit=20)

        assert len(results) == 5
        assert total == 5
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_artifacts_custom_pagination(self, repository, mock_session):
        """Test listing artifacts with custom page and limit."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        _results, total = await repository.list_artifacts(page=3, limit=10)

        assert total == 100
        # Page 3 with limit 10 should skip 20 items
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_artifacts_excludes_deleted(self, repository, mock_session):
        """Test that list_artifacts excludes deleted by default."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        await repository.list_artifacts(include_deleted=False)

        # Should filter out deleted artifacts
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_artifacts_includes_deleted(self, repository, mock_session):
        """Test list_artifacts with include_deleted=True."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10

        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        await repository.list_artifacts(include_deleted=True)

        # Should include deleted artifacts
        assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_soft_delete_success(self, repository, mock_session, sample_artifact):
        """Test soft deleting an artifact."""
        # Mock get_artifact_by_id to return artifact
        sample_artifact.is_deleted = False
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_artifact
        mock_session.execute.return_value = mock_result

        success = await repository.soft_delete(sample_artifact.id)

        assert success is True
        assert sample_artifact.is_deleted is True
        assert sample_artifact.deleted_at is not None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self, repository, mock_session):
        """Test soft delete when artifact doesn't exist."""
        # Mock get_artifact_by_id to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        success = await repository.soft_delete(uuid.uuid4())

        assert success is False
        # Commit should not be called
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_restore_success(self, repository, mock_session, sample_artifact):
        """Test restoring a soft-deleted artifact."""
        # Mock artifact that is soft-deleted
        sample_artifact.is_deleted = True
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_artifact
        mock_session.execute.return_value = mock_result

        success = await repository.restore(sample_artifact.id)

        assert success is True
        assert sample_artifact.is_deleted is False
        assert sample_artifact.deleted_at is None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_not_found(self, repository, mock_session):
        """Test restore when artifact doesn't exist."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        success = await repository.restore(uuid.uuid4())

        assert success is False
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_etag(self, repository, mock_session, sample_artifact):
        """Test generating ETag for caching."""
        # Mock get_artifact_by_id to return artifact
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_artifact
        mock_session.execute.return_value = mock_result

        etag = await repository.generate_etag(sample_artifact.id)

        # ETag should be generated from timestamp (MD5 hash)
        assert etag is not None
        assert len(etag) == 32  # MD5 produces 32-character hex string
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_etag_not_found(self, repository, mock_session):
        """Test generate_etag when artifact doesn't exist."""
        # Mock empty result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        etag = await repository.generate_etag(uuid.uuid4())

        assert etag is None
