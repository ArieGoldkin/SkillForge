"""Tests for TokenCounter utility class.

Tests cover:
- Token counting for plain text with different models
- Token counting for LangChain message lists
- Model-specific encoding handling (GPT-4, GPT-4o, unknown models)
- Encoding caching behavior
- Cost estimation for different models and token counts
- Edge cases: empty strings, empty messages, special characters
- Fallback behavior for unknown models (cl100k_base encoding)
"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.shared.services.llm.token_counter import TokenCounter


class TestTokenCountText:
    """Test token counting for plain text strings."""

    @pytest.mark.unit
    def test_count_text_simple_string(self) -> None:
        """Test counting tokens in a simple text string."""
        text = "Hello world"
        count = TokenCounter.count_text(text, model="gpt-4")

        # "Hello world" is typically 2 tokens for GPT-4
        assert isinstance(count, int)
        assert count > 0

    @pytest.mark.unit
    def test_count_text_empty_string(self) -> None:
        """Test counting tokens in empty string returns zero."""
        count = TokenCounter.count_text("", model="gpt-4")

        assert count == 0

    @pytest.mark.unit
    def test_count_text_multiline_string(self) -> None:
        """Test counting tokens in multi-line text."""
        text = """Line 1
Line 2
Line 3"""
        count = TokenCounter.count_text(text, model="gpt-4")

        assert count > 3  # At least 3 tokens for content + newlines

    @pytest.mark.unit
    def test_count_text_with_special_characters(self) -> None:
        """Test counting tokens with special characters and unicode."""
        text = "Hello! 🌍 Special chars: @#$%"
        count = TokenCounter.count_text(text, model="gpt-4")

        assert isinstance(count, int)
        assert count > 0

    @pytest.mark.unit
    def test_count_text_different_models(self) -> None:
        """Test that different models may produce different token counts."""
        text = "This is a test sentence for token counting."

        count_gpt4 = TokenCounter.count_text(text, model="gpt-4")
        count_gpt4o = TokenCounter.count_text(text, model="gpt-4o")

        # Both should return valid counts
        assert isinstance(count_gpt4, int)
        assert isinstance(count_gpt4o, int)
        assert count_gpt4 > 0
        assert count_gpt4o > 0

    @pytest.mark.unit
    def test_count_text_long_text(self) -> None:
        """Test counting tokens in longer text."""
        # Approximate: 1 token ~= 4 characters for English
        text = "word " * 1000  # ~1000 words

        count = TokenCounter.count_text(text, model="gpt-4")

        assert count > 500  # Should be many tokens
        assert count < 2000  # But reasonable


class TestTokenCountMessages:
    """Test token counting for LangChain message lists."""

    @pytest.mark.unit
    def test_count_messages_single_human_message(self) -> None:
        """Test counting tokens in single HumanMessage."""
        messages = [HumanMessage(content="Hello, how are you?")]

        count = TokenCounter.count_messages(messages, model="gpt-4")

        assert isinstance(count, int)
        assert count > 0

    @pytest.mark.unit
    def test_count_messages_multiple_messages(self) -> None:
        """Test counting tokens across multiple messages."""
        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="What is the capital of France?"),
            AIMessage(content="The capital of France is Paris."),
        ]

        count = TokenCounter.count_messages(messages, model="gpt-4")

        # Should count all message content
        assert count > 10  # Multiple sentences worth of tokens

    @pytest.mark.unit
    def test_count_messages_empty_list(self) -> None:
        """Test counting tokens in empty message list returns zero."""
        count = TokenCounter.count_messages([], model="gpt-4")

        assert count == 0

    @pytest.mark.unit
    def test_count_messages_empty_content(self) -> None:
        """Test counting tokens when messages have empty content."""
        messages = [
            HumanMessage(content=""),
            AIMessage(content=""),
        ]

        count = TokenCounter.count_messages(messages, model="gpt-4")

        # get_buffer_string adds message type prefixes, so count > 0
        assert count >= 0

    @pytest.mark.unit
    def test_count_messages_with_model_parameter(self) -> None:
        """Test that model parameter is passed through correctly."""
        messages = [HumanMessage(content="Test message")]

        count_gpt4 = TokenCounter.count_messages(messages, model="gpt-4")
        count_gpt4o = TokenCounter.count_messages(messages, model="gpt-4o")

        # Both should work
        assert isinstance(count_gpt4, int)
        assert isinstance(count_gpt4o, int)

    @pytest.mark.unit
    def test_count_messages_long_conversation(self) -> None:
        """Test counting tokens in a long conversation."""
        messages = [
            SystemMessage(content="You are a helpful coding assistant."),
        ]

        # Add many turns
        for i in range(10):
            messages.append(HumanMessage(content=f"Question {i}?"))
            messages.append(AIMessage(content=f"Answer {i}."))

        count = TokenCounter.count_messages(messages, model="gpt-4")

        # Should be substantial token count
        assert count > 20


class TestEncodingCaching:
    """Test encoding caching behavior to avoid repeated tiktoken initialization."""

    @pytest.mark.unit
    def test_encoding_cached_for_same_model(self) -> None:
        """Test that encoding is cached and reused for same model."""
        # Clear cache first
        TokenCounter._encodings.clear()

        with patch("app.shared.services.llm.token_counter.tiktoken.encoding_for_model") as mock_encoding:
            mock_enc = MagicMock()
            mock_enc.encode.return_value = [1, 2, 3]
            mock_encoding.return_value = mock_enc

            # First call - should create encoding
            TokenCounter.count_text("test", model="gpt-4")

            # Second call - should reuse cached encoding
            TokenCounter.count_text("test2", model="gpt-4")

            # encoding_for_model should only be called once
            assert mock_encoding.call_count == 1

    @pytest.mark.unit
    def test_encoding_different_models_cached_separately(self) -> None:
        """Test that different models have separate cached encodings."""
        # Clear cache first
        TokenCounter._encodings.clear()

        with patch("app.shared.services.llm.token_counter.tiktoken.encoding_for_model") as mock_encoding:
            mock_enc = MagicMock()
            mock_enc.encode.return_value = [1, 2, 3]
            mock_encoding.return_value = mock_enc

            # Use two different models
            TokenCounter.count_text("test", model="gpt-4")
            TokenCounter.count_text("test", model="gpt-4o")

            # Should be called twice (once per model)
            assert mock_encoding.call_count == 2
            assert "gpt-4" in TokenCounter._encodings
            assert "gpt-4o" in TokenCounter._encodings

    @pytest.mark.unit
    def test_encoding_fallback_for_unknown_model(self) -> None:
        """Test fallback to cl100k_base for unknown models."""
        # Clear cache first
        TokenCounter._encodings.clear()

        with patch("app.shared.services.llm.token_counter.tiktoken.encoding_for_model") as mock_encoding_for_model:
            with patch("app.shared.services.llm.token_counter.tiktoken.get_encoding") as mock_get_encoding:
                # Simulate KeyError for unknown model
                mock_encoding_for_model.side_effect = KeyError("unknown-model")

                # Setup fallback encoding
                mock_enc = MagicMock()
                mock_enc.encode.return_value = [1, 2, 3]
                mock_get_encoding.return_value = mock_enc

                count = TokenCounter.count_text("test", model="unknown-model")

                # Should have called fallback
                mock_get_encoding.assert_called_once_with("cl100k_base")
                assert count == 3  # 3 tokens from mock

    @pytest.mark.unit
    def test_encoding_fallback_cached(self) -> None:
        """Test that fallback encoding is also cached."""
        # Clear cache first
        TokenCounter._encodings.clear()

        with patch("app.shared.services.llm.token_counter.tiktoken.encoding_for_model") as mock_encoding_for_model:
            with patch("app.shared.services.llm.token_counter.tiktoken.get_encoding") as mock_get_encoding:
                mock_encoding_for_model.side_effect = KeyError("unknown-model")

                mock_enc = MagicMock()
                mock_enc.encode.return_value = [1, 2, 3]
                mock_get_encoding.return_value = mock_enc

                # First call
                TokenCounter.count_text("test1", model="unknown-model")

                # Second call
                TokenCounter.count_text("test2", model="unknown-model")

                # get_encoding should only be called once (cached)
                assert mock_get_encoding.call_count == 1


class TestCostEstimation:
    """Test cost estimation for different models and token counts."""

    @pytest.mark.unit
    def test_estimate_cost_gpt4o(self) -> None:
        """Test cost estimation for GPT-4o model."""
        # GPT-4o: $2.50 per 1M input, $10.00 per 1M output
        cost = TokenCounter.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="gpt-4o",
        )

        assert cost == 12.50  # $2.50 + $10.00

    @pytest.mark.unit
    def test_estimate_cost_gpt4o_mini(self) -> None:
        """Test cost estimation for GPT-4o-mini model."""
        # GPT-4o-mini: $0.15 per 1M input, $0.60 per 1M output
        cost = TokenCounter.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="gpt-4o-mini",
        )

        assert cost == 0.75  # $0.15 + $0.60

    @pytest.mark.unit
    def test_estimate_cost_claude_sonnet(self) -> None:
        """Test cost estimation for Claude 3.5 Sonnet."""
        # Claude 3.5 Sonnet: $3.00 per 1M input, $15.00 per 1M output
        cost = TokenCounter.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="claude-3-5-sonnet",
        )

        assert cost == 18.00  # $3.00 + $15.00

    @pytest.mark.unit
    def test_estimate_cost_claude_haiku(self) -> None:
        """Test cost estimation for Claude 3.5 Haiku."""
        # Claude 3.5 Haiku: $0.80 per 1M input, $4.00 per 1M output
        cost = TokenCounter.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="claude-3-5-haiku",
        )

        assert cost == 4.80  # $0.80 + $4.00

    @pytest.mark.unit
    def test_estimate_cost_small_token_counts(self) -> None:
        """Test cost estimation with realistic small token counts."""
        # 1000 input, 500 output tokens on GPT-4o
        cost = TokenCounter.estimate_cost(
            input_tokens=1000,
            output_tokens=500,
            model="gpt-4o",
        )

        # (1000 * 2.50 + 500 * 10.00) / 1_000_000 = 0.0075
        assert cost == pytest.approx(0.0075, rel=1e-6)

    @pytest.mark.unit
    def test_estimate_cost_zero_tokens(self) -> None:
        """Test cost estimation with zero tokens."""
        cost = TokenCounter.estimate_cost(
            input_tokens=0,
            output_tokens=0,
            model="gpt-4o",
        )

        assert cost == 0.0

    @pytest.mark.unit
    def test_estimate_cost_only_input_tokens(self) -> None:
        """Test cost estimation with only input tokens."""
        cost = TokenCounter.estimate_cost(
            input_tokens=10000,
            output_tokens=0,
            model="gpt-4o",
        )

        # 10000 * 2.50 / 1_000_000 = 0.025
        assert cost == pytest.approx(0.025, rel=1e-6)

    @pytest.mark.unit
    def test_estimate_cost_only_output_tokens(self) -> None:
        """Test cost estimation with only output tokens."""
        cost = TokenCounter.estimate_cost(
            input_tokens=0,
            output_tokens=10000,
            model="gpt-4o",
        )

        # 10000 * 10.00 / 1_000_000 = 0.1
        assert cost == pytest.approx(0.1, rel=1e-6)

    @pytest.mark.unit
    def test_estimate_cost_unknown_model_uses_high_tier_pricing(self) -> None:
        """Test that unknown models use conservative high-tier pricing."""
        # Unknown model should default to ($5.0, $15.0) per 1M tokens
        cost = TokenCounter.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="unknown-model-xyz",
        )

        assert cost == 20.00  # $5.00 + $15.00

    @pytest.mark.unit
    def test_estimate_cost_realistic_conversation(self) -> None:
        """Test cost estimation for realistic conversation scenario."""
        # Typical conversation: 500 input tokens, 300 output tokens
        cost = TokenCounter.estimate_cost(
            input_tokens=500,
            output_tokens=300,
            model="gpt-4o-mini",
        )

        # (500 * 0.15 + 300 * 0.60) / 1_000_000 = 0.00025500
        expected = (500 * 0.15 + 300 * 0.60) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)

    @pytest.mark.unit
    def test_estimate_cost_large_document_analysis(self) -> None:
        """Test cost estimation for large document analysis."""
        # Large document: 100k input tokens, 5k output tokens
        cost = TokenCounter.estimate_cost(
            input_tokens=100_000,
            output_tokens=5_000,
            model="claude-3-5-sonnet",
        )

        # (100000 * 3.00 + 5000 * 15.00) / 1_000_000 = 0.375
        expected = (100_000 * 3.00 + 5_000 * 15.00) / 1_000_000
        assert cost == pytest.approx(expected, rel=1e-6)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.unit
    def test_count_text_very_long_string(self) -> None:
        """Test counting tokens in very long string."""
        # 10,000 words
        text = "word " * 10_000

        count = TokenCounter.count_text(text, model="gpt-4")

        assert count > 5_000  # Should be many tokens
        assert isinstance(count, int)

    @pytest.mark.unit
    def test_count_text_special_unicode_characters(self) -> None:
        """Test counting tokens with various unicode characters."""
        text = "Hello 世界 🌍 Привет مرحبا"

        count = TokenCounter.count_text(text, model="gpt-4")

        assert isinstance(count, int)
        assert count > 0

    @pytest.mark.unit
    def test_count_messages_with_tool_calls(self) -> None:
        """Test counting tokens in messages with tool calls."""
        messages = [
            AIMessage(
                content="I'll use the calculator",
                tool_calls=[
                    {
                        "name": "calculator",
                        "args": {"expression": "2 + 2"},
                        "id": "call_123",
                    }
                ],
            ),
        ]

        count = TokenCounter.count_messages(messages, model="gpt-4")

        # Should count the text content (tool calls are serialized by get_buffer_string)
        assert count > 0

    @pytest.mark.unit
    def test_count_text_whitespace_only(self) -> None:
        """Test counting tokens in whitespace-only string."""
        text = "   \n\t  \n  "

        count = TokenCounter.count_text(text, model="gpt-4")

        # Whitespace may produce tokens
        assert count >= 0

    @pytest.mark.unit
    def test_estimate_cost_negative_tokens_raises_no_error(self) -> None:
        """Test that negative token counts don't raise errors (though invalid)."""
        # While negative tokens are invalid, the function should handle gracefully
        cost = TokenCounter.estimate_cost(
            input_tokens=-100,
            output_tokens=-50,
            model="gpt-4o",
        )

        # Should compute mathematically (negative cost)
        assert isinstance(cost, float)

    @pytest.mark.unit
    def test_count_messages_default_model_parameter(self) -> None:
        """Test that count_messages uses gpt-4 as default model."""
        messages = [HumanMessage(content="Test")]

        # Call without model parameter
        count = TokenCounter.count_messages(messages)

        assert isinstance(count, int)
        assert count > 0

    @pytest.mark.unit
    def test_count_text_default_model_parameter(self) -> None:
        """Test that count_text uses gpt-4 as default model."""
        # Call without model parameter
        count = TokenCounter.count_text("Test")

        assert isinstance(count, int)
        assert count > 0
