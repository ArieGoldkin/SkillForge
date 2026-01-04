"""Tests for MessageUtils utility class.

Tests cover:
- extract_text() with string content and block content
- extract_reasoning() for Claude extended thinking
- extract_tool_calls() from message attributes
- get_usage_metadata() for token tracking
- Edge cases: empty messages, missing attributes, mixed content types
- Content block formats: text, thinking, reasoning, tool calls
"""

import pytest
from langchain_core.messages import AIMessage

from app.shared.services.llm.message_utils import MessageUtils


class TestExtractText:
    """Test extracting plain text from messages."""

    @pytest.mark.unit
    def test_extract_text_from_string_content(self) -> None:
        """Test extracting text when content is a simple string."""
        message = AIMessage(content="Hello, this is a test message.")

        text = MessageUtils.extract_text(message)

        assert text == "Hello, this is a test message."

    @pytest.mark.unit
    def test_extract_text_from_empty_string(self) -> None:
        """Test extracting text from empty string content."""
        message = AIMessage(content="")

        text = MessageUtils.extract_text(message)

        assert text == ""

    @pytest.mark.unit
    def test_extract_text_from_single_text_block(self) -> None:
        """Test extracting text from single content block."""
        message = AIMessage(
            content=[
                {"type": "text", "text": "This is a text block."},
            ]
        )

        text = MessageUtils.extract_text(message)

        assert text == "This is a text block."

    @pytest.mark.unit
    def test_extract_text_from_multiple_text_blocks(self) -> None:
        """Test extracting text from multiple content blocks (joined with newlines)."""
        message = AIMessage(
            content=[
                {"type": "text", "text": "First paragraph."},
                {"type": "text", "text": "Second paragraph."},
                {"type": "text", "text": "Third paragraph."},
            ]
        )

        text = MessageUtils.extract_text(message)

        expected = "First paragraph.\nSecond paragraph.\nThird paragraph."
        assert text == expected

    @pytest.mark.unit
    def test_extract_text_ignores_non_text_blocks(self) -> None:
        """Test that non-text blocks (thinking, tool_use) are ignored."""
        message = AIMessage(
            content=[
                {"type": "text", "text": "User-visible text."},
                {"type": "thinking", "thinking": "Internal reasoning..."},
                {"type": "tool_use", "name": "search", "input": {"query": "test"}},
                {"type": "text", "text": "More visible text."},
            ]
        )

        text = MessageUtils.extract_text(message)

        # Should only extract text blocks
        expected = "User-visible text.\nMore visible text."
        assert text == expected

    @pytest.mark.unit
    def test_extract_text_from_empty_block_list(self) -> None:
        """Test extracting text from empty content block list."""
        message = AIMessage(content=[])

        text = MessageUtils.extract_text(message)

        assert text == ""

    @pytest.mark.unit
    def test_extract_text_with_missing_text_field(self) -> None:
        """Test extracting text when text block is missing 'text' field."""
        message = AIMessage(
            content=[
                {"type": "text", "text": "Valid text."},
                {"type": "text"},  # Missing 'text' field
                {"type": "text", "text": "More valid text."},
            ]
        )

        text = MessageUtils.extract_text(message)

        # Missing field should be treated as empty string
        expected = "Valid text.\n\nMore valid text."
        assert text == expected

    @pytest.mark.unit
    def test_extract_text_with_string_blocks(self) -> None:
        """Test extracting text when content list contains raw strings."""
        message = AIMessage(
            content=[
                "First string",
                {"type": "text", "text": "Text block"},
                "Second string",
            ]
        )

        text = MessageUtils.extract_text(message)

        expected = "First string\nText block\nSecond string"
        assert text == expected

    @pytest.mark.unit
    def test_extract_text_preserves_whitespace(self) -> None:
        """Test that whitespace in text content is preserved."""
        message = AIMessage(content="  Leading and trailing spaces  ")

        text = MessageUtils.extract_text(message)

        assert text == "  Leading and trailing spaces  "

    @pytest.mark.unit
    def test_extract_text_with_newlines_in_content(self) -> None:
        """Test that newlines within text blocks are preserved."""
        message = AIMessage(content="Line 1\nLine 2\nLine 3")

        text = MessageUtils.extract_text(message)

        assert text == "Line 1\nLine 2\nLine 3"


