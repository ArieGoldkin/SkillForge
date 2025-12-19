"""Tests for hybrid evaluator.

This module tests the HybridEvaluator which provides a unified interface
for switching between local G-Eval, Langfuse evaluators, or both.

Issue #381: Langfuse LLM-as-Judge Evaluators
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.evaluation.evaluators.hybrid_evaluator import (
    HybridEvaluator,
    create_hybrid_evaluator,
)
from app.evaluation.types import Example, Run


class TestHybridEvaluator:
    """Tests for HybridEvaluator class."""

    def test_init_local_backend(self):
        """Test initialization with local backend."""
        evaluator = HybridEvaluator(aspect="relevance", backend="local")
        assert evaluator.aspect == "relevance"
        assert evaluator.backend == "local"
        assert evaluator.judge_model is None

    def test_init_langfuse_backend(self):
        """Test initialization with Langfuse backend."""
        evaluator = HybridEvaluator(aspect="depth", backend="langfuse")
        assert evaluator.aspect == "depth"
        assert evaluator.backend == "langfuse"

    def test_init_both_backend(self):
        """Test initialization with both backends."""
        evaluator = HybridEvaluator(aspect="coherence", backend="both")
        assert evaluator.aspect == "coherence"
        assert evaluator.backend == "both"

    def test_init_invalid_backend_raises_error(self):
        """Test that invalid backend raises ValueError."""
        with pytest.raises(ValueError, match="Invalid backend"):
            HybridEvaluator(aspect="relevance", backend="invalid")

    def test_init_invalid_aspect_raises_error(self):
        """Test that invalid aspect raises ValueError."""
        with pytest.raises(ValueError, match="Invalid aspect"):
            HybridEvaluator(aspect="invalid", backend="local")

    def test_init_with_custom_model(self):
        """Test initialization with custom judge model."""
        evaluator = HybridEvaluator(
            aspect="relevance", backend="langfuse", judge_model="gpt-4o-mini"
        )
        assert evaluator.judge_model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_evaluate_local_backend(self, mocker):
        """Test evaluation with local backend."""
        # Mock the local quality evaluator
        mock_evaluator_func = mocker.AsyncMock(
            return_value={"key": "quality_relevance", "score": 0.85, "comment": "Good"}
        )
        mocker.patch(
            "app.evaluation.evaluators.quality.create_quality_evaluator",
            return_value=mock_evaluator_func,
        )

        # Create evaluator
        evaluator = HybridEvaluator(aspect="relevance", backend="local")

        # Create mock run and example
        run = Run(
            id=uuid4(),
            name="test",
            run_type="chain",
            start_time=datetime.now(UTC),
            trace_id=uuid4(),
            inputs={"content": "input"},
            outputs={"insights": "output"},
        )
        example = Example(inputs={"content": "input"}, outputs={})

        # Evaluate
        result = await evaluator.evaluate(run, example)

        # Verify result
        assert result["key"] == "quality_relevance"
        assert result["score"] == 0.85
        assert result["comment"] == "Good"

        # Verify local evaluator was called
        mock_evaluator_func.assert_called_once_with(run, example)

    @pytest.mark.asyncio
    async def test_evaluate_langfuse_backend_success(self, mocker):
        """Test evaluation with Langfuse backend (successful)."""
        # Mock Langfuse evaluator
        mock_langfuse_evaluator = mocker.AsyncMock()
        mock_langfuse_evaluator.evaluate.return_value = 0.9

        mocker.patch(
            "app.shared.services.evaluators.langfuse_evaluators.create_langfuse_evaluator",
            return_value=mock_langfuse_evaluator,
        )

        # Mock content extraction
        mocker.patch(
            "app.evaluation.evaluators.quality._extract_evaluable_content",
            side_effect=lambda x: str(x),
        )

        # Create evaluator
        evaluator = HybridEvaluator(aspect="depth", backend="langfuse")

        # Create mock run and example
        run = Run(
            id=uuid4(),
            name="test",
            run_type="chain",
            start_time=datetime.now(UTC),
            trace_id=uuid4(),
            inputs={"content": "input"},
            outputs={"insights": "output"},
        )
        example = Example(inputs={"content": "input"}, outputs={})

        # Evaluate
        result = await evaluator.evaluate(run, example)

        # Verify result
        assert result["key"] == "quality_depth"
        assert result["score"] == 0.9
        assert "Langfuse evaluation" in result["comment"]

        # Verify Langfuse evaluator was called
        mock_langfuse_evaluator.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_langfuse_backend_fallback_to_local(self, mocker):
        """Test Langfuse backend falls back to local on error."""
        # Mock Langfuse evaluator to raise error
        mock_langfuse_evaluator = mocker.AsyncMock()
        mock_langfuse_evaluator.evaluate.side_effect = Exception("Langfuse API error")

        mocker.patch(
            "app.shared.services.evaluators.langfuse_evaluators.create_langfuse_evaluator",
            return_value=mock_langfuse_evaluator,
        )

        # Mock content extraction
        mocker.patch(
            "app.evaluation.evaluators.quality._extract_evaluable_content",
            side_effect=lambda x: str(x),
        )

        # Mock local evaluator
        mock_local_evaluator = mocker.AsyncMock(
            return_value={"key": "quality_depth", "score": 0.75, "comment": "Fallback"}
        )
        mocker.patch(
            "app.evaluation.evaluators.quality.create_quality_evaluator",
            return_value=mock_local_evaluator,
        )

        # Create evaluator
        evaluator = HybridEvaluator(aspect="depth", backend="langfuse")

        # Create mock run and example
        run = Run(
            id=uuid4(),
            name="test",
            run_type="chain",
            start_time=datetime.now(UTC),
            trace_id=uuid4(),
            inputs={"content": "input"},
            outputs={"insights": "output"},
        )
        example = Example(inputs={"content": "input"}, outputs={})

        # Evaluate
        result = await evaluator.evaluate(run, example)

        # Verify fallback result from local
        assert result["key"] == "quality_depth"
        assert result["score"] == 0.75
        assert result["comment"] == "Fallback"

        # Verify both evaluators were called
        mock_langfuse_evaluator.evaluate.assert_called_once()
        mock_local_evaluator.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_both_backend_comparison(self, mocker):
        """Test both backend runs both evaluators and logs comparison."""
        # Mock local evaluator
        mock_local_evaluator = mocker.AsyncMock(
            return_value={"key": "quality_coherence", "score": 0.8, "comment": "Local: Good"}
        )
        mocker.patch(
            "app.evaluation.evaluators.quality.create_quality_evaluator",
            return_value=mock_local_evaluator,
        )

        # Mock Langfuse evaluator
        mock_langfuse_evaluator = mocker.AsyncMock()
        mock_langfuse_evaluator.evaluate.return_value = 0.85

        mocker.patch(
            "app.shared.services.evaluators.langfuse_evaluators.create_langfuse_evaluator",
            return_value=mock_langfuse_evaluator,
        )

        # Mock content extraction
        mocker.patch(
            "app.evaluation.evaluators.quality._extract_evaluable_content",
            side_effect=lambda x: str(x),
        )

        # Create evaluator
        evaluator = HybridEvaluator(aspect="coherence", backend="both")

        # Create mock run and example
        run = Run(
            id=uuid4(),
            name="test",
            run_type="chain",
            start_time=datetime.now(UTC),
            trace_id=uuid4(),
            inputs={"content": "input"},
            outputs={"insights": "output"},
        )
        example = Example(inputs={"content": "input"}, outputs={})

        # Evaluate
        result = await evaluator.evaluate(run, example)

        # Verify result uses local score (primary)
        assert result["key"] == "quality_coherence"
        assert result["score"] == 0.8  # Local score

        # Verify comment includes comparison
        assert "Local: 0.80" in result["comment"]
        assert "Langfuse: 0.85" in result["comment"]
        assert "Diff:" in result["comment"]

        # Verify both evaluators were called
        mock_local_evaluator.assert_called_once()
        mock_langfuse_evaluator.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_both_backend_langfuse_error_continues(self, mocker):
        """Test both backend continues even if Langfuse fails."""
        # Mock local evaluator
        mock_local_evaluator = mocker.AsyncMock(
            return_value={"key": "quality_coherence", "score": 0.8, "comment": "Local"}
        )
        mocker.patch(
            "app.evaluation.evaluators.quality.create_quality_evaluator",
            return_value=mock_local_evaluator,
        )

        # Mock Langfuse evaluator to fail
        mock_langfuse_evaluator = mocker.AsyncMock()
        mock_langfuse_evaluator.evaluate.side_effect = Exception("API down")

        mocker.patch(
            "app.shared.services.evaluators.langfuse_evaluators.create_langfuse_evaluator",
            return_value=mock_langfuse_evaluator,
        )

        # Mock content extraction
        mocker.patch(
            "app.evaluation.evaluators.quality._extract_evaluable_content",
            side_effect=lambda x: str(x),
        )

        # Create evaluator
        evaluator = HybridEvaluator(aspect="coherence", backend="both")

        # Create mock run and example
        run = Run(
            id=uuid4(),
            name="test",
            run_type="chain",
            start_time=datetime.now(UTC),
            trace_id=uuid4(),
            inputs={"content": "input"},
            outputs={"insights": "output"},
        )
        example = Example(inputs={"content": "input"}, outputs={})

        # Evaluate
        result = await evaluator.evaluate(run, example)

        # Verify result uses local score
        assert result["key"] == "quality_coherence"
        assert result["score"] == 0.8

        # Verify comment includes Langfuse failure
        assert "Langfuse: 0.00" in result["comment"]

        # Verify both were attempted
        mock_local_evaluator.assert_called_once()
        mock_langfuse_evaluator.evaluate.assert_called_once()


class TestCreateHybridEvaluator:
    """Tests for create_hybrid_evaluator factory function."""

    def test_create_with_explicit_backend(self):
        """Test factory with explicit backend parameter."""
        evaluator = create_hybrid_evaluator("relevance", backend="langfuse")
        assert isinstance(evaluator, HybridEvaluator)
        assert evaluator.aspect == "relevance"
        assert evaluator.backend == "langfuse"

    def test_create_with_settings_backend(self, mocker):
        """Test factory uses settings when backend not provided."""
        # Mock settings
        mock_settings = mocker.Mock()
        mock_settings.EVALUATOR_BACKEND = "both"
        mocker.patch(
            "app.core.config.get_settings",
            return_value=mock_settings,
        )

        evaluator = create_hybrid_evaluator("depth")
        assert evaluator.backend == "both"

    def test_create_with_custom_model(self):
        """Test factory with custom judge model."""
        evaluator = create_hybrid_evaluator("coherence", backend="local", judge_model="gpt-4o-mini")
        assert evaluator.judge_model == "gpt-4o-mini"
