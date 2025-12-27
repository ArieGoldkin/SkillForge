"""Unit tests for tracing constants and cost calculation.

Tests the calculate_llm_cost() function and validates LLM pricing configuration
for accurate cost tracking across all supported models.
"""

from app.core.tracing_constants import (
    DEFAULT_PRICING,
    LLM_PRICING,
    TRACE_TAGS,
    calculate_llm_cost,
)


class TestCalculateLLMCost:
    """Test suite for LLM cost calculation function."""

    def test_claude_3_5_sonnet_pricing(self) -> None:
        """Test Claude 3.5 Sonnet pricing calculation.

        Example from docstring:
        1000 input tokens = 1000/1M * $3.00 = $0.003
        500 output tokens = 500/1M * $15.00 = $0.0075
        Total = $0.0105
        """
        cost = calculate_llm_cost("claude-3-5-sonnet-20241022", 1000, 500)
        assert cost == 0.0105

    def test_claude_3_5_sonnet_20240620(self) -> None:
        """Test older Claude 3.5 Sonnet variant pricing."""
        cost = calculate_llm_cost("claude-3-5-sonnet-20240620", 1000, 500)
        assert cost == 0.0105

    def test_gpt_4o_pricing(self) -> None:
        """Test GPT-4o pricing calculation.

        GPT-4o: $2.50/1M input, $10.00/1M output
        2000 input = 2000/1M * $2.50 = $0.005
        1000 output = 1000/1M * $10.00 = $0.010
        Total = $0.015
        """
        cost = calculate_llm_cost("gpt-4o", 2000, 1000)
        assert cost == 0.015

    def test_gpt_4o_mini_pricing(self) -> None:
        """Test GPT-4o-mini pricing (cheapest GPT-4 variant).

        GPT-4o-mini: $0.15/1M input, $0.60/1M output
        """
        cost = calculate_llm_cost("gpt-4o-mini", 10000, 5000)
        expected = (10000 / 1_000_000 * 0.15) + (5000 / 1_000_000 * 0.60)
        assert cost == round(expected, 6)

    def test_claude_opus_pricing(self) -> None:
        """Test Claude 3 Opus pricing (most expensive model).

        Claude Opus: $15.00/1M input, $75.00/1M output
        """
        cost = calculate_llm_cost("claude-3-opus-20240229", 1000, 1000)
        expected = (1000 / 1_000_000 * 15.00) + (1000 / 1_000_000 * 75.00)
        assert cost == 0.09

    def test_claude_haiku_pricing(self) -> None:
        """Test Claude 3 Haiku pricing (cheapest Anthropic model).

        Claude Haiku: $0.25/1M input, $1.25/1M output
        """
        cost = calculate_llm_cost("claude-3-haiku-20240307", 5000, 2000)
        expected = (5000 / 1_000_000 * 0.25) + (2000 / 1_000_000 * 1.25)
        assert cost == round(expected, 6)

    def test_unknown_model_uses_default_pricing(self) -> None:
        """Test that unknown models use DEFAULT_PRICING fallback.

        DEFAULT_PRICING: $1.00/1M input, $2.00/1M output
        """
        cost = calculate_llm_cost("unknown-model-xyz", 1000, 500)
        expected = (1000 / 1_000_000 * DEFAULT_PRICING["input"]) + (
            500 / 1_000_000 * DEFAULT_PRICING["output"]
        )
        assert cost == round(expected, 6)

    def test_zero_tokens_zero_cost(self) -> None:
        """Test that zero tokens result in zero cost."""
        cost = calculate_llm_cost("claude-3-5-sonnet-20241022", 0, 0)
        assert cost == 0.0

    def test_only_input_tokens(self) -> None:
        """Test cost calculation with only input tokens (no output)."""
        cost = calculate_llm_cost("gpt-4o", 1000, 0)
        expected = 1000 / 1_000_000 * 2.50
        assert cost == round(expected, 6)

    def test_only_output_tokens(self) -> None:
        """Test cost calculation with only output tokens (no input)."""
        cost = calculate_llm_cost("gpt-4o", 0, 1000)
        expected = 1000 / 1_000_000 * 10.00
        assert cost == round(expected, 6)

    def test_large_token_counts(self) -> None:
        """Test cost calculation with millions of tokens.

        Simulates a large batch processing scenario.
        """
        # 5 million input tokens + 2 million output tokens
        cost = calculate_llm_cost("claude-3-5-sonnet-20241022", 5_000_000, 2_000_000)
        expected = (5_000_000 / 1_000_000 * 3.00) + (2_000_000 / 1_000_000 * 15.00)
        assert cost == 45.0

    def test_result_rounded_to_6_decimals(self) -> None:
        """Test that result is rounded to exactly 6 decimal places.

        Uses a calculation that would produce more than 6 decimals.
        """
        # 7 tokens input, 3 tokens output (creates long decimal)
        cost = calculate_llm_cost("claude-3-5-sonnet-20241022", 7, 3)
        # Manual calculation: (7/1M * 3.00) + (3/1M * 15.00)
        # = 0.000021 + 0.000045 = 0.000066
        assert cost == 0.000066
        # Verify it's exactly 6 decimal places (no more, no less)
        assert len(str(cost).split(".")[-1]) <= 6

    def test_fractional_cents_handling(self) -> None:
        """Test handling of sub-cent costs (typical for small requests)."""
        cost = calculate_llm_cost("gpt-4o-mini", 100, 50)
        expected = (100 / 1_000_000 * 0.15) + (50 / 1_000_000 * 0.60)
        assert cost == round(expected, 6)
        assert cost < 0.001  # Less than 1/10th of a cent


