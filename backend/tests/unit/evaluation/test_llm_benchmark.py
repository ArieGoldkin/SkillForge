"""Unit tests for LLM benchmark module.

Tests focus on:
1. Synthesis target function field name mapping
2. Benchmark mode context variable isolation
3. Target function output structure validation
"""

from unittest.mock import MagicMock, patch

import pytest


class TestSynthesisTargetFieldMapping:
    """Tests for synthesis target function field name mapping.

    The synthesis target must return field names that match
    the AggregatedInsights schema exactly, otherwise the
    synthesis_correctness_evaluator will fail to validate outputs.
    """

    @pytest.fixture
    def mock_aggregate_findings_result(self):
        """Mock result from aggregate_findings task."""
        return {
            "aggregated_insights": {
                "executive_summary": "This is a test summary about FastAPI.",
                "key_findings": [
                    "FastAPI provides excellent async performance",
                    "Type hints enable auto-generated documentation",
                    "Security features need to be added manually",
                ],
                "synthesis": {
                    "technical_analysis": "Detailed technical analysis...",
                    "implementation_guidance": "Step by step guide...",
                    "risk_assessment": "Security risks identified...",
                    "recommendations": ["Use OAuth2", "Add rate limiting"],
                },
                "conflicts_resolved": [
                    {
                        "agents": ["security_auditor", "tech_comparator"],
                        "topic": "Authentication approach",
                        "resolution": "Use JWT with short expiry",
                    }
                ],
                "coverage_gaps": [
                    {
                        "missing_agent": "performance_analyst",
                        "reason": "Not selected by supervisor",
                    }
                ],
                "cross_domain_connections": [
                    {
                        "from_domain": "security",
                        "to_domain": "performance",
                        "connection": "JWT validation adds latency",
                    }
                ],
                "coverage_score": 0.75,
            }
        }

    @pytest.mark.asyncio
    @patch("app.evaluation.llm_benchmark.aggregate_findings")
    async def test_synthesis_target_returns_correct_field_names(
        self, mock_aggregate, mock_aggregate_findings_result
    ):
        """Test that synthesis target returns AggregatedInsights-compatible field names."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        mock_aggregate.return_value = mock_aggregate_findings_result

        benchmark = LLMBenchmark(local_mode=True)
        target = benchmark._create_synthesis_target("gpt-4o-mini")

        # Call the target function
        result = await target({"agent_findings": []})

        # Verify ALL expected field names are present (AggregatedInsights schema)
        expected_fields = [
            "executive_summary",
            "key_findings",
            "synthesis",
            "conflicts_resolved",
            "coverage_gaps",
            "cross_domain_connections",
            "coverage_score",
        ]

        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

        # Verify OLD incorrect field names are NOT present
        assert "summary" not in result, "Should not use 'summary' (use 'executive_summary')"
        assert "key_points" not in result, "Should not use 'key_points' (use 'key_findings')"

    @pytest.mark.asyncio
    @patch("app.evaluation.llm_benchmark.aggregate_findings")
    async def test_synthesis_target_preserves_field_values(
        self, mock_aggregate, mock_aggregate_findings_result
    ):
        """Test that synthesis target preserves actual values from aggregate_findings."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        mock_aggregate.return_value = mock_aggregate_findings_result

        benchmark = LLMBenchmark(local_mode=True)
        target = benchmark._create_synthesis_target("gpt-4o-mini")

        result = await target({"agent_findings": []})

        # Verify values are correctly passed through
        expected = mock_aggregate_findings_result["aggregated_insights"]
        assert result["executive_summary"] == expected["executive_summary"]
        assert result["key_findings"] == expected["key_findings"]
        assert result["synthesis"] == expected["synthesis"]
        assert result["coverage_score"] == expected["coverage_score"]
        assert len(result["cross_domain_connections"]) == 1

    @pytest.mark.asyncio
    @patch("app.evaluation.llm_benchmark.aggregate_findings")
    async def test_synthesis_target_handles_empty_aggregated_insights(self, mock_aggregate):
        """Test that synthesis target handles missing aggregated_insights gracefully."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        # Return empty aggregated_insights
        mock_aggregate.return_value = {"aggregated_insights": {}}

        benchmark = LLMBenchmark(local_mode=True)
        target = benchmark._create_synthesis_target("gpt-4o-mini")

        result = await target({"agent_findings": []})

        # Should return empty defaults, not crash
        assert result["executive_summary"] == ""
        assert result["key_findings"] == []
        assert result["synthesis"] == {}
        assert result["coverage_score"] == 0.0

    @pytest.mark.asyncio
    @patch("app.evaluation.llm_benchmark.aggregate_findings")
    async def test_synthesis_target_handles_missing_result_key(self, mock_aggregate):
        """Test that synthesis target handles missing 'aggregated_insights' key."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        # Return result without aggregated_insights key
        mock_aggregate.return_value = {}

        benchmark = LLMBenchmark(local_mode=True)
        target = benchmark._create_synthesis_target("gpt-4o-mini")

        result = await target({"agent_findings": []})

        # Should return empty defaults, not crash
        assert result["executive_summary"] == ""
        assert result["key_findings"] == []


