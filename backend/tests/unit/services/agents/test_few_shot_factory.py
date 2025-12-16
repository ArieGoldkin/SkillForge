"""Unit tests for Few-Shot Agent Factory.

Tests cover:
- Control variant (no example injection)
- Treatment variant (with examples)
- Graceful degradation on errors
- Token budget truncation
- Example formatting
- Metrics tracking
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.services.agents.few_shot_factory import (
    MAX_EXAMPLE_TOKENS,
    _estimate_token_count,
    _format_examples_for_prompt,
    _truncate_examples_to_budget,
    create_few_shot_agent,
)
from app.shared.services.embeddings.service import EmbeddingService
from app.shared.services.examples import AgentExample, ExampleSelectionResult


@pytest.fixture
def mock_session() -> AsyncSession:
    """Mock database session."""
    return MagicMock(spec=AsyncSession)


@pytest.fixture
def mock_embedding_service() -> EmbeddingService:
    """Mock embedding service."""
    mock = MagicMock(spec=EmbeddingService)
    mock.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
    return mock


@pytest.fixture
def sample_examples() -> list[AgentExample]:
    """Sample agent examples for testing."""
    return [
        AgentExample(
            id=uuid4(),
            agent_type="tech_comparator",
            input_summary="Comparing React vs Vue for state management",
            input_content_preview="React hooks provide useState and useReducer...",
            output_example={
                "primary_tech": "React 18.2.0",
                "alternatives": ["Vue 3.3.0", "Svelte 3.59.0"],
                "comparison": {
                    "React 18.2.0": {
                        "pros": ["Hooks API", "Large ecosystem"],
                        "cons": ["Boilerplate for state management"],
                        "use_cases": ["Large-scale applications"],
                    }
                },
                "recommendation": "Use React for large teams",
            },
            context_note="Good example of versioned tech comparison",
            quality_score=0.95,
            content_type="article",
            difficulty_level="intermediate",
            similarity_distance=0.15,
        ),
        AgentExample(
            id=uuid4(),
            agent_type="tech_comparator",
            input_summary="FastAPI vs Flask performance comparison",
            input_content_preview="FastAPI leverages async/await for better performance...",
            output_example={
                "primary_tech": "FastAPI 0.104.1",
                "alternatives": ["Flask 3.0.0", "Django 5.0.0"],
                "comparison": {
                    "FastAPI 0.104.1": {
                        "pros": ["Async support", "Auto documentation"],
                        "cons": ["Newer ecosystem"],
                        "use_cases": ["API-first applications"],
                    }
                },
                "recommendation": "Use FastAPI for modern async APIs",
            },
            context_note="Shows numeric performance metrics",
            quality_score=0.92,
            content_type="article",
            difficulty_level="intermediate",
            similarity_distance=0.22,
        ),
    ]


@pytest.fixture
def sample_selection_result(sample_examples: list[AgentExample]) -> ExampleSelectionResult:
    """Sample selection result."""
    return ExampleSelectionResult(
        examples=sample_examples,
        total_candidates=10,
        selection_strategy="semantic_similarity",
        avg_quality_score=0.935,
        avg_similarity_distance=0.185,
    )


def mock_base_agent_factory(**kwargs: Any) -> dict[str, Any]:
    """Mock base agent factory for testing."""
    return {
        "type": "mock_agent",
        "system_prompt": kwargs.get("system_prompt", ""),
        "response_schema": kwargs.get("response_schema"),
    }


class TestFormatExamplesForPrompt:
    """Tests for _format_examples_for_prompt()."""

    def test_formats_examples_correctly(
        self, sample_selection_result: ExampleSelectionResult
    ) -> None:
        """Test that examples are formatted correctly."""
        result = _format_examples_for_prompt(sample_selection_result)

        assert "=== FEW-SHOT EXAMPLES ===" in result
        assert "EXAMPLE 1:" in result
        assert "EXAMPLE 2:" in result
        assert "Comparing React vs Vue" in result
        assert "FastAPI vs Flask" in result
        assert "Quality Score: 0.95" in result
        assert "Quality Score: 0.92" in result
        assert "=== END OF EXAMPLES ===" in result

    def test_includes_relevance_scores(
        self, sample_selection_result: ExampleSelectionResult
    ) -> None:
        """Test that relevance scores are included."""
        result = _format_examples_for_prompt(sample_selection_result)

        # Relevance = 1 - distance
        assert "Relevance: 0.85" in result  # 1 - 0.15
        assert "Relevance: 0.78" in result  # 1 - 0.22

    def test_handles_empty_examples(self) -> None:
        """Test that empty examples return empty string."""
        empty_result = ExampleSelectionResult(
            examples=[],
            total_candidates=0,
            selection_strategy="semantic_similarity",
            avg_quality_score=None,
            avg_similarity_distance=None,
        )

        result = _format_examples_for_prompt(empty_result)
        assert result == ""

    def test_truncates_long_content_preview(self, sample_examples: list[AgentExample]) -> None:
        """Test that long content previews are truncated."""
        long_example = AgentExample(
            id=uuid4(),
            agent_type="tech_comparator",
            input_summary="Test",
            input_content_preview="A" * 500,  # Long preview
            output_example={"test": "data"},
            quality_score=0.9,
        )

        result_with_long = ExampleSelectionResult(
            examples=[long_example],
            total_candidates=1,
            selection_strategy="semantic_similarity",
        )

        formatted = _format_examples_for_prompt(result_with_long)
        assert "..." in formatted  # Ellipsis for truncation
        assert formatted.count("A") < 500  # Should be truncated


class TestEstimateTokenCount:
    """Tests for _estimate_token_count()."""

    def test_estimates_tokens_correctly(self) -> None:
        """Test token estimation (4 chars ≈ 1 token)."""
        text = "This is a test"  # 14 chars
        tokens = _estimate_token_count(text)
        assert tokens == 3  # 14 // 4 = 3

    def test_handles_empty_string(self) -> None:
        """Test empty string returns 0 tokens."""
        assert _estimate_token_count("") == 0

    def test_handles_long_text(self) -> None:
        """Test estimation for longer text."""
        text = "A" * 1000  # 1000 chars
        tokens = _estimate_token_count(text)
        assert tokens == 250  # 1000 // 4


class TestTruncateExamplesToBudget:
    """Tests for _truncate_examples_to_budget()."""

    def test_keeps_all_examples_within_budget(
        self, sample_selection_result: ExampleSelectionResult
    ) -> None:
        """Test that examples within budget are kept."""
        # Set very high budget
        result = _truncate_examples_to_budget(sample_selection_result, max_tokens=100000)
        assert len(result.examples) == 2  # All examples kept

    def test_truncates_examples_exceeding_budget(
        self, sample_selection_result: ExampleSelectionResult
    ) -> None:
        """Test that examples exceeding budget are truncated."""
        # Set very low budget (should keep only 1 example)
        result = _truncate_examples_to_budget(sample_selection_result, max_tokens=100)
        assert len(result.examples) <= 1  # Should truncate

    def test_handles_empty_examples(self) -> None:
        """Test empty examples list."""
        empty_result = ExampleSelectionResult(
            examples=[],
            total_candidates=0,
            selection_strategy="semantic_similarity",
        )

        truncated = _truncate_examples_to_budget(empty_result)
        assert len(truncated.examples) == 0

    def test_preserves_metadata(self, sample_selection_result: ExampleSelectionResult) -> None:
        """Test that metadata is preserved after truncation."""
        truncated = _truncate_examples_to_budget(sample_selection_result)

        assert truncated.total_candidates == sample_selection_result.total_candidates
        assert truncated.selection_strategy == sample_selection_result.selection_strategy
        assert truncated.avg_quality_score == sample_selection_result.avg_quality_score


class TestCreateFewShotAgentControlVariant:
    """Tests for create_few_shot_agent() control variant."""

    @pytest.mark.asyncio
    async def test_control_variant_returns_base_agent(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that control variant returns base agent without modification."""
        agent = await create_few_shot_agent(
            agent_type="tech_comparator",
            content="Test content",
            base_agent_factory=mock_base_agent_factory,
            session=mock_session,
            embedding_service=mock_embedding_service,
            variant="control",
            system_prompt="Original prompt",
        )

        assert agent["type"] == "mock_agent"
        assert agent["system_prompt"] == "Original prompt"  # No modification

    @pytest.mark.asyncio
    async def test_control_variant_passes_kwargs(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that control variant passes all kwargs to factory."""
        agent = await create_few_shot_agent(
            agent_type="tech_comparator",
            content="Test content",
            base_agent_factory=mock_base_agent_factory,
            session=mock_session,
            embedding_service=mock_embedding_service,
            variant="control",
            system_prompt="Test prompt",
            response_schema={"test": "schema"},
        )

        assert agent["system_prompt"] == "Test prompt"
        assert agent["response_schema"] == {"test": "schema"}

    @pytest.mark.asyncio
    async def test_control_variant_raises_factory_errors(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that control variant raises factory errors."""

        def failing_factory(**kwargs: Any) -> None:
            raise ValueError("Factory error")

        with pytest.raises(ValueError, match="Factory error"):
            await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory=failing_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
                variant="control",
            )


