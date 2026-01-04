"""Token counting utilities for cost tracking and context management.

This module provides utilities for counting tokens across different LLM providers
and estimating API costs. Uses tiktoken for accurate tokenization matching
the production models.

Usage:
    ```python
    from app.shared.services.llm.token_counter import TokenCounter

    # Count tokens in messages
    token_count = TokenCounter.count_messages(messages, model="gpt-4o")

    # Estimate API cost
    cost = TokenCounter.estimate_cost(1000, 500, "claude-3-5-sonnet")
    ```

Note:
    Pricing data is approximate and should be updated as providers change rates.
    Check provider documentation for current pricing.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import tiktoken
from langchain_core.messages import get_buffer_string

if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


class TokenCounter:
    """Count tokens for various LLM providers and estimate costs."""

    _encodings: ClassVar[dict[str, tiktoken.Encoding]] = {}

    @classmethod
    def count_messages(cls, messages: list[BaseMessage], model: str = "gpt-4") -> int:
        """Count tokens in a list of LangChain messages.

        Converts messages to text buffer and counts tokens using
        the appropriate encoding for the model.

        Args:
            messages: List of LangChain BaseMessage objects
            model: Model identifier for tokenization (default: "gpt-4")

        Returns:
            Total token count for all messages

        Example:
            >>> from langchain_core.messages import HumanMessage, AIMessage
            >>> messages = [
            ...     HumanMessage(content="Hello"),
            ...     AIMessage(content="Hi there!"),
            ... ]
            >>> count = TokenCounter.count_messages(messages)

        """
        buffer = get_buffer_string(messages)
        return cls.count_text(buffer, model)

    @classmethod
    def count_text(cls, text: str, model: str = "gpt-4") -> int:
        """Count tokens in a plain text string.

        Args:
            text: Text string to tokenize
            model: Model identifier for tokenization (default: "gpt-4")

        Returns:
            Token count

        Example:
            >>> count = TokenCounter.count_text("Hello world", "gpt-4o")

        """
        encoding = cls._get_encoding(model)
        return len(encoding.encode(text))

    @classmethod
    def _get_encoding(cls, model: str) -> tiktoken.Encoding:
        """Get or cache tiktoken encoding for model.

        Uses tiktoken's encoding_for_model when available, falls back
        to cl100k_base (GPT-4/GPT-3.5 encoding) for unknown models.

        Args:
            model: Model identifier

        Returns:
            tiktoken.Encoding instance

        """
        if model not in cls._encodings:
            try:
                cls._encodings[model] = tiktoken.encoding_for_model(model)
            except KeyError:
                # Fall back to cl100k_base for unknown models
                cls._encodings[model] = tiktoken.get_encoding("cl100k_base")
        return cls._encodings[model]

    @classmethod
    def estimate_cost(cls, input_tokens: int, output_tokens: int, model: str) -> float:
        """Estimate API cost in USD based on token counts.

        Pricing is per 1M tokens as of January 2025. For unknown models,
        uses conservative high-tier pricing.

        Args:
            input_tokens: Number of input (prompt) tokens
            output_tokens: Number of output (completion) tokens
            model: Model identifier

        Returns:
            Estimated cost in USD

        Example:
            >>> cost = TokenCounter.estimate_cost(1000, 500, "gpt-4o")
            >>> print(f"${cost:.4f}")

        Note:
            Pricing data should be periodically updated as providers change rates.
            Check https://openai.com/pricing and https://anthropic.com/pricing

        """
        # Pricing per 1M tokens (as of January 2025): tuple of (input, output) per 1M
        pricing = {
            "gpt-4o": (2.50, 10.00),
            "gpt-4o-mini": (0.15, 0.60),
            "claude-3-5-sonnet": (3.00, 15.00),
            "claude-3-5-haiku": (0.80, 4.00),
        }

        # Default to high-tier pricing for unknown models
        input_price, output_price = pricing.get(model, (5.0, 15.0))

        return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