class TestBenchmarkContextVariables:
    """Tests for benchmark context variable behavior."""

    def test_is_benchmark_mode_default_false(self):
        """Test that is_benchmark_mode returns False by default."""
        from app.evaluation.llm_benchmark import is_benchmark_mode

        assert is_benchmark_mode() is False

    def test_benchmark_mode_true_inside_context(self):
        """Test that is_benchmark_mode returns True inside context."""
        from app.evaluation.llm_benchmark import benchmark_model_context, is_benchmark_mode

        with benchmark_model_context("test-model"):
            assert is_benchmark_mode() is True

    def test_benchmark_mode_false_after_context(self):
        """Test that is_benchmark_mode returns False after context exits."""
        from app.evaluation.llm_benchmark import benchmark_model_context, is_benchmark_mode

        with benchmark_model_context("test-model"):
            pass  # Context active

        assert is_benchmark_mode() is False

    def test_model_id_set_inside_context(self):
        """Test that model_id is set correctly inside context."""
        from app.evaluation.llm_benchmark import (
            benchmark_model_context,
            get_benchmark_model_id,
        )

        with benchmark_model_context("claude-sonnet-4"):
            assert get_benchmark_model_id() == "claude-sonnet-4"

    def test_model_id_none_after_context(self):
        """Test that model_id returns to None after context exits."""
        from app.evaluation.llm_benchmark import (
            benchmark_model_context,
            get_benchmark_model_id,
        )

        with benchmark_model_context("claude-sonnet-4"):
            pass

        assert get_benchmark_model_id() is None


class TestBenchmarkAPIKeyValidation:
    """Tests for API key validation in benchmark."""

    @patch("app.evaluation.llm_benchmark.get_model_info")
    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_success(self, mock_settings, mock_get_model_info):
        """Test successful API key validation."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        # Mock model info
        mock_model_info = MagicMock()
        mock_model_info.api_key_field = "OPENAI_API_KEY"
        mock_model_info.provider = "openai"
        mock_get_model_info.return_value = mock_model_info

        # Mock valid API key
        mock_settings.OPENAI_API_KEY = "sk-valid-key-12345"

        benchmark = LLMBenchmark(local_mode=True)
        is_valid, error = benchmark.validate_api_key("gpt-4o-mini")

        assert is_valid is True
        assert error is None

    @patch("app.evaluation.llm_benchmark.get_model_info")
    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_missing(self, mock_settings, mock_get_model_info):
        """Test API key validation when key is missing."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        mock_model_info = MagicMock()
        mock_model_info.api_key_field = "OPENAI_API_KEY"
        mock_model_info.provider = "openai"
        mock_get_model_info.return_value = mock_model_info

        # Mock missing API key
        mock_settings.OPENAI_API_KEY = None

        benchmark = LLMBenchmark(local_mode=True)
        is_valid, error = benchmark.validate_api_key("gpt-4o-mini")

        assert is_valid is False
        assert "Missing" in error

    @patch("app.evaluation.llm_benchmark.get_model_info")
    @patch("app.evaluation.llm_benchmark.settings")
    def test_validate_api_key_placeholder(self, mock_settings, mock_get_model_info):
        """Test API key validation rejects placeholder keys."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        mock_model_info = MagicMock()
        mock_model_info.api_key_field = "OPENAI_API_KEY"
        mock_model_info.provider = "openai"
        mock_get_model_info.return_value = mock_model_info

        # Mock placeholder API key
        mock_settings.OPENAI_API_KEY = "sk-test-placeholder..."

        benchmark = LLMBenchmark(local_mode=True)
        is_valid, error = benchmark.validate_api_key("gpt-4o-mini")

        assert is_valid is False
        assert "placeholder" in error

    @patch("app.evaluation.llm_benchmark.get_model_info")
    def test_validate_api_key_unknown_model(self, mock_get_model_info):
        """Test API key validation for unknown model."""
        from app.evaluation.llm_benchmark import LLMBenchmark

        mock_get_model_info.return_value = None

        benchmark = LLMBenchmark(local_mode=True)
        is_valid, error = benchmark.validate_api_key("unknown-model-xyz")

        assert is_valid is False
        assert "not found" in error