class TestCreateFewShotAgentTreatmentVariant:
    """Tests for create_few_shot_agent() treatment variant."""

    @pytest.mark.asyncio
    async def test_treatment_variant_injects_examples(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
        sample_selection_result: ExampleSelectionResult,
    ) -> None:
        """Test that treatment variant injects examples into prompt."""
        with patch(
            "app.shared.services.agents.few_shot_factory.SemanticExampleSelector"
        ) as mock_selector_class:
            # Mock selector to return sample results
            mock_selector = MagicMock()
            mock_selector.select_examples = AsyncMock(return_value=sample_selection_result)
            mock_selector_class.return_value = mock_selector

            agent = await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
                variant="treatment",
                system_prompt="Original prompt",
                max_examples=5,
            )

            # Check that examples were injected
            assert agent["type"] == "mock_agent"
            assert "=== FEW-SHOT EXAMPLES ===" in agent["system_prompt"]
            assert "EXAMPLE 1:" in agent["system_prompt"]
            assert "Original prompt" in agent["system_prompt"]

            # Verify selector was called correctly
            mock_selector.select_examples.assert_awaited_once_with(
                content="Test content",
                agent_type="tech_comparator",
                max_examples=5,
                min_quality_score=0.8,
            )

    @pytest.mark.asyncio
    async def test_treatment_variant_falls_back_on_no_examples(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that treatment falls back to control when no examples found."""
        empty_result = ExampleSelectionResult(
            examples=[],
            total_candidates=0,
            selection_strategy="semantic_similarity",
        )

        with patch(
            "app.shared.services.agents.few_shot_factory.SemanticExampleSelector"
        ) as mock_selector_class:
            mock_selector = MagicMock()
            mock_selector.select_examples = AsyncMock(return_value=empty_result)
            mock_selector_class.return_value = mock_selector

            agent = await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
                variant="treatment",
                system_prompt="Original prompt",
            )

            # Should fall back to control (no examples injected)
            assert agent["system_prompt"] == "Original prompt"

    @pytest.mark.asyncio
    async def test_treatment_variant_falls_back_on_selector_error(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test graceful degradation when example selection fails."""
        with patch(
            "app.shared.services.agents.few_shot_factory.SemanticExampleSelector"
        ) as mock_selector_class:
            # Mock selector to raise error
            mock_selector = MagicMock()
            mock_selector.select_examples = AsyncMock(side_effect=ValueError("DB error"))
            mock_selector_class.return_value = mock_selector

            # Should not raise, should fall back to control
            agent = await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
                variant="treatment",
                system_prompt="Original prompt",
            )

            # Fallback to control variant
            assert agent["system_prompt"] == "Original prompt"

    @pytest.mark.asyncio
    async def test_treatment_variant_truncates_to_budget(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
        sample_selection_result: ExampleSelectionResult,
    ) -> None:
        """Test that examples are truncated to token budget."""
        with patch(
            "app.shared.services.agents.few_shot_factory.SemanticExampleSelector"
        ) as mock_selector_class:
            mock_selector = MagicMock()
            mock_selector.select_examples = AsyncMock(return_value=sample_selection_result)
            mock_selector_class.return_value = mock_selector

            # Create agent (should truncate examples)
            agent = await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
                variant="treatment",
                system_prompt="Original prompt",
            )

            # Verify examples section exists but respects budget
            prompt = agent["system_prompt"]
            assert "=== FEW-SHOT EXAMPLES ===" in prompt
            # Should have some examples, but total prompt should be reasonable
            estimated_tokens = _estimate_token_count(prompt)
            assert estimated_tokens < MAX_EXAMPLE_TOKENS + 5000  # Examples + original prompt


