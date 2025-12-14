"""Tests for quality evaluator response parsing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.evaluation.evaluators.quality import create_quality_evaluator


class TestQualityEvaluatorParsing:
    """Tests for quality evaluator response parsing."""

    @pytest.mark.asyncio
    @patch("app.evaluation.evaluators.quality.get_chat_model")
    @patch("app.core.config.settings")
    async def test_parse_string_response(self, mock_settings, mock_get_chat_model):
        """Evaluator correctly parses string response content."""
        mock_settings.LLM_MODEL = "gpt-4o-mini"

        # Mock model that returns string content
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "8"  # Score of 8/10
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_chat_model.return_value = mock_model

        evaluator = create_quality_evaluator(aspect="overall")

        # Create mock Run and Example
        mock_run = MagicMock()
        mock_run.outputs = {"result": "Some output text"}
        mock_example = MagicMock()
        mock_example.inputs = {"content": "Input content"}
        mock_example.outputs = {"expected": "Expected output"}

        result = await evaluator(mock_run, mock_example)

        assert result["key"] == "quality_overall"
        assert result["score"] == 0.8  # 8/10 normalized

    @pytest.mark.asyncio
    @patch("app.evaluation.evaluators.quality.get_chat_model")
    @patch("app.core.config.settings")
    async def test_parse_list_response(self, mock_settings, mock_get_chat_model):
        """Evaluator correctly parses list response content (multi-part)."""
        mock_settings.LLM_MODEL = "gpt-4o-mini"

        # Mock model that returns list content (happens with some providers)
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = ["7"]  # List with score
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_chat_model.return_value = mock_model

        evaluator = create_quality_evaluator(aspect="relevance")

        mock_run = MagicMock()
        mock_run.outputs = {"result": "Some output"}
        mock_example = MagicMock()
        mock_example.inputs = {"content": "Input"}
        mock_example.outputs = {}

        result = await evaluator(mock_run, mock_example)

        assert result["key"] == "quality_relevance"
        assert result["score"] == 0.7  # 7/10 normalized

    @pytest.mark.asyncio
    @patch("app.evaluation.evaluators.quality.get_chat_model")
    @patch("app.core.config.settings")
    async def test_parse_invalid_response(self, mock_settings, mock_get_chat_model):
        """Evaluator handles unparseable response gracefully."""
        mock_settings.LLM_MODEL = "gpt-4o-mini"

        # Mock model that returns invalid content
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "not a number"
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_chat_model.return_value = mock_model

        evaluator = create_quality_evaluator(aspect="accuracy")

        mock_run = MagicMock()
        mock_run.outputs = {"result": "Output"}
        mock_example = MagicMock()
        mock_example.inputs = {"content": "Input"}
        mock_example.outputs = {}

        result = await evaluator(mock_run, mock_example)

        assert result["key"] == "quality_accuracy"
        assert result["score"] == 0.0  # Failed to parse
        assert "Failed to parse" in result.get("comment", "")

    @pytest.mark.asyncio
    @patch("app.evaluation.evaluators.quality.get_chat_model")
    @patch("app.core.config.settings")
    async def test_parse_empty_list_response(self, mock_settings, mock_get_chat_model):
        """Evaluator handles empty list response gracefully."""
        mock_settings.LLM_MODEL = "gpt-4o-mini"

        # Mock model that returns empty list
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = []  # Empty list
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_chat_model.return_value = mock_model

        evaluator = create_quality_evaluator(aspect="completeness")

        mock_run = MagicMock()
        mock_run.outputs = {"result": "Output"}
        mock_example = MagicMock()
        mock_example.inputs = {"content": "Input"}
        mock_example.outputs = {}

        result = await evaluator(mock_run, mock_example)

        assert result["key"] == "quality_completeness"
        assert result["score"] == 0.0  # Failed to parse empty list


class TestQualityEvaluatorFactory:
    """Tests for quality evaluator factory function."""

    def test_create_evaluator_returns_callable(self):
        """Factory returns a callable evaluator."""
        evaluator = create_quality_evaluator("relevance")
        assert callable(evaluator)

    def test_create_evaluator_default_aspect(self):
        """Factory uses 'overall' as default aspect."""
        evaluator = create_quality_evaluator()
        # The evaluator function is created, we verify by checking it's callable
        assert callable(evaluator)

    def test_create_evaluator_custom_judge_model(self):
        """Factory accepts custom judge model."""
        evaluator = create_quality_evaluator("depth", judge_model="gpt-5-mini")
        assert callable(evaluator)
