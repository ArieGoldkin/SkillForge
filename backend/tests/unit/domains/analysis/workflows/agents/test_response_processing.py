"""Unit tests for response processing - multi-provider structured output extraction.

Issue #586: Tests for Gemini vs Anthropic/OpenAI response format handling.

Gemini's `with_structured_output(strict=True)` returns Pydantic models directly,
while Anthropic/OpenAI wrap in {"structured_response": model}. These tests ensure
both formats are handled correctly.

TDD: These tests were written BEFORE the fix to ensure proper coverage.
"""

import pytest
from pydantic import BaseModel

from app.domains.analysis.workflows.agents.response_processing import (
    extract_structured_response,
)


# ============================================================================
# Test Fixtures - Mock Pydantic Models
# ============================================================================


class MockKeyInsightsOutput(BaseModel):
    """Mock Pydantic model simulating KeyInsightsOutput."""

    insights: list[dict]
    summary: str
    confidence_score: float


class MockTechComparisonOutput(BaseModel):
    """Mock Pydantic model simulating TechComparisonOutput."""

    comparisons: list[dict]
    recommendation: str
    confidence_score: float


# ============================================================================
# Tests: Wrapped Format (Anthropic/OpenAI Pattern)
# ============================================================================


class TestExtractStructuredResponseWrappedFormat:
    """Tests for wrapped format: {"structured_response": PydanticModel}."""

    def test_extracts_from_wrapped_pydantic_model(self):
        """Test extracting from Anthropic/OpenAI wrapped format."""
        mock_model = MockKeyInsightsOutput(
            insights=[
                {"title": "Test Insight", "description": "Description", "importance": "high"}
            ],
            summary="Test summary",
            confidence_score=0.85,
        )
        wrapped_result = {"structured_response": mock_model}

        result = extract_structured_response(wrapped_result, "key_insights")

        assert result["summary"] == "Test summary"
        assert result["confidence_score"] == 0.85
        assert len(result["insights"]) == 1
        assert result["insights"][0]["title"] == "Test Insight"

    def test_extracts_tech_comparison_wrapped_format(self):
        """Test extracting TechComparison from wrapped format."""
        mock_model = MockTechComparisonOutput(
            comparisons=[{"tech_a": "React", "tech_b": "Vue", "winner": "React"}],
            recommendation="Use React for this project",
            confidence_score=0.90,
        )
        wrapped_result = {"structured_response": mock_model}

        result = extract_structured_response(wrapped_result, "tech_comparator")

        assert result["recommendation"] == "Use React for this project"
        assert result["confidence_score"] == 0.90
        assert len(result["comparisons"]) == 1


# ============================================================================
# Tests: Direct Pydantic Model (Gemini Pattern)
# ============================================================================


class TestExtractStructuredResponseDirectPydantic:
    """Tests for direct Pydantic model format (Gemini 2.5+ pattern).

    Gemini's `with_structured_output(strict=True)` returns the Pydantic model
    directly without wrapping in {"structured_response": model}.
    """

    def test_extracts_from_direct_pydantic_model(self):
        """Test extracting from Gemini's direct Pydantic model return."""
        # Gemini returns Pydantic model directly, not wrapped
        direct_result = MockKeyInsightsOutput(
            insights=[
                {"title": "Direct Insight", "description": "From Gemini", "importance": "high"}
            ],
            summary="Direct summary from Gemini",
            confidence_score=0.88,
        )

        result = extract_structured_response(direct_result, "key_insights")

        assert result["summary"] == "Direct summary from Gemini"
        assert result["confidence_score"] == 0.88
        assert len(result["insights"]) == 1
        assert result["insights"][0]["title"] == "Direct Insight"

    def test_extracts_tech_comparison_direct_pydantic(self):
        """Test extracting TechComparison from direct Pydantic model."""
        direct_result = MockTechComparisonOutput(
            comparisons=[{"tech_a": "FastAPI", "tech_b": "Django", "winner": "FastAPI"}],
            recommendation="FastAPI for async performance",
            confidence_score=0.92,
        )

        result = extract_structured_response(direct_result, "tech_comparator")

        assert result["recommendation"] == "FastAPI for async performance"
        assert result["confidence_score"] == 0.92

    def test_handles_empty_insights_list(self):
        """Test handling direct Pydantic model with empty insights."""
        direct_result = MockKeyInsightsOutput(
            insights=[],
            summary="No insights found",
            confidence_score=0.50,
        )

        result = extract_structured_response(direct_result, "key_insights")

        assert result["insights"] == []
        assert result["summary"] == "No insights found"