class TestLLMPricingCoverage:
    """Test that all models in LLM_PRICING have correct pricing structure."""

    def test_all_models_have_input_output_pricing(self) -> None:
        """Verify all 11 models have both input and output pricing."""
        assert len(LLM_PRICING) == 11
        for model, pricing in LLM_PRICING.items():
            assert "input" in pricing, f"{model} missing input pricing"
            assert "output" in pricing, f"{model} missing output pricing"
            assert isinstance(pricing["input"], (int, float)), f"{model} input not numeric"
            assert isinstance(pricing["output"], (int, float)), f"{model} output not numeric"
            assert pricing["input"] > 0, f"{model} input pricing must be positive"
            assert pricing["output"] > 0, f"{model} output pricing must be positive"

    def test_claude_models_coverage(self) -> None:
        """Test that all Claude model variants are included."""
        claude_models = [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-sonnet-20240620",
            "claude-3-opus-20240229",
            "claude-3-haiku-20240307",
        ]
        for model in claude_models:
            assert model in LLM_PRICING, f"Missing {model} in pricing table"

    def test_gpt_models_coverage(self) -> None:
        """Test that all GPT model variants are included."""
        gpt_models = [
            "gpt-4-turbo-preview",
            "gpt-4-turbo-2024-04-09",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-3.5-turbo",
        ]
        for model in gpt_models:
            assert model in LLM_PRICING, f"Missing {model} in pricing table"

    def test_gemini_models_coverage(self) -> None:
        """Test that all Gemini model variants are included."""
        gemini_models = [
            "gemini-pro",
            "gemini-1.5-pro",
        ]
        for model in gemini_models:
            assert model in LLM_PRICING, f"Missing {model} in pricing table"

    def test_output_pricing_higher_than_input(self) -> None:
        """Verify that output tokens are always more expensive than input.

        This is a universal pattern across all LLM providers.
        """
        for model, pricing in LLM_PRICING.items():
            assert pricing["output"] > pricing["input"], (
                f"{model}: output pricing should exceed input pricing"
            )

    def test_pricing_reasonable_ranges(self) -> None:
        """Sanity check: pricing values are within reasonable ranges.

        As of Jan 2025, typical pricing:
        - Input: $0.15/1M (cheap) to $15.00/1M (expensive)
        - Output: $0.60/1M (cheap) to $75.00/1M (expensive)
        """
        for model, pricing in LLM_PRICING.items():
            assert 0.10 <= pricing["input"] <= 20.00, (
                f"{model} input pricing seems unrealistic: ${pricing['input']}"
            )
            assert 0.50 <= pricing["output"] <= 100.00, (
                f"{model} output pricing seems unrealistic: ${pricing['output']}"
            )


class TestDefaultPricing:
    """Test the default pricing fallback for unknown models."""

    def test_default_pricing_structure(self) -> None:
        """Verify DEFAULT_PRICING has correct structure."""
        assert "input" in DEFAULT_PRICING
        assert "output" in DEFAULT_PRICING
        assert DEFAULT_PRICING["input"] == 1.00
        assert DEFAULT_PRICING["output"] == 2.00

    def test_default_pricing_is_conservative(self) -> None:
        """Verify DEFAULT_PRICING is mid-range (conservative estimate).

        Should not be cheapest (to avoid underestimating costs) or most
        expensive (to avoid over-alarming for unknown models).
        """
        all_input_prices = [p["input"] for p in LLM_PRICING.values()]
        all_output_prices = [p["output"] for p in LLM_PRICING.values()]

        # Should be above minimum but below maximum
        assert DEFAULT_PRICING["input"] > min(all_input_prices)
        assert DEFAULT_PRICING["input"] < max(all_input_prices)
        assert DEFAULT_PRICING["output"] > min(all_output_prices)
        assert DEFAULT_PRICING["output"] < max(all_output_prices)