class TestCreateFewShotAgentValidation:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_raises_on_empty_agent_type(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that empty agent_type raises ValueError."""
        with pytest.raises(ValueError, match="agent_type cannot be empty"):
            await create_few_shot_agent(
                agent_type="",
                content="Test content",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
            )

    @pytest.mark.asyncio
    async def test_raises_on_empty_content(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            await create_few_shot_agent(
                agent_type="tech_comparator",
                content="",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
            )

    @pytest.mark.asyncio
    async def test_raises_on_non_callable_factory(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that non-callable factory raises TypeError."""
        with pytest.raises(TypeError, match="base_agent_factory must be callable"):
            await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory="not_a_function",  # type: ignore[arg-type]
                session=mock_session,
                embedding_service=mock_embedding_service,
            )

    @pytest.mark.asyncio
    async def test_handles_missing_system_prompt_in_treatment(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
        sample_selection_result: ExampleSelectionResult,
    ) -> None:
        """Test that missing system_prompt falls back to control."""
        with patch(
            "app.shared.services.agents.few_shot_factory.SemanticExampleSelector"
        ) as mock_selector_class:
            mock_selector = MagicMock()
            mock_selector.select_examples = AsyncMock(return_value=sample_selection_result)
            mock_selector_class.return_value = mock_selector

            # No system_prompt provided
            agent = await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
                variant="treatment",
                # No system_prompt kwarg
            )

            # Should fall back to control (no examples)
            assert agent["system_prompt"] == ""


