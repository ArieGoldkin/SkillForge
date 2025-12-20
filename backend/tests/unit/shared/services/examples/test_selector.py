"""Unit tests for SemanticExampleSelector service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.services.examples.schemas import ExampleSelectionResult
from app.shared.services.examples.selector import SemanticExampleSelector


@pytest.mark.unit
class TestSemanticExampleSelector:
    """Tests for SemanticExampleSelector class."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        service = AsyncMock()
        # Mock generate_embedding to return a 1536-dim vector
        service.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
        return service

    @pytest.fixture
    def selector(self, mock_session, mock_embedding_service):
        """Create SemanticExampleSelector instance with mocks."""
        return SemanticExampleSelector(mock_session, mock_embedding_service)

    @pytest.mark.asyncio
    async def test_initialization(self, mock_session, mock_embedding_service):
        """SemanticExampleSelector initializes with session and embedding service."""
        selector = SemanticExampleSelector(mock_session, mock_embedding_service)

        assert selector.session == mock_session
        assert selector.embedding_service == mock_embedding_service

    @pytest.mark.asyncio
    async def test_select_examples_with_valid_input(
        self, selector, mock_session, mock_embedding_service
    ):
        """select_examples() returns results with valid input."""
        # Mock database query result
        mock_example_model = MagicMock()
        mock_example_model.id = uuid.uuid4()
        mock_example_model.agent_type = "tech_comparator"
        mock_example_model.input_summary = "Comparing React vs Vue"
        mock_example_model.input_content_preview = "React uses..."
        mock_example_model.output_example = {"comparison": "..."}
        mock_example_model.context_note = "Test note"
        mock_example_model.quality_score = 0.9
        mock_example_model.content_type = "article"
        mock_example_model.difficulty_level = "intermediate"

        # Mock query execution
        mock_result = AsyncMock()
        mock_result.all = MagicMock(return_value=[(mock_example_model, 0.15)])

        mock_session.execute = AsyncMock(return_value=mock_result)

        # Mock _count_candidates as async
        with patch.object(selector, "_count_candidates", return_value=5):
            # Call select_examples
            result = await selector.select_examples(
                content="How to implement state management in React",
                agent_type="tech_comparator",
                max_examples=5,
                min_quality_score=0.7,
            )

            # Assertions
            assert isinstance(result, ExampleSelectionResult)
            assert len(result.examples) == 1
            assert result.examples[0].agent_type == "tech_comparator"
            assert result.examples[0].quality_score == 0.9
            assert result.examples[0].similarity_distance == 0.15
            assert result.selection_strategy == "semantic_similarity"
            assert result.total_candidates == 5

            # Verify embedding was generated
            mock_embedding_service.generate_embedding.assert_called_once()
            call_args = mock_embedding_service.generate_embedding.call_args
            assert len(call_args[0][0]) <= 2000  # Content truncated to 2000 chars

    @pytest.mark.asyncio
    async def test_select_examples_truncates_content(self, selector, mock_embedding_service):
        """select_examples() truncates content to 2000 chars for embedding."""
        long_content = "x" * 5000  # 5000 characters

        with (
            patch.object(selector, "_count_candidates", return_value=0),
            patch.object(selector.session, "execute") as mock_execute,
        ):
            mock_result = AsyncMock()
            mock_result.all = MagicMock(return_value=[])
            mock_execute.return_value = mock_result

            await selector.select_examples(
                content=long_content,
                agent_type="tech_comparator",
                max_examples=5,
            )

            # Verify content was truncated
            call_args = mock_embedding_service.generate_embedding.call_args
            assert len(call_args[0][0]) == 2000

    @pytest.mark.asyncio
    async def test_select_examples_rejects_empty_content(self, selector):
        """select_examples() raises ValueError for empty content."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await selector.select_examples(
                content="",
                agent_type="tech_comparator",
            )

        with pytest.raises(ValueError, match="Content cannot be empty"):
            await selector.select_examples(
                content="   ",  # Whitespace only
                agent_type="tech_comparator",
            )

    @pytest.mark.asyncio
    async def test_select_examples_rejects_empty_agent_type(self, selector):
        """select_examples() raises ValueError for empty agent_type."""
        with pytest.raises(ValueError, match="Agent type cannot be empty"):
            await selector.select_examples(
                content="Valid content",
                agent_type="",
            )

        with pytest.raises(ValueError, match="Agent type cannot be empty"):
            await selector.select_examples(
                content="Valid content",
                agent_type="   ",  # Whitespace only
            )

    @pytest.mark.asyncio
    async def test_select_examples_handles_embedding_failure(
        self, selector, mock_embedding_service, mock_session
    ):
        """select_examples() returns empty result when embedding generation fails."""
        # Mock embedding service to raise exception
        mock_embedding_service.generate_embedding.side_effect = Exception("OpenAI API error")

        result = await selector.select_examples(
            content="Test content",
            agent_type="tech_comparator",
        )

        assert isinstance(result, ExampleSelectionResult)
        assert result.examples == []
        assert result.total_candidates == 0
        assert result.avg_quality_score is None
        assert result.avg_similarity_distance is None

    @pytest.mark.asyncio
    async def test_select_examples_handles_query_failure(
        self, selector, mock_session, mock_embedding_service
    ):
        """select_examples() returns empty result when database query fails."""
        # Mock successful embedding generation
        mock_embedding_service.generate_embedding.return_value = [0.1] * 1536

        # Mock database query to raise exception
        mock_session.execute.side_effect = Exception("Database connection error")

        result = await selector.select_examples(
            content="Test content",
            agent_type="tech_comparator",
        )

        assert isinstance(result, ExampleSelectionResult)
        assert result.examples == []
        assert result.total_candidates == 0

    @pytest.mark.asyncio
    async def test_select_examples_returns_empty_when_no_results(self, selector, mock_session):
        """select_examples() returns empty result when no examples match."""
        # Mock query to return no results
        mock_result = AsyncMock()
        mock_result.all = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(selector, "_count_candidates", return_value=0):
            result = await selector.select_examples(
                content="Test content",
                agent_type="nonexistent_agent",
            )

            assert result.examples == []
            assert result.total_candidates == 0

    @pytest.mark.asyncio
    async def test_select_examples_filters_by_content_type(
        self, selector, mock_session, mock_embedding_service
    ):
        """select_examples() filters by content_type when provided."""
        mock_result = AsyncMock()
        mock_result.all = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(selector, "_count_candidates", return_value=0):
            await selector.select_examples(
                content="Test content",
                agent_type="tech_comparator",
                content_type="tutorial",
            )

            # Verify execute was called (query includes content_type filter)
            assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_select_examples_respects_max_examples_limit(
        self, selector, mock_session, mock_embedding_service
    ):
        """select_examples() respects max_examples parameter."""
        # Create 10 mock examples
        mock_examples = []
        for i in range(10):
            mock_example = MagicMock()
            mock_example.id = uuid.uuid4()
            mock_example.agent_type = "tech_comparator"
            mock_example.input_summary = f"Test {i}"
            mock_example.input_content_preview = "Content"
            mock_example.output_example = {}
            mock_example.context_note = None
            mock_example.quality_score = 0.9
            mock_example.content_type = "article"
            mock_example.difficulty_level = "intermediate"
            mock_examples.append((mock_example, 0.1 + i * 0.01))

        # Mock query to return only first 3 (respecting limit)
        mock_result = AsyncMock()
        mock_result.all = MagicMock(return_value=mock_examples[:3])
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(selector, "_count_candidates", return_value=10):
            result = await selector.select_examples(
                content="Test content",
                agent_type="tech_comparator",
                max_examples=3,
            )

            # Should only return 3 examples
            assert len(result.examples) == 3

    @pytest.mark.asyncio
    async def test_select_examples_calculates_statistics(
        self, selector, mock_session, mock_embedding_service
    ):
        """select_examples() calculates avg_quality_score and avg_similarity_distance."""
        # Create mock examples with known scores
        mock_example1 = MagicMock()
        mock_example1.id = uuid.uuid4()
        mock_example1.agent_type = "tech_comparator"
        mock_example1.input_summary = "Test 1"
        mock_example1.input_content_preview = "Content"
        mock_example1.output_example = {}
        mock_example1.context_note = None
        mock_example1.quality_score = 0.9  # Quality score 1
        mock_example1.content_type = "article"
        mock_example1.difficulty_level = "intermediate"

        mock_example2 = MagicMock()
        mock_example2.id = uuid.uuid4()
        mock_example2.agent_type = "tech_comparator"
        mock_example2.input_summary = "Test 2"
        mock_example2.input_content_preview = "Content"
        mock_example2.output_example = {}
        mock_example2.context_note = None
        mock_example2.quality_score = 0.8  # Quality score 2
        mock_example2.content_type = "article"
        mock_example2.difficulty_level = "intermediate"

        mock_result = AsyncMock()
        mock_result.all = MagicMock(
            return_value=[
                (mock_example1, 0.1),  # Distance 1
                (mock_example2, 0.2),  # Distance 2
            ]
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(selector, "_count_candidates", return_value=5):
            result = await selector.select_examples(
                content="Test content",
                agent_type="tech_comparator",
            )

            # Check statistics
            assert result.avg_quality_score == pytest.approx(0.85)  # (0.9 + 0.8) / 2
            assert result.avg_similarity_distance == pytest.approx(0.15)  # (0.1 + 0.2) / 2
            assert result.total_candidates == 5

    @pytest.mark.asyncio
    async def test_count_candidates_returns_count(self, selector, mock_session):
        """_count_candidates() returns count of matching examples."""
        # Mock count query
        mock_result = AsyncMock()
        mock_result.scalar_one = MagicMock(return_value=42)
        mock_session.execute = AsyncMock(return_value=mock_result)

        count = await selector._count_candidates(
            agent_type="tech_comparator",
            min_quality_score=0.7,
            content_type=None,
        )

        assert count == 42

    @pytest.mark.asyncio
    async def test_count_candidates_handles_exception(self, selector, mock_session):
        """_count_candidates() returns 0 when query fails."""
        mock_session.execute.side_effect = Exception("Database error")

        count = await selector._count_candidates(
            agent_type="tech_comparator",
            min_quality_score=0.7,
            content_type=None,
        )

        assert count == 0
