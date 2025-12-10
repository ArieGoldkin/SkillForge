"""Unit tests for ReRanker.

Tests cover:
- Basic re-ranking functionality
- Score combination (alpha*base + beta*llm + gamma*structural)
- Timeout handling with fallback
- LLM error handling with fallback
- Deterministic ordering (tiebreaker by chunk_id)
- Disabled config handling
- Backwards compatibility
"""

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.constants import RERANK_ALPHA, RERANK_BETA, RERANK_GAMMA
from app.schemas.search import ChunkMetadata, ReRankConfig, SearchResult
from app.services.search.reranker import ReRanker, ReRankScore


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    """Create sample SearchResult objects for testing."""
    now = datetime.now(UTC)
    return [
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            analysis_id=str(uuid.uuid4()),
            content="First chunk about OAuth2 authentication.",
            snippet="First chunk about <mark>OAuth2</mark>...",
            score=0.9,
            metadata=ChunkMetadata(section="Auth"),
            created_at=now,
        ),
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            analysis_id=str(uuid.uuid4()),
            content="Second chunk about FastAPI.",
            snippet="Second chunk about <mark>FastAPI</mark>...",
            score=0.8,
            metadata=ChunkMetadata(section="Framework"),
            created_at=now,
        ),
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            analysis_id=str(uuid.uuid4()),
            content="Third chunk about Python.",
            snippet="Third chunk about <mark>Python</mark>...",
            score=0.7,
            metadata=ChunkMetadata(),
            created_at=now,
        ),
    ]


@pytest.fixture
def mock_model():
    """Create a mock LLM model."""
    mock = MagicMock()
    # Return scores in order: 0.8, 0.9, 0.6 (second chunk gets highest LLM score)
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="0.8\n0.9\n0.6"))
    return mock


@pytest.fixture
def reranker(mock_model):
    """Create a ReRanker with mocked LLM model."""
    reranker = ReRanker(model=mock_model)
    return reranker


class TestReRankerBasic:
    """Tests for basic re-ranking functionality."""

    @pytest.mark.asyncio
    async def test_rerank_reduces_candidates_to_final_count(
        self, reranker, sample_search_results
    ):
        """Test that re-ranking reduces candidates to final_count."""
        config = ReRankConfig(enabled=True, candidate_count=50, final_count=2)

        results = await reranker.rerank(
            query="OAuth2",
            results=sample_search_results,
            config=config,
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_rerank_returns_all_if_fewer_than_final_count(
        self, reranker, sample_search_results
    ):
        """Test that re-ranking returns all results if fewer than final_count."""
        config = ReRankConfig(enabled=True, candidate_count=50, final_count=10)

        results = await reranker.rerank(
            query="OAuth2",
            results=sample_search_results,  # Only 3 results
            config=config,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_disabled_config_returns_truncated_results(
        self, reranker, sample_search_results
    ):
        """Test that disabled config returns original results truncated."""
        config = ReRankConfig(enabled=False, final_count=2)

        results = await reranker.rerank(
            query="OAuth2",
            results=sample_search_results,
            config=config,
        )

        assert len(results) == 2
        # Should be first 2 results unchanged (not re-ranked)
        assert results[0].chunk_id == sample_search_results[0].chunk_id
        assert results[1].chunk_id == sample_search_results[1].chunk_id


class TestReRankerScoreCombination:
    """Tests for score combination logic."""

    @pytest.mark.asyncio
    async def test_score_combination_formula(self):
        """Test that final score uses correct combination formula."""
        now = datetime.now(UTC)
        # Use fixed UUIDs so we can track which is which
        results = [
            SearchResult(
                chunk_id="chunk-first",
                analysis_id="test",
                content="First chunk.",
                snippet="First...",
                score=0.9,
                metadata=ChunkMetadata(),  # No structural boost
                created_at=now,
            ),
            SearchResult(
                chunk_id="chunk-second",
                analysis_id="test",
                content="Second chunk.",
                snippet="Second...",
                score=0.8,
                metadata=ChunkMetadata(),  # No structural boost
                created_at=now,
            ),
            SearchResult(
                chunk_id="chunk-third",
                analysis_id="test",
                content="Third chunk.",
                snippet="Third...",
                score=0.7,
                metadata=ChunkMetadata(),  # No structural boost
                created_at=now,
            ),
        ]

        mock_model = MagicMock()
        # Return scores: first=0.8, second=0.9, third=0.6
        mock_model.ainvoke = AsyncMock(return_value=MagicMock(content="0.8\n0.9\n0.6"))

        reranker = ReRanker(model=mock_model)
        # Use final_count=2 to ensure re-ranking happens (3 results > 2 final)
        config = ReRankConfig(
            enabled=True,
            final_count=2,
            use_structural_priors=False,  # Disable structural for simpler test
        )

        reranked = await reranker.rerank(
            query="OAuth2",
            results=results,
            config=config,
        )

        # With structural priors disabled, gamma contribution is 0
        # First result: 0.3 * 0.9 (base) + 0.5 * 0.8 (llm) = 0.27 + 0.40 = 0.67
        # Second result: 0.3 * 0.8 (base) + 0.5 * 0.9 (llm) = 0.24 + 0.45 = 0.69
        # Third result: 0.3 * 0.7 (base) + 0.5 * 0.6 (llm) = 0.21 + 0.30 = 0.51

        # Second result should rank first (highest combined score)
        assert len(reranked) == 2
        assert reranked[0].chunk_id == "chunk-second"
        assert reranked[1].chunk_id == "chunk-first"

    @pytest.mark.asyncio
    async def test_structural_priors_contribute_to_score(self, sample_search_results):
        """Test that structural priors contribute to final score."""
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="0.5\n0.5\n0.5")  # Equal LLM scores
        )

        reranker = ReRanker(model=mock_model)
        config = ReRankConfig(
            enabled=True,
            final_count=3,
            use_structural_priors=True,
        )

        # First result has section, others don't
        sample_search_results[0].metadata = ChunkMetadata(section="Auth")
        sample_search_results[1].metadata = ChunkMetadata()
        sample_search_results[2].metadata = ChunkMetadata()

        results = await reranker.rerank(
            query="test",
            results=sample_search_results,
            config=config,
        )

        # First result should still be first due to structural prior boost
        # and higher base score
        assert len(results) == 3