# ============================================================================
# Tests: Error Cases
# ============================================================================


class TestExtractStructuredResponseErrors:
    """Tests for error handling in response extraction."""

    def test_raises_runtime_error_for_none_result(self):
        """Test that None result raises RuntimeError."""
        with pytest.raises(RuntimeError, match="returned no result"):
            extract_structured_response(None, "key_insights")

    def test_raises_runtime_error_for_missing_structured_response_in_dict(self):
        """Test that dict without structured_response raises RuntimeError."""
        invalid_dict = {"some_key": "some_value"}

        with pytest.raises(RuntimeError, match="did not return structured_response"):
            extract_structured_response(invalid_dict, "key_insights")

    def test_raises_type_error_for_non_pydantic_in_wrapper(self):
        """Test that non-Pydantic value in wrapper raises TypeError."""
        invalid_wrapped = {"structured_response": {"plain": "dict"}}

        with pytest.raises(TypeError, match="not a Pydantic model"):
            extract_structured_response(invalid_wrapped, "key_insights")

    def test_raises_type_error_for_plain_string(self):
        """Test that plain string raises appropriate error."""
        with pytest.raises((TypeError, RuntimeError)):
            extract_structured_response("plain string", "key_insights")

    def test_raises_type_error_for_plain_list(self):
        """Test that plain list raises appropriate error."""
        with pytest.raises((TypeError, RuntimeError)):
            extract_structured_response(["item1", "item2"], "key_insights")


# ============================================================================
# Tests: Edge Cases & Multi-Provider Compatibility
# ============================================================================


class TestMultiProviderCompatibility:
    """Tests ensuring all supported LLM providers work correctly."""

    def test_anthropic_format_compatibility(self):
        """Simulate Anthropic Claude response format."""
        # Anthropic returns wrapped format
        anthropic_response = {
            "structured_response": MockKeyInsightsOutput(
                insights=[{"title": "Anthropic", "description": "Test", "importance": "medium"}],
                summary="From Claude",
                confidence_score=0.87,
            )
        }

        result = extract_structured_response(anthropic_response, "key_insights")
        assert result["summary"] == "From Claude"

    def test_openai_format_compatibility(self):
        """Simulate OpenAI GPT-4 response format."""
        # OpenAI also returns wrapped format
        openai_response = {
            "structured_response": MockKeyInsightsOutput(
                insights=[{"title": "OpenAI", "description": "Test", "importance": "high"}],
                summary="From GPT-4",
                confidence_score=0.89,
            )
        }

        result = extract_structured_response(openai_response, "key_insights")
        assert result["summary"] == "From GPT-4"

    def test_gemini_format_compatibility(self):
        """Simulate Gemini 2.5 Flash response format."""
        # Gemini returns direct Pydantic model
        gemini_response = MockKeyInsightsOutput(
            insights=[{"title": "Gemini", "description": "Test", "importance": "high"}],
            summary="From Gemini 2.5 Flash",
            confidence_score=0.91,
        )

        result = extract_structured_response(gemini_response, "key_insights")
        assert result["summary"] == "From Gemini 2.5 Flash"

    def test_all_agents_work_with_both_formats(self):
        """Parameterized test ensuring all agent types work with both formats."""
        agent_types = [
            "key_insights",
            "tech_comparator",
            "security_auditor",
            "implementation_planner",
            "learning_path_builder",
        ]

        for agent_type in agent_types:
            # Test wrapped format
            wrapped = {
                "structured_response": MockKeyInsightsOutput(
                    insights=[],
                    summary="Wrapped",
                    confidence_score=0.8,
                )
            }
            result = extract_structured_response(wrapped, agent_type)
            assert "summary" in result

            # Test direct Pydantic format
            direct = MockKeyInsightsOutput(
                insights=[],
                summary="Direct",
                confidence_score=0.8,
            )
            result = extract_structured_response(direct, agent_type)
            assert "summary" in result
