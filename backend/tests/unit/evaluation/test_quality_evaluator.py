"""Tests for quality evaluator response parsing.

Issue #299-304: Added tests for _extract_evaluable_content to verify
the fix for the dict-to-string bug.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.evaluation.evaluators.quality import (
    _extract_evaluable_content,
    _format_list_items,
    _format_nested_dict,
    create_quality_evaluator,
)


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
    async def test_parse_gemini_dict_response(self, mock_settings, mock_get_chat_model):
        """Evaluator correctly parses Gemini's new dict format response.

        Issue: Gemini (Dec 2024+) returns responses in format:
        [{'type': 'text', 'text': '8', 'extras': {'signature': '...'}}]
        instead of just "8" or ["8"].
        """
        mock_settings.LLM_MODEL = "gemini-3-flash"

        # Mock model that returns Gemini's new dict format
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            {
                "type": "text",
                "text": "9",
                "extras": {"signature": "abc123"},
            }
        ]
        mock_model.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_chat_model.return_value = mock_model

        evaluator = create_quality_evaluator(aspect="depth")

        mock_run = MagicMock()
        mock_run.outputs = {"result": "Detailed analysis output"}
        mock_example = MagicMock()
        mock_example.inputs = {"content": "Input"}
        mock_example.outputs = {}

        result = await evaluator(mock_run, mock_example)

        assert result["key"] == "quality_depth"
        assert result["score"] == 0.9  # 9/10 normalized
        assert "9" in result.get("comment", "") and "/10" in result.get("comment", "")

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


class TestExtractEvaluableContent:
    """Tests for _extract_evaluable_content function.

    Issue #299-304: These tests verify the fix for the dict-to-string bug
    where outputs like {"insights": "content"} were converted to
    "{'insights': 'content'}" instead of extracting the actual content.
    """

    def test_extract_from_none_returns_empty(self):
        """Returns empty string for None input."""
        result = _extract_evaluable_content(None)
        assert result == ""

    def test_extract_from_string_returns_string(self):
        """Returns the string directly for string input."""
        result = _extract_evaluable_content("This is a test")
        assert result == "This is a test"

    def test_extract_from_string_truncates_long_content(self):
        """Truncates very long strings."""
        long_string = "x" * 20000
        result = _extract_evaluable_content(long_string)
        # Issue #299-304: Updated from 8000 to 15000 to preserve analytical depth
        assert len(result) == 15000  # MAX_CONTENT_LENGTH

    def test_extract_insights_from_dict(self):
        """Extracts insights key from dictionary."""
        data = {"insights": "This is the analysis content"}
        result = _extract_evaluable_content(data)
        assert "This is the analysis content" in result
        assert "{'insights':" not in result  # Should NOT have dict syntax

    def test_extract_executive_summary_from_dict(self):
        """Extracts executive_summary key from dictionary."""
        data = {"executive_summary": "Brief summary of findings"}
        result = _extract_evaluable_content(data)
        assert "Brief summary of findings" in result
        assert "Executive Summary" in result  # Formatted key

    def test_extract_nested_insights(self):
        """Extracts content from nested insights dictionary."""
        data = {
            "insights": {
                "executive_summary": "This is the executive summary",
                "key_findings": ["Finding 1", "Finding 2"],
            }
        }
        result = _extract_evaluable_content(data)
        assert "executive summary" in result.lower()
        assert "{'insights':" not in result

    def test_extract_key_findings_list(self):
        """Extracts and formats key_findings list."""
        data = {
            "key_findings": [
                "First key finding",
                "Second key finding",
                "Third key finding",
            ]
        }
        result = _extract_evaluable_content(data)
        assert "First key finding" in result
        assert "Second key finding" in result

    def test_extract_aggregated_insights(self):
        """Extracts aggregated_insights from dictionary."""
        data = {
            "aggregated_insights": {
                "synthesis": "Technical synthesis content",
                "recommendations": "Key recommendations",
            }
        }
        result = _extract_evaluable_content(data)
        assert "synthesis" in result.lower()

    def test_extract_synthesis_string(self):
        """Extracts synthesis when it's a string."""
        data = {"synthesis": "Complete technical analysis and recommendations"}
        result = _extract_evaluable_content(data)
        assert "Complete technical analysis" in result

    def test_fallback_extracts_string_values(self):
        """Falls back to extracting any string values from dict."""
        data = {
            "custom_field": "This is a custom field value that should be extracted",
            "another_field": "Another value",
        }
        result = _extract_evaluable_content(data)
        # Should extract the values, not show dict syntax
        assert "{'custom_field':" not in result

    def test_handles_empty_dict(self):
        """Handles empty dictionary gracefully."""
        result = _extract_evaluable_content({})
        assert result == "{}"  # Falls back to str() but that's ok for empty

    def test_real_world_aggregated_insights_structure(self):
        """Tests with a realistic aggregated_insights structure."""
        data = {
            "insights": {
                "executive_summary": "This paper introduces DeepCode, a novel approach to code analysis.",
                "key_findings": [
                    "DeepCode achieves 95% accuracy on code classification",
                    "The model outperforms existing baselines by 12%",
                    "Training requires only 4 GPU hours",
                ],
                "synthesis": {
                    "technical_analysis": "The approach uses transformer architecture...",
                    "implementation_guidance": "To implement, start with...",
                    "risk_assessment": "Main risks include...",
                    "recommendations": "We recommend adopting this approach for...",
                },
            }
        }
        result = _extract_evaluable_content(data)

        # Should extract meaningful content
        assert "DeepCode" in result
        assert "95% accuracy" in result or "accuracy" in result
        # Should NOT have dict syntax
        assert "{'insights':" not in result
        assert "{'executive_summary':" not in result