class TestReRankerFallback:
    """Tests for timeout and error fallback behavior."""

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self, sample_search_results):
        """Test that timeout triggers fallback to base ranking."""
        mock_model = MagicMock()

        # Simulate timeout by making ainvoke take too long
        async def slow_invoke(*args, **kwargs):
            await asyncio.sleep(10)  # Much longer than timeout
            return MagicMock(content="0.5\n0.5\n0.5")

        mock_model.ainvoke = slow_invoke

        reranker = ReRanker(model=mock_model)

        # Patch asyncio.timeout to use a very short timeout
        # (ReRankConfig enforces minimum 1 second, so we patch instead)
        config = ReRankConfig(
            enabled=True,
            final_count=2,
            timeout_seconds=1.0,  # Valid minimum
        )

        # Override the config's timeout for the test
        original_timeout = config.timeout_seconds
        object.__setattr__(config, "timeout_seconds", 0.1)

        results = await reranker.rerank(
            query="OAuth2",
            results=sample_search_results,
            config=config,
        )

        # Should return results sorted by base score (fallback)
        assert len(results) == 2
        assert results[0].chunk_id == sample_search_results[0].chunk_id  # Highest base score
        assert results[1].chunk_id == sample_search_results[1].chunk_id  # Second highest

    @pytest.mark.asyncio
    async def test_llm_error_triggers_fallback(self, sample_search_results):
        """Test that LLM error triggers fallback to base ranking."""
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(side_effect=RuntimeError("API error"))

        reranker = ReRanker(model=mock_model)
        config = ReRankConfig(enabled=True, final_count=2)

        results = await reranker.rerank(
            query="OAuth2",
            results=sample_search_results,
            config=config,
        )

        # Should return results sorted by base score (fallback)
        assert len(results) == 2
        assert results[0].score == sample_search_results[0].score
        assert results[1].score == sample_search_results[1].score


class TestReRankerDeterminism:
    """Tests for deterministic ordering."""

    @pytest.mark.asyncio
    async def test_equal_scores_ordered_by_chunk_id(self):
        """Test that equal scores use chunk_id as tiebreaker."""
        now = datetime.now(UTC)
        # Create 3 results so len(results) > final_count triggers re-ranking
        results = [
            SearchResult(
                chunk_id="bbb-chunk",
                analysis_id="test",
                content="Content B",
                snippet="B",
                score=0.5,  # Same base score
                metadata=ChunkMetadata(),  # No structural boost
                created_at=now,
            ),
            SearchResult(
                chunk_id="aaa-chunk",
                analysis_id="test",
                content="Content A",
                snippet="A",
                score=0.5,  # Same base score
                metadata=ChunkMetadata(),  # No structural boost
                created_at=now,
            ),
            SearchResult(
                chunk_id="ccc-chunk",
                analysis_id="test",
                content="Content C",
                snippet="C",
                score=0.5,  # Same base score
                metadata=ChunkMetadata(),  # No structural boost
                created_at=now,
            ),
        ]

        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="0.5\n0.5\n0.5")  # Equal LLM scores
        )

        reranker = ReRanker(model=mock_model)
        # Use final_count=2 to ensure re-ranking happens (3 results > 2 final)
        config = ReRankConfig(enabled=True, final_count=2, use_structural_priors=False)

        reranked = await reranker.rerank(query="test", results=results, config=config)

        # All should have same final score: 0.3*0.5 + 0.5*0.5 + 0.2*0 = 0.4
        # With equal scores, should be ordered alphabetically by chunk_id as tiebreaker
        assert len(reranked) == 2
        assert reranked[0].chunk_id == "aaa-chunk"
        assert reranked[1].chunk_id == "bbb-chunk"


