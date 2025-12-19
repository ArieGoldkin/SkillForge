"""Tests for Langfuse LLM-as-Judge evaluators.

This module tests the LangfuseEvaluatorService which provides
quality evaluation with Langfuse tracking and cost visibility.

Issue #381: Langfuse LLM-as-Judge Evaluators
"""

import pytest

from app.shared.services.evaluators.langfuse_evaluators import (
    LangfuseEvaluatorService,
    create_langfuse_evaluator,
)


class TestLangfuseEvaluatorService:
    """Tests for LangfuseEvaluatorService class."""

    def test_init_default_model(self):
        """Test initialization with default model."""
        service = LangfuseEvaluatorService()
        assert service.model is None

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        service = LangfuseEvaluatorService(model="gpt-4o-mini")
        assert service.model == "gpt-4o-mini"

    def test_get_rubric_relevance(self):
        """Test rubric retrieval for relevance criterion."""
        service = LangfuseEvaluatorService()
        rubric = service._get_rubric("relevance")
        assert "relevant" in rubric.lower()
        assert "1-3" in rubric
        assert "10" in rubric

    def test_get_rubric_depth(self):
        """Test rubric retrieval for depth criterion."""
        service = LangfuseEvaluatorService()
        rubric = service._get_rubric("depth")
        assert "depth" in rubric.lower() or "thorough" in rubric.lower()
        assert "1-3" in rubric
        assert "10" in rubric

    def test_get_rubric_coherence(self):
        """Test rubric retrieval for coherence criterion."""
        service = LangfuseEvaluatorService()
        rubric = service._get_rubric("coherence")
        assert "coherent" in rubric.lower() or "structure" in rubric.lower()
        assert "1-3" in rubric
        assert "10" in rubric

    def test_build_evaluation_prompt(self):
        """Test evaluation prompt construction."""
        service = LangfuseEvaluatorService()
        prompt = service._build_evaluation_prompt(
            criterion="relevance",
            rubric="Test rubric",
            input_content="Input content",
            output_content="Output content",
        )

        assert "relevance" in prompt
        assert "Test rubric" in prompt
        assert "Input content" in prompt
        assert "Output content" in prompt
        assert "<reasoning>" in prompt
        assert "<score>" in prompt

    def test_parse_score_simple_string(self):
        """Test score parsing from simple string response."""
        service = LangfuseEvaluatorService()

        # Test valid score
        response = "<reasoning>Good analysis</reasoning>\n<score>8</score>"
        score = service._parse_score(response, "relevance")
        assert 0.0 <= score <= 1.0
        # Score 8 should map to (8-1)/9 = 0.778
        assert abs(score - 0.778) < 0.01

    def test_parse_score_gemini_format(self):
        """Test score parsing from Gemini's list format."""
        service = LangfuseEvaluatorService()

        # Gemini format: [{'type': 'text', 'text': '...'}]
        response = [{"type": "text", "text": "<score>9</score>"}]
        score = service._parse_score(response, "depth")
        assert 0.0 <= score <= 1.0
        # Score 9 should map to (9-1)/9 = 0.889
        assert abs(score - 0.889) < 0.01

    def test_parse_score_clamping(self):
        """Test score clamping to valid range."""
        service = LangfuseEvaluatorService()

        # Score above 10 should be clamped
        response = "<score>15</score>"
        score = service._parse_score(response, "relevance")
        assert score == 1.0  # (10-1)/9 = 1.0

    def test_parse_score_missing_tags(self):
        """Test score parsing when tags are missing but number exists."""
        service = LangfuseEvaluatorService()

        # Number without tags
        response = "The score is 7"
        score = service._parse_score(response, "coherence")
        assert 0.0 <= score <= 1.0
        # Score 7 should map to (7-1)/9 = 0.667
        assert abs(score - 0.667) < 0.01

    def test_parse_score_no_number_raises_error(self):
        """Test that parsing fails when no score is found."""
        service = LangfuseEvaluatorService()

        with pytest.raises(ValueError, match="Failed to parse score"):
            service._parse_score("No score here", "relevance")

    @pytest.mark.asyncio
    async def test_evaluate_invalid_criterion_raises_error(self):
        """Test that invalid criterion raises ValueError."""
        service = LangfuseEvaluatorService()

        with pytest.raises(ValueError, match="Unsupported criterion"):
            await service.evaluate(
                trace_id=None,
                input_content="test",
                output_content="test",
                criterion="invalid_criterion",
            )

    def test_create_langfuse_evaluator(self):
        """Test factory function for creating evaluators."""
        evaluator = create_langfuse_evaluator("relevance")
        assert isinstance(evaluator, LangfuseEvaluatorService)
        assert evaluator.model is None

    def test_create_langfuse_evaluator_with_model(self):
        """Test factory function with custom model."""
        evaluator = create_langfuse_evaluator("depth", model="gpt-4o-mini")
        assert isinstance(evaluator, LangfuseEvaluatorService)
        assert evaluator.model == "gpt-4o-mini"