class TestCreateFewShotAgentMetrics:
    """Tests for metrics and logging."""

    @pytest.mark.asyncio
    async def test_logs_example_retrieval_metrics(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
        sample_selection_result: ExampleSelectionResult,
    ) -> None:
        """Test that example retrieval metrics are logged."""
        with patch(
            "app.shared.services.agents.few_shot_factory.SemanticExampleSelector"
        ) as mock_selector_class:
            mock_selector = MagicMock()
            mock_selector.select_examples = AsyncMock(return_value=sample_selection_result)
            mock_selector_class.return_value = mock_selector

            with patch("app.shared.services.agents.few_shot_factory.logger") as mock_logger:
                await create_few_shot_agent(
                    agent_type="tech_comparator",
                    content="Test content",
                    base_agent_factory=mock_base_agent_factory,
                    session=mock_session,
                    embedding_service=mock_embedding_service,
                    variant="treatment",
                    system_prompt="Test prompt",
                )

                # Check that metrics were logged
                mock_logger.info.assert_any_call(
                    "few_shot_examples_retrieved",
                    agent_type="tech_comparator",
                    num_examples=2,
                    total_candidates=10,
                    avg_quality_score=0.935,
                    avg_similarity_distance=0.185,
                    retrieval_time_ms=pytest.approx(0, abs=1000),  # Within 1 second
                )

    @pytest.mark.asyncio
    async def test_logs_control_variant(
        self,
        mock_session: AsyncSession,
        mock_embedding_service: EmbeddingService,
    ) -> None:
        """Test that control variant is logged."""
        with patch("app.shared.services.agents.few_shot_factory.logger") as mock_logger:
            await create_few_shot_agent(
                agent_type="tech_comparator",
                content="Test content",
                base_agent_factory=mock_base_agent_factory,
                session=mock_session,
                embedding_service=mock_embedding_service,
                variant="control",
            )

            mock_logger.info.assert_called_with(
                "few_shot_factory_control_variant",
                agent_type="tech_comparator",
                variant="control",
            )
