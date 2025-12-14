"""Tests for LLM benchmark utilities."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.evaluation.llm_benchmark import (
    LLMBenchmark,
    benchmark_model_context,
    get_benchmark_model_id,
    is_benchmark_mode,
)


class TestBenchmarkModelContext:
    """Tests for the benchmark_model_context context manager."""

    def test_sets_model_id(self):
        """Context manager sets the model ID correctly."""
        assert get_benchmark_model_id() is None

        with benchmark_model_context("gpt-4o-mini"):
            assert get_benchmark_model_id() == "gpt-4o-mini"

        # Should reset after exit
        assert get_benchmark_model_id() is None

    def test_sets_benchmark_mode(self):
        """Context manager sets benchmark mode to True."""
        assert is_benchmark_mode() is False

        with benchmark_model_context("claude-haiku-3-5-20241022"):
            assert is_benchmark_mode() is True

        # Should reset after exit
        assert is_benchmark_mode() is False

    def test_resets_on_exception(self):
        """Context manager resets state even on exception."""
        assert get_benchmark_model_id() is None
        assert is_benchmark_mode() is False

        with pytest.raises(ValueError):
            with benchmark_model_context("test-model"):
                assert get_benchmark_model_id() == "test-model"
                assert is_benchmark_mode() is True
                raise ValueError("Test error")

        # Should still reset after exception
        assert get_benchmark_model_id() is None
        assert is_benchmark_mode() is False

    def test_nested_contexts(self):
        """Nested contexts work correctly."""
        with benchmark_model_context("outer-model"):
            assert get_benchmark_model_id() == "outer-model"

            with benchmark_model_context("inner-model"):
                assert get_benchmark_model_id() == "inner-model"

            # Inner context reset, outer still active
            assert get_benchmark_model_id() == "outer-model"

        assert get_benchmark_model_id() is None


class TestLLMBenchmarkValidation:
    """Tests for LLMBenchmark API key validation."""

    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_openai_valid(self, mock_settings):
        """Valid OpenAI API key returns True."""
        mock_settings.OPENAI_API_KEY = "sk-real-key-here"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None

        benchmark = LLMBenchmark(project_name="test", local_mode=True)
        is_valid, error = benchmark.validate_api_key("gpt-5-mini")

        assert is_valid is True
        assert error is None

    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_openai_missing(self, mock_settings):
        """Missing OpenAI API key returns False with error."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None

        benchmark = LLMBenchmark(project_name="test", local_mode=True)
        is_valid, error = benchmark.validate_api_key("gpt-5-mini")

        assert is_valid is False
        assert "OPENAI_API_KEY" in error

    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_anthropic_valid(self, mock_settings):
        """Valid Anthropic API key returns True."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = "sk-ant-real-key"
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = None

        benchmark = LLMBenchmark(project_name="test", local_mode=True)
        is_valid, error = benchmark.validate_api_key("claude-haiku-3-5-20241022")

        assert is_valid is True
        assert error is None

    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_google_valid(self, mock_settings):
        """Valid Google API key returns True."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = "google-real-key"
        mock_settings.XAI_API_KEY = None

        benchmark = LLMBenchmark(project_name="test", local_mode=True)
        is_valid, error = benchmark.validate_api_key("gemini-2.5-flash")

        assert is_valid is True
        assert error is None

    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_xai_valid(self, mock_settings):
        """Valid xAI API key returns True."""
        mock_settings.OPENAI_API_KEY = None
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = None
        mock_settings.XAI_API_KEY = "xai-real-key"

        benchmark = LLMBenchmark(project_name="test", local_mode=True)
        is_valid, error = benchmark.validate_api_key("grok-3-mini")

        assert is_valid is True
        assert error is None

    @patch("app.evaluation.llm_benchmark.settings")
    def test_get_available_models(self, mock_settings):
        """get_available_models filters by API key availability."""
        mock_settings.OPENAI_API_KEY = "sk-real-key"
        mock_settings.ANTHROPIC_API_KEY = None
        mock_settings.GOOGLE_API_KEY = "google-real-key"
        mock_settings.XAI_API_KEY = None

        benchmark = LLMBenchmark(project_name="test", local_mode=True)
        models = ["gpt-5-mini", "claude-haiku-3-5-20241022", "gemini-2.5-flash", "grok-3-mini"]

        available, errors = benchmark.get_available_models(models)

        assert "gpt-5-mini" in available
        assert "gemini-2.5-flash" in available
        assert "claude-haiku-3-5-20241022" not in available
        assert "grok-3-mini" not in available
        assert "claude-haiku-3-5-20241022" in errors
        assert "grok-3-mini" in errors

    def test_validate_api_key_unknown_model(self):
        """Unknown model returns False with appropriate error."""
        benchmark = LLMBenchmark(project_name="test", local_mode=True)
        is_valid, error = benchmark.validate_api_key("unknown-model-xyz")

        assert is_valid is False
        assert "not found in registry" in error