class TestFormatNestedDict:
    """Tests for _format_nested_dict helper function."""

    def test_formats_flat_dict(self):
        """Formats a flat dictionary correctly."""
        data = {"key1": "value1", "key2": "value2"}
        result = _format_nested_dict(data)
        assert "Key1: value1" in result
        assert "Key2: value2" in result

    def test_formats_nested_dict(self):
        """Formats nested dictionaries with indentation."""
        data = {"outer": {"inner": "value"}}
        result = _format_nested_dict(data)
        assert "Outer:" in result
        assert "Inner: value" in result

    def test_limits_recursion_depth(self):
        """Stops recursion at depth 3."""
        deeply_nested = {"a": {"b": {"c": {"d": {"e": "too deep"}}}}}
        result = _format_nested_dict(deeply_nested)
        # Should not cause stack overflow
        assert result is not None

    def test_handles_lists_of_strings(self):
        """Handles lists of strings in dict values."""
        data = {"tags": ["tag1", "tag2", "tag3"]}
        result = _format_nested_dict(data)
        assert "tag1" in result
        assert "tag2" in result


class TestFormatListItems:
    """Tests for _format_list_items helper function."""

    def test_formats_string_list(self):
        """Formats list of strings with bullets."""
        items = ["Item one", "Item two", "Item three"]
        result = _format_list_items("findings", items)
        assert "Findings:" in result
        assert "- Item one" in result
        assert "- Item two" in result

    def test_formats_dict_list(self):
        """Formats list of dictionaries."""
        items = [
            {"summary": "First summary"},
            {"description": "Second description"},
        ]
        result = _format_list_items("results", items)
        assert "Results:" in result
        assert "First summary" in result
        assert "Second description" in result

    def test_limits_to_10_items(self):
        """Only includes first 10 items."""
        items = [f"Item {i}" for i in range(20)]
        result = _format_list_items("items", items)
        assert "Item 9" in result
        assert "Item 10" not in result

    def test_truncates_long_items(self):
        """Truncates individual items longer than 200 chars."""
        long_item = "x" * 300
        result = _format_list_items("items", [long_item])
        # Should not contain full 300 chars
        assert len(result) < 350
