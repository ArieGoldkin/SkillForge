"""Unit tests for ExampleRepository."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.example_repository import ExampleRepository
from app.models.agent_example import AgentExample


@pytest.mark.unit
class TestExampleRepository:
    """Tests for ExampleRepository class."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def repository(self, mock_session):
        """Create ExampleRepository instance with mock session."""
        return ExampleRepository(mock_session)

    @pytest.mark.asyncio
    async def test_initialization(self, mock_session):
        """ExampleRepository initializes with session."""
        repo = ExampleRepository(mock_session)
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_by_id_returns_example_when_found(self, repository, mock_session):
        """get_by_id() returns AgentExample when ID exists."""
        example_id = uuid.uuid4()
        mock_example = AgentExample(
            id=example_id,
            agent_type="tech_comparator",
            input_summary="Test",
            output_example={},
            quality_score=0.9,
        )

        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_example)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_id(example_id)

        assert result == mock_example
        assert result.id == example_id

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(self, repository, mock_session):
        """get_by_id() returns None when ID doesn't exist."""
        example_id = uuid.uuid4()

        # Mock query result returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_id(example_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_agent_type_returns_examples(self, repository, mock_session):
        """get_by_agent_type() returns list of examples for agent type."""
        # Create mock examples
        examples = [
            AgentExample(
                id=uuid.uuid4(),
                agent_type="tech_comparator",
                input_summary="Test 1",
                output_example={},
                quality_score=0.95,
            ),
            AgentExample(
                id=uuid.uuid4(),
                agent_type="tech_comparator",
                input_summary="Test 2",
                output_example={},
                quality_score=0.90,
            ),
        ]

        # Mock query result
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=examples)
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_agent_type(
            agent_type="tech_comparator",
            min_quality=0.8,
            limit=10,
        )

        assert len(result) == 2
        assert all(e.agent_type == "tech_comparator" for e in result)

    @pytest.mark.asyncio
    async def test_get_by_agent_type_filters_by_quality(self, repository, mock_session):
        """get_by_agent_type() applies min_quality filter."""
        # Mock to return empty list (quality filter applied)
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result = AsyncMock()
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repository.get_by_agent_type(
            agent_type="tech_comparator",
            min_quality=0.95,  # High threshold
            limit=10,
        )

        assert result == []
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_get_similar_examples_returns_examples_with_distances(
        self, repository, mock_session
    ):
        """get_similar_examples() returns list of (example, distance) tuples."""
        embedding = [0.1] * 1536  # Valid 1536-dim embedding

        example1 = AgentExample(
            id=uuid.uuid4(),
            agent_type="tech_comparator",
            input_summary="Test 1",
            output_example={},
            quality_score=0.9,
        )
        example2 = AgentExample(
            id=uuid.uuid4(),
            agent_type="tech_comparator",
            input_summary="Test 2",
            output_example={},
            quality_score=0.85,
        )

        # Mock query results with distance
        mock_row1 = MagicMock()
        mock_row1.AgentExample = example1
        mock_row1.distance = 0.12

        mock_row2 = MagicMock()
        mock_row2.AgentExample = example2
        mock_row2.distance = 0.18

        mock_result = AsyncMock()
        mock_result.__iter__ = MagicMock(return_value=iter([mock_row1, mock_row2]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        results = await repository.get_similar_examples(
            embedding=embedding,
            agent_type="tech_comparator",
            min_quality=0.8,
            limit=5,
        )

        assert len(results) == 2
        assert results[0] == (example1, 0.12)
        assert results[1] == (example2, 0.18)

    @pytest.mark.asyncio
    async def test_get_similar_examples_returns_empty_for_invalid_embedding(self, repository):
        """get_similar_examples() returns empty list for invalid embedding."""
        # Test with empty embedding
        results = await repository.get_similar_examples(
            embedding=[],
            agent_type="tech_comparator",
        )
        assert results == []

        # Test with wrong dimensions
        results = await repository.get_similar_examples(
            embedding=[0.1] * 100,  # Wrong dimensions (not 1536)
            agent_type="tech_comparator",
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_get_similar_examples_filters_by_content_type(self, repository, mock_session):
        """get_similar_examples() filters by content_type when provided."""
        embedding = [0.1] * 1536

        mock_result = AsyncMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        await repository.get_similar_examples(
            embedding=embedding,
            agent_type="tech_comparator",
            content_type="tutorial",
            min_quality=0.8,
            limit=5,
        )

        # Verify execute was called (query built with content_type filter)
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_create_adds_and_commits_example(self, repository, mock_session):
        """create() adds example to session and commits."""
        example = AgentExample(
            id=uuid.uuid4(),
            agent_type="tech_comparator",
            input_summary="Test",
            output_example={},
            quality_score=0.9,
        )

        result = await repository.create(example)

        # Verify session operations
        mock_session.add.assert_called_once_with(example)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(example)

        assert result == example

    @pytest.mark.asyncio
    async def test_bulk_create_adds_all_examples(self, repository, mock_session):
        """bulk_create() adds multiple examples and commits."""
        examples = [
            AgentExample(
                id=uuid.uuid4(),
                agent_type="tech_comparator",
                input_summary=f"Test {i}",
                output_example={},
                quality_score=0.9,
            )
            for i in range(10)
        ]

        result = await repository.bulk_create(examples)

        # Verify session operations
        mock_session.add_all.assert_called_once_with(examples)
        mock_session.commit.assert_called_once()

        assert result == examples

    @pytest.mark.asyncio
    async def test_count_by_agent_type_returns_counts(self, repository, mock_session):
        """count_by_agent_type() returns dictionary of agent type counts."""
        # Mock query results
        mock_result = AsyncMock()
        mock_result.__iter__ = MagicMock(
            return_value=iter(
                [
                    ("tech_comparator", 15),
                    ("implementation_planner", 12),
                    ("security_auditor", 8),
                ]
            )
        )
        mock_session.execute = AsyncMock(return_value=mock_result)

        counts = await repository.count_by_agent_type()

        assert counts == {
            "tech_comparator": 15,
            "implementation_planner": 12,
            "security_auditor": 8,
        }
        assert mock_session.execute.called

    @pytest.mark.asyncio
    async def test_count_by_agent_type_returns_empty_dict_when_no_examples(
        self, repository, mock_session
    ):
        """count_by_agent_type() returns empty dict when no examples exist."""
        mock_result = AsyncMock()
        mock_result.__iter__ = MagicMock(return_value=iter([]))
        mock_session.execute = AsyncMock(return_value=mock_result)

        counts = await repository.count_by_agent_type()

        assert counts == {}