class TestExtractReasoning:
    """Test extracting reasoning/thinking from Claude extended thinking."""

    @pytest.mark.unit
    def test_extract_reasoning_from_thinking_block(self) -> None:
        """Test extracting reasoning from Claude 'thinking' block."""
        message = AIMessage(
            content=[
                {"type": "thinking", "thinking": "Let me analyze this step by step..."},
                {"type": "text", "text": "The answer is 42."},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        assert reasoning == "Let me analyze this step by step..."

    @pytest.mark.unit
    def test_extract_reasoning_from_reasoning_block(self) -> None:
        """Test extracting reasoning from generic 'reasoning' block (future-proof)."""
        message = AIMessage(
            content=[
                {"type": "reasoning", "reasoning": "First, I'll consider the constraints..."},
                {"type": "text", "text": "Based on this analysis..."},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        assert reasoning == "First, I'll consider the constraints..."

    @pytest.mark.unit
    def test_extract_reasoning_returns_none_for_string_content(self) -> None:
        """Test that reasoning returns None when content is a string."""
        message = AIMessage(content="Regular text response")

        reasoning = MessageUtils.extract_reasoning(message)

        assert reasoning is None

    @pytest.mark.unit
    def test_extract_reasoning_returns_none_when_not_present(self) -> None:
        """Test that reasoning returns None when no reasoning block present."""
        message = AIMessage(
            content=[
                {"type": "text", "text": "Just a regular response."},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        assert reasoning is None

    @pytest.mark.unit
    def test_extract_reasoning_returns_first_thinking_block(self) -> None:
        """Test that only the first thinking block is returned."""
        message = AIMessage(
            content=[
                {"type": "thinking", "thinking": "First thought."},
                {"type": "text", "text": "Some text."},
                {"type": "thinking", "thinking": "Second thought."},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        # Should return first thinking block
        assert reasoning == "First thought."

    @pytest.mark.unit
    def test_extract_reasoning_empty_thinking_content(self) -> None:
        """Test extracting empty reasoning content."""
        message = AIMessage(
            content=[
                {"type": "thinking", "thinking": ""},
                {"type": "text", "text": "Answer"},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        assert reasoning == ""

    @pytest.mark.unit
    def test_extract_reasoning_missing_thinking_field(self) -> None:
        """Test extracting reasoning when thinking field is missing."""
        message = AIMessage(
            content=[
                {"type": "thinking"},  # Missing 'thinking' field
                {"type": "text", "text": "Answer"},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        assert reasoning is None

    @pytest.mark.unit
    def test_extract_reasoning_prefers_thinking_over_reasoning(self) -> None:
        """Test that 'thinking' type is checked before 'reasoning' type."""
        message = AIMessage(
            content=[
                {"type": "thinking", "thinking": "Claude thinking"},
                {"type": "reasoning", "reasoning": "Generic reasoning"},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        # Should return first match (thinking)
        assert reasoning == "Claude thinking"

    @pytest.mark.unit
    def test_extract_reasoning_with_multiline_content(self) -> None:
        """Test extracting multi-line reasoning content."""
        thinking_content = """Let me break this down:
1. First consideration
2. Second consideration
3. Conclusion"""

        message = AIMessage(
            content=[
                {"type": "thinking", "thinking": thinking_content},
                {"type": "text", "text": "Final answer."},
            ]
        )

        reasoning = MessageUtils.extract_reasoning(message)

        assert reasoning == thinking_content


class TestExtractToolCalls:
    """Test extracting tool calls from messages."""

    @pytest.mark.unit
    def test_extract_tool_calls_from_message(self) -> None:
        """Test extracting tool calls from message.tool_calls attribute."""
        message = AIMessage(
            content="I'll use the calculator",
            tool_calls=[
                {
                    "name": "calculator",
                    "args": {"expression": "2 + 2"},
                    "id": "call_123",
                }
            ],
        )

        calls = MessageUtils.extract_tool_calls(message)

        assert len(calls) == 1
        assert calls[0]["name"] == "calculator"
        assert calls[0]["args"] == {"expression": "2 + 2"}
        assert calls[0]["id"] == "call_123"

    @pytest.mark.unit
    def test_extract_tool_calls_multiple_calls(self) -> None:
        """Test extracting multiple tool calls."""
        message = AIMessage(
            content="I'll use multiple tools",
            tool_calls=[
                {
                    "name": "search",
                    "args": {"query": "test"},
                    "id": "call_1",
                },
                {
                    "name": "calculator",
                    "args": {"expression": "10 * 5"},
                    "id": "call_2",
                },
            ],
        )

        calls = MessageUtils.extract_tool_calls(message)

        assert len(calls) == 2
        assert calls[0]["name"] == "search"
        assert calls[1]["name"] == "calculator"

    @pytest.mark.unit
    def test_extract_tool_calls_returns_empty_list_when_none(self) -> None:
        """Test that empty list is returned when no tool calls present."""
        message = AIMessage(content="Just a regular response")

        calls = MessageUtils.extract_tool_calls(message)

        assert calls == []

    @pytest.mark.unit
    def test_extract_tool_calls_returns_empty_list_when_attribute_missing(self) -> None:
        """Test that empty list is returned when tool_calls attribute missing."""
        # Create a basic AIMessage
        message = AIMessage(content="Response")

        # Manually remove tool_calls attribute to test edge case
        if hasattr(message, "tool_calls"):
            delattr(message, "tool_calls")

        calls = MessageUtils.extract_tool_calls(message)

        assert calls == []

    @pytest.mark.unit
    def test_extract_tool_calls_empty_tool_calls_list(self) -> None:
        """Test extracting from empty tool_calls list."""
        message = AIMessage(content="Response", tool_calls=[])

        calls = MessageUtils.extract_tool_calls(message)

        assert calls == []

    @pytest.mark.unit
    def test_extract_tool_calls_with_complex_args(self) -> None:
        """Test extracting tool calls with complex nested arguments."""
        message = AIMessage(
            content="Using complex tool",
            tool_calls=[
                {
                    "name": "complex_tool",
                    "args": {
                        "nested": {
                            "field": "value",
                            "list": [1, 2, 3],
                        },
                        "array": ["a", "b"],
                    },
                    "id": "call_complex",
                }
            ],
        )

        calls = MessageUtils.extract_tool_calls(message)

        assert len(calls) == 1
        assert calls[0]["args"]["nested"]["field"] == "value"
        assert calls[0]["args"]["nested"]["list"] == [1, 2, 3]
        assert calls[0]["args"]["array"] == ["a", "b"]


class TestGetUsageMetadata:
    """Test extracting token usage metadata from messages."""

    @pytest.mark.unit
    def test_get_usage_metadata_with_full_metadata(self) -> None:
        """Test extracting usage metadata when all fields present."""
        message = AIMessage(
            content="Response",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )

        usage = MessageUtils.get_usage_metadata(message)

        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150

    @pytest.mark.unit
    def test_get_usage_metadata_returns_zeros_when_missing(self) -> None:
        """Test that zeros are returned when usage_metadata missing."""
        message = AIMessage(content="Response")

        usage = MessageUtils.get_usage_metadata(message)

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["total_tokens"] == 0

    @pytest.mark.unit
    def test_get_usage_metadata_handles_dict_like_access(self) -> None:
        """Test that get_usage_metadata handles dict-like access with .get() defaults."""
        # LangChain requires all fields, but our utility uses .get() for safety
        message = AIMessage(
            content="Response",
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            },
        )

        usage = MessageUtils.get_usage_metadata(message)

        # Should extract all fields successfully
        assert usage["input_tokens"] == 100
        assert usage["output_tokens"] == 50
        assert usage["total_tokens"] == 150

    @pytest.mark.unit
    def test_get_usage_metadata_with_zero_tokens(self) -> None:
        """Test extracting usage metadata with zero tokens."""
        message = AIMessage(
            content="",
            usage_metadata={
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )

        usage = MessageUtils.get_usage_metadata(message)

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["total_tokens"] == 0

    @pytest.mark.unit
    def test_get_usage_metadata_with_large_token_counts(self) -> None:
        """Test extracting usage metadata with large token counts."""
        message = AIMessage(
            content="Long response",
            usage_metadata={
                "input_tokens": 100_000,
                "output_tokens": 50_000,
                "total_tokens": 150_000,
            },
        )

        usage = MessageUtils.get_usage_metadata(message)

        assert usage["input_tokens"] == 100_000
        assert usage["output_tokens"] == 50_000
        assert usage["total_tokens"] == 150_000

    @pytest.mark.unit
    def test_get_usage_metadata_none_metadata(self) -> None:
        """Test extracting usage when metadata is None (not provided)."""
        # Create message without usage_metadata
        message = AIMessage(content="Response")

        # Explicitly set to None to simulate missing metadata
        message.usage_metadata = None

        usage = MessageUtils.get_usage_metadata(message)

        assert usage["input_tokens"] == 0
        assert usage["output_tokens"] == 0
        assert usage["total_tokens"] == 0

    @pytest.mark.unit
    def test_get_usage_metadata_returns_dict_structure(self) -> None:
        """Test that usage metadata always returns expected dict structure."""
        message = AIMessage(content="Response")

        usage = MessageUtils.get_usage_metadata(message)

        # Verify dict has expected keys
        assert "input_tokens" in usage
        assert "output_tokens" in usage
        assert "total_tokens" in usage
        assert len(usage) == 3

    @pytest.mark.unit
    def test_get_usage_metadata_with_extra_fields(self) -> None:
        """Test that extra fields in usage_metadata are ignored."""
        message = AIMessage(
            content="Response",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
                "extra_field": 999,  # Extra field
                "another_field": "ignored",
            },
        )

        usage = MessageUtils.get_usage_metadata(message)

        # Should only return standard fields
        assert usage["input_tokens"] == 10
        assert usage["output_tokens"] == 5
        assert usage["total_tokens"] == 15
        assert "extra_field" not in usage
        assert "another_field" not in usage


class TestIntegrationScenarios:
    """Test realistic integration scenarios combining multiple utilities."""

    @pytest.mark.unit
    def test_extract_all_from_claude_extended_thinking_response(self) -> None:
        """Test extracting all components from Claude extended thinking response."""
        message = AIMessage(
            content=[
                {
                    "type": "thinking",
                    "thinking": "I need to analyze the user's question carefully...",
                },
                {"type": "text", "text": "Based on my analysis, the answer is..."},
            ],
            usage_metadata={
                "input_tokens": 150,
                "output_tokens": 200,
                "total_tokens": 350,
            },
        )

        # Extract all components
        text = MessageUtils.extract_text(message)
        reasoning = MessageUtils.extract_reasoning(message)
        tool_calls = MessageUtils.extract_tool_calls(message)
        usage = MessageUtils.get_usage_metadata(message)

        assert text == "Based on my analysis, the answer is..."
        assert reasoning == "I need to analyze the user's question carefully..."
        assert tool_calls == []
        assert usage["total_tokens"] == 350

    @pytest.mark.unit
    def test_extract_all_from_tool_using_response(self) -> None:
        """Test extracting all components from response with tool calls."""
        message = AIMessage(
            content="I'll search for that information.",
            tool_calls=[
                {
                    "name": "search",
                    "args": {"query": "Python testing best practices"},
                    "id": "call_search_1",
                }
            ],
            usage_metadata={
                "input_tokens": 50,
                "output_tokens": 30,
                "total_tokens": 80,
            },
        )

        text = MessageUtils.extract_text(message)
        reasoning = MessageUtils.extract_reasoning(message)
        tool_calls = MessageUtils.extract_tool_calls(message)
        usage = MessageUtils.get_usage_metadata(message)

        assert text == "I'll search for that information."
        assert reasoning is None
        assert len(tool_calls) == 1
        assert tool_calls[0]["name"] == "search"
        assert usage["total_tokens"] == 80

    @pytest.mark.unit
    def test_extract_all_from_simple_text_response(self) -> None:
        """Test extracting all components from simple text response."""
        message = AIMessage(
            content="This is a simple response.",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 5,
                "total_tokens": 15,
            },
        )

        text = MessageUtils.extract_text(message)
        reasoning = MessageUtils.extract_reasoning(message)
        tool_calls = MessageUtils.extract_tool_calls(message)
        usage = MessageUtils.get_usage_metadata(message)

        assert text == "This is a simple response."
        assert reasoning is None
        assert tool_calls == []
        assert usage["total_tokens"] == 15

    @pytest.mark.unit
    def test_extract_all_from_minimal_message(self) -> None:
        """Test extracting from minimal message with no optional fields."""
        message = AIMessage(content="")

        text = MessageUtils.extract_text(message)
        reasoning = MessageUtils.extract_reasoning(message)
        tool_calls = MessageUtils.extract_tool_calls(message)
        usage = MessageUtils.get_usage_metadata(message)

        assert text == ""
        assert reasoning is None
        assert tool_calls == []
        assert usage["total_tokens"] == 0

    @pytest.mark.unit
    def test_extract_from_complex_multiblock_response(self) -> None:
        """Test extracting from complex response with multiple block types."""
        message = AIMessage(
            content=[
                {"type": "thinking", "thinking": "Let me think about this..."},
                {"type": "text", "text": "Here's my first point."},
                {"type": "text", "text": "And here's my second point."},
                {"type": "tool_use", "name": "search", "input": {"query": "test"}},
            ],
            tool_calls=[
                {
                    "name": "search",
                    "args": {"query": "test"},
                    "id": "call_1",
                }
            ],
            usage_metadata={
                "input_tokens": 200,
                "output_tokens": 150,
                "total_tokens": 350,
            },
        )

        text = MessageUtils.extract_text(message)
        reasoning = MessageUtils.extract_reasoning(message)
        tool_calls = MessageUtils.extract_tool_calls(message)
        usage = MessageUtils.get_usage_metadata(message)

        # Text should only include text blocks (not thinking or tool_use)
        assert text == "Here's my first point.\nAnd here's my second point."
        assert reasoning == "Let me think about this..."
        assert len(tool_calls) == 1
        assert usage["total_tokens"] == 350