class TestLangfuseEvaluatorIntegration:
    """Integration tests for Langfuse evaluators (with mocked LLM calls)."""

    @pytest.mark.asyncio
    async def test_evaluate_with_mocked_llm(self, mocker):
        """Test evaluation with mocked LLM response."""
        # Mock the chat model
        mock_model = mocker.AsyncMock()
        mock_response = mocker.Mock()
        mock_response.content = "<reasoning>Highly relevant</reasoning>\n<score>9</score>"
        mock_model.ainvoke.return_value = mock_response

        mocker.patch(
            "app.shared.services.evaluators.langfuse_evaluators.get_chat_model",
            return_value=mock_model,
        )

        # Mock score submission
        mocker.patch(
            "app.core.langfuse_config.submit_langfuse_score"
        )

        # Test evaluation
        service = LangfuseEvaluatorService()
        score = await service.evaluate(
            trace_id="test-trace-123",
            input_content="Test input content",
            output_content="Test output content",
            criterion="relevance",
        )

        # Verify score
        assert 0.0 <= score <= 1.0
        # Score 9 should map to (9-1)/9 = 0.889
        assert abs(score - 0.889) < 0.01

        # Verify LLM was called
        mock_model.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_evaluate_handles_llm_error(self, mocker):
        """Test that evaluation propagates LLM errors."""
        # Mock the chat model to raise an error
        mock_model = mocker.AsyncMock()
        mock_model.ainvoke.side_effect = Exception("LLM API error")

        mocker.patch(
            "app.shared.services.evaluators.langfuse_evaluators.get_chat_model",
            return_value=mock_model,
        )

        # Test evaluation
        service = LangfuseEvaluatorService()
        with pytest.raises(Exception, match="LLM API error"):
            await service.evaluate(
                trace_id="test-trace-123",
                input_content="Test input",
                output_content="Test output",
                criterion="depth",
            )

    @pytest.mark.asyncio
    async def test_evaluate_with_gemini_response_format(self, mocker):
        """Test evaluation with Gemini's dict response format."""
        # Mock the chat model with Gemini format
        mock_model = mocker.AsyncMock()
        mock_response = mocker.Mock()
        mock_response.content = [
            {"type": "text", "text": "<reasoning>Deep analysis</reasoning>\n<score>8</score>"}
        ]
        mock_model.ainvoke.return_value = mock_response

        mocker.patch(
            "app.shared.services.evaluators.langfuse_evaluators.get_chat_model",
            return_value=mock_model,
        )

        # Mock score submission
        mocker.patch(
            "app.core.langfuse_config.submit_langfuse_score"
        )

        # Test evaluation
        service = LangfuseEvaluatorService()
        score = await service.evaluate(
            trace_id="test-trace-123",
            input_content="Test input",
            output_content="Test output",
            criterion="depth",
        )

        # Verify score
        assert 0.0 <= score <= 1.0
        # Score 8 should map to (8-1)/9 = 0.778
        assert abs(score - 0.778) < 0.01
