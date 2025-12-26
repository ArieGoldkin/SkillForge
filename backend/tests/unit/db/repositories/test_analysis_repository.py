"""Unit tests for AnalysisRepository database operations."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.analysis import Analysis
from app.db.repositories.analysis_repository import AnalysisRepository


@pytest.mark.unit
class TestAnalysisRepository:
    """Test cases for AnalysisRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def repository(self, mock_session):
        """Create AnalysisRepository instance with mock session."""
        return AnalysisRepository(mock_session)

    @pytest.fixture
    def sample_analysis(self):
        """Create a sample Analysis for testing."""
        return Analysis(
            id=uuid.uuid4(),
            url="https://example.com/article",
            content_type="article",
            status="pending",
            title="Sample Article",
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def complete_analysis(self):
        """Create a complete Analysis with all fields."""
        return Analysis(
            id=uuid.uuid4(),
            url="https://example.com/complete",
            content_type="article",
            status="complete",
            title="Complete Article",
            raw_content="Full article content here",
            content_embedding=[0.1] * 1536,
            extraction_metadata={"word_count": 500},
            created_at=datetime.now(UTC),
        )

    @pytest.mark.asyncio
    async def test_create_analysis_minimal(self, repository, mock_session):
        """Test creating analysis with minimal required fields."""
        analysis_id = uuid.uuid4()
        url = "https://example.com/test"
        content_type = "article"
        status = "pending"

        mock_session.refresh = AsyncMock()

        result = await repository.create_analysis(
            analysis_id=analysis_id,
            url=url,
            content_type=content_type,
            status=status,
        )

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_analysis_with_title(self, repository, mock_session):
        """Test creating analysis with optional title."""
        analysis_id = uuid.uuid4()

        mock_session.refresh = AsyncMock()

        await repository.create_analysis(
            analysis_id=analysis_id,
            url="https://example.com/test",
            content_type="article",
            status="pending",
            title="Test Article Title",
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, mock_session, complete_analysis):
        """Test get_by_id when analysis exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = complete_analysis
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(complete_analysis.id, validate=False)

        assert result == complete_analysis
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, mock_session):
        """Test get_by_id when analysis doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(uuid.uuid4(), validate=False)

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_with_validation(self, repository, mock_session, complete_analysis):
        """Test get_by_id with validation enabled."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = complete_analysis
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_id(complete_analysis.id, validate=True)

        # Should return analysis even with validation
        assert result == complete_analysis
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_validation_logs_warnings(self, repository, mock_session):
        """Test that validation logs warnings for incomplete data."""
        # Create incomplete analysis (missing required fields for "complete" status)
        incomplete = Analysis(
            id=uuid.uuid4(),
            url="https://example.com/incomplete",
            status="complete",  # Status is complete but missing fields
            content_type="article",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = incomplete
        mock_session.execute.return_value = mock_result

        # Should still return analysis but log warnings
        result = await repository.get_by_id(incomplete.id, validate=True)

        assert result == incomplete

    @pytest.mark.asyncio
    async def test_get_by_url_found(self, repository, mock_session, sample_analysis):
        """Test get_by_url when analysis exists."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_analysis
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_url(sample_analysis.url)

        assert result == sample_analysis
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_url_not_found(self, repository, mock_session):
        """Test get_by_url when URL doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_url("https://nonexistent.com")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_url_for_idempotency(self, repository, mock_session, sample_analysis):
        """Test get_by_url is used for idempotency checks."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_analysis
        mock_session.execute.return_value = mock_result

        # Check if URL already analyzed
        existing = await repository.get_by_url("https://example.com/article")

        assert existing is not None
        assert existing.url == sample_analysis.url

    @pytest.mark.asyncio
    async def test_find_similar_analyses_basic(self, repository, mock_session, complete_analysis):
        """Test finding similar analyses using vector search."""
        # Mock scalars result (single-stage, already optimized query)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [complete_analysis]
        mock_session.scalars.return_value = mock_scalars

        query_embedding = [0.1] * 1536
        results = await repository.find_similar_analyses(
            query_embedding=query_embedding,
            limit=5,
        )

        # Should have called scalars once
        mock_session.scalars.assert_called_once()
        assert len(results) == 1
        assert results[0] == complete_analysis

    @pytest.mark.asyncio
    async def test_find_similar_analyses_empty(self, repository, mock_session):
        """Test find_similar_analyses with no results."""
        # Mock empty results
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        query_embedding = [0.1] * 1536
        results = await repository.find_similar_analyses(
            query_embedding=query_embedding,
            limit=5,
        )

        # Should return empty list
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_find_similar_analyses_custom_limits(self, repository, mock_session):
        """Test find_similar_analyses with custom limit parameters."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        query_embedding = [0.1] * 1536
        await repository.find_similar_analyses(
            query_embedding=query_embedding,
            limit=10,
            fast_search_limit=50,
        )

        # Should call scalars with custom limits
        mock_session.scalars.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_error(self, repository, mock_session):
        """Test recording error without changing status."""
        analysis_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        await repository.record_error(
            analysis_id=analysis_id,
            error_code="HTTP_500",
            error_message="Server error",
            stage="extraction",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_progress_events(self, repository, mock_session):
        """Test retrieving progress events for an analysis."""
        from app.db.models.progress import AnalysisProgress

        analysis_id = uuid.uuid4()
        events = [
            AnalysisProgress(
                analysis_id=analysis_id,
                stage="extraction",
                status="complete",
                created_at=datetime.now(UTC),
            ),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = events
        mock_session.execute.return_value = mock_result

        results = await repository.get_progress_events(analysis_id)

        assert len(results) == 1
        assert results[0].stage == "extraction"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_progress_events_empty(self, repository, mock_session):
        """Test get_progress_events with no events."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        results = await repository.get_progress_events(uuid.uuid4())

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_prepare_for_retry(self, repository, mock_session):
        """Test preparing analysis for retry."""
        analysis_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        await repository.prepare_for_retry(
            analysis_id=analysis_id,
            restart_stage="extraction",
        )

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_for_rerun(self, repository, mock_session):
        """Test preparing analysis for rerun."""
        analysis_id = uuid.uuid4()
        artifact_id = uuid.uuid4()

        # Create analysis with rerun_count=1
        existing_analysis = Analysis(
            id=analysis_id,
            url="https://example.com",
            status="complete",
            content_type="article",
            rerun_count=1,  # Already ran once
        )

        # Mock get_by_id to return existing analysis
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = existing_analysis

        # Mock the update query
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 1

        mock_session.execute.side_effect = [mock_get_result, mock_update_result]

        run_number, previous_artifact = await repository.prepare_for_rerun(
            analysis_id=analysis_id,
            current_artifact_id=artifact_id,
        )

        # Should return incremented run number (1 + 1 = 2) and passed artifact
        assert run_number == 2
        assert previous_artifact == artifact_id
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_for_rerun_first_run(self, repository, mock_session):
        """Test prepare_for_rerun when first rerun (rerun_count starts at 0)."""
        analysis_id = uuid.uuid4()

        # Create analysis with rerun_count=0 (never rerun before)
        existing_analysis = Analysis(
            id=analysis_id,
            url="https://example.com",
            status="complete",
            content_type="article",
            rerun_count=0,  # First run, never rerun
        )

        # Mock get_by_id to return existing analysis
        mock_get_result = MagicMock()
        mock_get_result.scalar_one_or_none.return_value = existing_analysis

        # Mock the update query
        mock_update_result = MagicMock()
        mock_update_result.rowcount = 1

        mock_session.execute.side_effect = [mock_get_result, mock_update_result]

        run_number, previous_artifact = await repository.prepare_for_rerun(
            analysis_id=analysis_id,
            current_artifact_id=None,
        )

        # Should return run_number=1 (0 + 1) and no previous artifact
        assert run_number == 1
        assert previous_artifact is None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_analysis_data_complete_valid(self, repository, complete_analysis):
        """Test validation passes for complete valid analysis."""
        errors = repository._validate_analysis_data(complete_analysis)

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_analysis_data_missing_content(self, repository):
        """Test validation detects missing raw_content."""
        analysis = Analysis(
            id=uuid.uuid4(),
            url="https://example.com",
            status="complete",
            content_type="article",
            content_embedding=[0.1] * 1536,
            extraction_metadata={"test": "data"},
        )

        errors = repository._validate_analysis_data(analysis)

        assert any("raw_content" in error for error in errors)

    @pytest.mark.asyncio
    async def test_validate_analysis_data_missing_embedding(self, repository):
        """Test validation detects missing embedding."""
        analysis = Analysis(
            id=uuid.uuid4(),
            url="https://example.com",
            status="complete",
            content_type="article",
            raw_content="Test content",
            extraction_metadata={"test": "data"},
        )

        errors = repository._validate_analysis_data(analysis)

        assert any("embedding" in error for error in errors)

    @pytest.mark.asyncio
    async def test_validate_analysis_data_wrong_embedding_dimensions(self, repository):
        """Test validation detects incorrect embedding dimensions."""
        analysis = Analysis(
            id=uuid.uuid4(),
            url="https://example.com",
            status="complete",
            content_type="article",
            raw_content="Test content",
            content_embedding=[0.1] * 512,  # Wrong size (should be 1536)
            extraction_metadata={"test": "data"},
        )

        errors = repository._validate_analysis_data(analysis)

        assert any("dims" in error for error in errors)

    @pytest.mark.asyncio
    async def test_validate_analysis_data_missing_metadata(self, repository):
        """Test validation detects missing metadata."""
        analysis = Analysis(
            id=uuid.uuid4(),
            url="https://example.com",
            status="complete",
            content_type="article",
            raw_content="Test content",
            content_embedding=[0.1] * 1536,
        )

        errors = repository._validate_analysis_data(analysis)

        assert any("metadata" in error for error in errors)

    @pytest.mark.asyncio
    async def test_validate_analysis_data_pending_status(self, repository):
        """Test validation skips checks for non-complete status."""
        analysis = Analysis(
            id=uuid.uuid4(),
            url="https://example.com",
            status="pending",  # Not complete
            content_type="article",
        )

        errors = repository._validate_analysis_data(analysis)

        # Pending analyses don't need complete data
        assert len(errors) == 0