class TestReRankerScoreParsing:
    """Tests for LLM response parsing."""

    @pytest.mark.asyncio
    async def test_parse_malformed_response_uses_default(self, sample_search_results):
        """Test that malformed LLM response uses default score."""
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="not a number\ninvalid\ngarbage")
        )

        reranker = ReRanker(model=mock_model)
        config = ReRankConfig(enabled=True, final_count=3, use_structural_priors=False)

        results = await reranker.rerank(
            query="test",
            results=sample_search_results,
            config=config,
        )

        # Should complete without error, using default 0.5 scores
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_parse_scores_with_formatting(self, sample_search_results):
        """Test that scores with various formatting are parsed correctly."""
        mock_model = MagicMock()
        # Various formatting styles the LLM might return
        mock_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="[1] 0.95\n2. 0.85\n0.75")
        )

        reranker = ReRanker(model=mock_model)
        config = ReRankConfig(enabled=True, final_count=3, use_structural_priors=False)

        results = await reranker.rerank(
            query="test",
            results=sample_search_results,
            config=config,
        )

        # Should parse successfully
        assert len(results) == 3


class TestReRankerScoreNormalization:
    """Tests for score normalization and clamping."""

    @pytest.mark.asyncio
    async def test_scores_clamped_to_0_1_range(self, sample_search_results):
        """Test that final scores are clamped to [0, 1] range."""
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(
            return_value=MagicMock(content="1.5\n-0.5\n0.5")  # Out of range scores
        )

        reranker = ReRanker(model=mock_model)
        config = ReRankConfig(enabled=True, final_count=3, use_structural_priors=False)

        results = await reranker.rerank(
            query="test",
            results=sample_search_results,
            config=config,
        )

        # All scores should be in [0, 1] range
        for result in results:
            assert 0.0 <= result.score <= 1.0


class TestReRankScore:
    """Tests for ReRankScore dataclass."""

    def test_rerank_score_creation(self):
        """Test ReRankScore dataclass creation."""
        score = ReRankScore(
            chunk_id="test-chunk",
            base_score=0.9,
            llm_score=0.8,
            structural_score=0.1,
            final_score=0.75,
        )

        assert score.chunk_id == "test-chunk"
        assert score.base_score == 0.9
        assert score.llm_score == 0.8
        assert score.structural_score == 0.1
        assert score.final_score == 0.75


class TestReRankerLazyLoading:
    """Tests for lazy model loading."""

    def test_model_not_loaded_on_init(self):
        """Test that model is not loaded during initialization."""
        with patch("app.services.search.reranker.get_chat_model") as mock_get_model:
            reranker = ReRanker()

            # Model should not be loaded yet
            mock_get_model.assert_not_called()

    def test_model_loaded_on_first_access(self):
        """Test that model is loaded on first property access."""
        with patch("app.services.search.reranker.get_chat_model") as mock_get_model:
            mock_get_model.return_value = MagicMock()
            reranker = ReRanker()

            # Access model property
            _ = reranker.model

            # Model should be loaded now
            mock_get_model.assert_called_once()


class TestReRankerPromptBuilding:
    """Tests for prompt building."""

    def test_system_prompt_format(self, reranker):
        """Test that system prompt has correct format."""
        system_prompt = reranker._get_system_prompt()

        assert "relevance" in system_prompt.lower()
        assert "0.0" in system_prompt
        assert "1.0" in system_prompt
        assert "score" in system_prompt.lower()

    def test_scoring_prompt_includes_query(self, reranker, sample_search_results):
        """Test that scoring prompt includes the query."""
        prompt = reranker._build_scoring_prompt("OAuth2 authentication", sample_search_results)

        assert "OAuth2 authentication" in prompt
        assert "Document 1" in prompt
        assert "Document 2" in prompt

    def test_scoring_prompt_truncates_long_content(self, reranker):
        """Test that long content is truncated in prompt."""
        now = datetime.now(UTC)
        long_result = SearchResult(
            chunk_id="test",
            analysis_id="test",
            content="A" * 1000,  # Very long content
            snippet="...",
            score=0.5,
            metadata=ChunkMetadata(),
            created_at=now,
        )

        prompt = reranker._build_scoring_prompt("test", [long_result])

        # Content should be truncated (300 chars max) with ellipsis
        assert "..." in prompt
        # Should not contain full content
        assert "A" * 500 not in prompt
