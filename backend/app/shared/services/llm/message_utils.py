"""Standard message content block utilities for provider-agnostic handling.

This module provides utilities for working with LangChain's standard message
content blocks, which can contain text, tool calls, reasoning, and other
structured content.

Usage:
    ```python
    from app.shared.services.llm.message_utils import MessageUtils

    # Extract text from message (handles both string and block content)
    text = MessageUtils.extract_text(ai_message)

    # Extract Claude extended thinking/reasoning
    reasoning = MessageUtils.extract_reasoning(ai_message)

    # Get token usage metadata
    usage = MessageUtils.get_usage_metadata(ai_message)
    ```

See Also:
    - LangChain Message Types: https://python.langchain.com/docs/concepts/messages/
    - Claude Extended Thinking: https://docs.anthropic.com/en/docs/build-with-claude/thinking

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from langchain_core.messages import AIMessage


class MessageUtils:
    """Utilities for handling standard LangChain message content blocks.

    LangChain messages can have content in two formats:
    1. Simple string: message.content = "Hello"
    2. List of blocks: message.content = [{"type": "text", "text": "Hello"}, ...]

    This class provides utilities to extract information from both formats.
    """

    @staticmethod
    def extract_text(message: AIMessage) -> str:
        """Extract plain text from message, handling both string and block content.

        Args:
            message: AIMessage from LangChain LLM response

        Returns:
            Concatenated text content (blocks joined with newlines)

        Example:
            >>> from langchain_core.messages import AIMessage
            >>> msg = AIMessage(content="Hello world")
            >>> text = MessageUtils.extract_text(msg)
            >>> print(text)
            Hello world

            >>> msg = AIMessage(
            ...     content=[
            ...         {"type": "text", "text": "First part"},
            ...         {"type": "text", "text": "Second part"},
            ...     ]
            ... )
            >>> text = MessageUtils.extract_text(msg)
            >>> print(text)
            First part
            Second part

        """
        if isinstance(message.content, str):
            return message.content

        # Handle list of content blocks
        text_parts = []
        for block in message.content:
            if isinstance(block, str):
                text_parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "\n".join(text_parts)

    @staticmethod
    def extract_reasoning(message: AIMessage) -> str | None:
        """Extract reasoning/thinking from Claude extended thinking responses.

        Claude can return extended thinking blocks that show its reasoning
        process before the final answer. This extracts that content.

        Args:
            message: AIMessage from Claude LLM response

        Returns:
            Reasoning/thinking text if present, otherwise None

        Example:
            >>> msg = AIMessage(
            ...     content=[
            ...         {"type": "thinking", "thinking": "Let me analyze..."},
            ...         {"type": "text", "text": "The answer is 42"},
            ...     ]
            ... )
            >>> reasoning = MessageUtils.extract_reasoning(msg)
            >>> print(reasoning)
            Let me analyze...

        See Also:
            https://docs.anthropic.com/en/docs/build-with-claude/thinking

        """
        if isinstance(message.content, str):
            return None

        for block in message.content:
            if isinstance(block, dict):
                # Claude uses "thinking" type
                if block.get("type") == "thinking":
                    return block.get("thinking")
                # Generic "reasoning" type (future-proof)
                if block.get("type") == "reasoning":
                    return block.get("reasoning")

        return None

    @staticmethod
    def extract_tool_calls(message: AIMessage) -> list[Any]:
        """Extract tool calls from message content blocks.

        LangChain standardizes tool calls in the tool_calls attribute.
        This provides safe extraction with fallback to empty list.

        Args:
            message: AIMessage from LLM response

        Returns:
            List of ToolCall objects, or empty list if none

        Example:
            >>> msg = AIMessage(
            ...     content="I'll use the calculator",
            ...     tool_calls=[
            ...         {
            ...             "name": "calculator",
            ...             "args": {"expression": "2 + 2"},
            ...             "id": "call_123",
            ...         }
            ...     ],
            ... )
            >>> calls = MessageUtils.extract_tool_calls(msg)
            >>> print(calls[0]["name"])
            calculator

        Note:
            Returns langchain_core.messages.ToolCall objects when available.

        """
        if not hasattr(message, "tool_calls"):
            return []
        return message.tool_calls or []

    @staticmethod
    def get_usage_metadata(message: AIMessage) -> dict[str, int]:
        """Extract token usage from message if available.

        LangChain providers can attach usage metadata to messages.
        This extracts it in a standardized format.

        Args:
            message: AIMessage from LLM response

        Returns:
            Dict with input_tokens, output_tokens, total_tokens
            (all 0 if no usage metadata available)

        Example:
            >>> msg = AIMessage(
            ...     content="Hello",
            ...     usage_metadata={
            ...         "input_tokens": 10,
            ...         "output_tokens": 5,
            ...         "total_tokens": 15,
            ...     },
            ... )
            >>> usage = MessageUtils.get_usage_metadata(msg)
            >>> print(f"Used {usage['total_tokens']} tokens")
            Used 15 tokens

        """
        if hasattr(message, "usage_metadata") and message.usage_metadata:
            return {
                "input_tokens": message.usage_metadata.get("input_tokens", 0),
                "output_tokens": message.usage_metadata.get("output_tokens", 0),
                "total_tokens": message.usage_metadata.get("total_tokens", 0),
            }

        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