class TestTraceTags:
    """Test trace tags configuration for Langfuse categorization."""

    def test_trace_tags_coverage(self) -> None:
        """Verify all expected trace tags are present."""
        expected_tags = [
            "parsing",
            "validation",
            "llm_call",
            "retry",
            "db_query",
            "sse_event",
            "self_correction",
            "result_processing",
            "specificity",
        ]
        assert len(TRACE_TAGS) == 9
        for tag in expected_tags:
            assert tag in TRACE_TAGS, f"Missing trace tag: {tag}"
            assert isinstance(TRACE_TAGS[tag], str)
            assert len(TRACE_TAGS[tag]) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_negative_tokens_not_validated(self) -> None:
        """Document that negative tokens are not validated.

        NOTE: This is current behavior. Function does not validate inputs.
        Negative tokens can produce unexpected results.
        """
        # This is allowed (but shouldn't happen in practice)
        # Negative input tokens create negative input cost
        cost_negative_input = calculate_llm_cost("gpt-4o", -1000, 100)
        # Expected: (-1000/1M * 2.50) + (100/1M * 10.00)
        # = -0.0025 + 0.001 = -0.0015
        assert cost_negative_input < 0

        # If negative output tokens offset by positive input
        cost_negative_output = calculate_llm_cost("gpt-4o", 1000, -100)
        # Expected: (1000/1M * 2.50) + (-100/1M * 10.00)
        # = 0.0025 + (-0.001) = 0.0015
        assert cost_negative_output > 0

    def test_very_small_token_counts(self) -> None:
        """Test that single-token costs are calculated correctly."""
        cost = calculate_llm_cost("claude-3-5-sonnet-20241022", 1, 1)
        expected = (1 / 1_000_000 * 3.00) + (1 / 1_000_000 * 15.00)
        assert cost == round(expected, 6)

    def test_model_name_case_sensitivity(self) -> None:
        """Document that model names are case-sensitive.

        Uppercase or mixed-case model names will use DEFAULT_PRICING.
        """
        lowercase_cost = calculate_llm_cost("gpt-4o", 1000, 500)
        uppercase_cost = calculate_llm_cost("GPT-4O", 1000, 500)

        # Case matters - uppercase uses default pricing
        assert lowercase_cost != uppercase_cost
        assert uppercase_cost == calculate_llm_cost("unknown", 1000, 500)

    def test_whitespace_in_model_name(self) -> None:
        """Document that whitespace in model names uses DEFAULT_PRICING.

        Model names must match exactly (no leading/trailing spaces).
        """
        valid_cost = calculate_llm_cost("gpt-4o", 1000, 500)
        invalid_cost = calculate_llm_cost(" gpt-4o ", 1000, 500)

        # Whitespace causes fallback to default pricing
        assert valid_cost != invalid_cost


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_typical_chat_completion(self) -> None:
        """Test cost for a typical chat completion request.

        Scenario: User asks a question, gets a detailed response
        - Input: ~500 tokens (conversation history + new question)
        - Output: ~1500 tokens (detailed answer)
        """
        cost = calculate_llm_cost("claude-3-5-sonnet-20241022", 500, 1500)
        expected = (500 / 1_000_000 * 3.00) + (1500 / 1_000_000 * 15.00)
        assert cost == 0.024

    def test_batch_processing_scenario(self) -> None:
        """Test cost for batch processing scenario.

        Scenario: Processing 100 documents with GPT-4o
        - Average input: 2000 tokens/doc
        - Average output: 500 tokens/doc
        - Total: 200K input, 50K output tokens
        """
        total_input = 200_000
        total_output = 50_000
        cost = calculate_llm_cost("gpt-4o", total_input, total_output)
        expected = (total_input / 1_000_000 * 2.50) + (total_output / 1_000_000 * 10.00)
        assert cost == 1.0

    def test_code_generation_scenario(self) -> None:
        """Test cost for code generation task.

        Scenario: Generate implementation from requirements
        - Input: 800 tokens (requirements + context)
        - Output: 3000 tokens (generated code + explanation)
        """
        cost = calculate_llm_cost("gpt-4o", 800, 3000)
        expected = (800 / 1_000_000 * 2.50) + (3000 / 1_000_000 * 10.00)
        assert cost == round(expected, 6)

    def test_budget_comparison_across_models(self) -> None:
        """Compare costs for same workload across different models.

        Helps validate pricing differences between providers.
        """
        input_tokens = 10_000
        output_tokens = 5_000

        claude_cost = calculate_llm_cost("claude-3-5-sonnet-20241022", input_tokens, output_tokens)
        gpt4o_cost = calculate_llm_cost("gpt-4o", input_tokens, output_tokens)
        haiku_cost = calculate_llm_cost("claude-3-haiku-20240307", input_tokens, output_tokens)
        mini_cost = calculate_llm_cost("gpt-4o-mini", input_tokens, output_tokens)

        # Haiku and GPT-4o-mini should be cheapest
        assert haiku_cost < claude_cost
        assert mini_cost < gpt4o_cost

        # Claude Sonnet and GPT-4o should be more expensive
        assert claude_cost > mini_cost
        assert gpt4o_cost > mini_cost
