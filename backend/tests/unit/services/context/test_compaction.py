"""Unit tests for session compaction service.

Tests CompactionConfig, SessionCompactor, and ContextCompiler.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domains.analysis.services.context.compaction import (
    CompactionConfig,
    CompactionMetrics,
    CompiledContext,
    SessionCompactor,
)
from app.domains.analysis.services.context.compiler import ContextCompiler
from app.shared.workflows.context_compiler import create_workflow_compiler

@pytest.mark.unit


class TestCompactionConfig:
    """Tests for CompactionConfig model."""

    def test_default_values(self) -> None:
        """Test CompactionConfig has correct defaults."""
        config = CompactionConfig()

        assert config.max_turns_full == 5
        assert config.summarize_after == 10
        assert config.summary_max_tokens == 500
        assert config.preserve_tool_calls is True
        assert config.token_budget == 6000

    def test_custom_values(self) -> None:
        """Test CompactionConfig accepts custom values."""
        config = CompactionConfig(
            max_turns_full=3,
            summarize_after=8,
            summary_max_tokens=300,
            preserve_tool_calls=False,
            token_budget=4000,
        )

        assert config.max_turns_full == 3
        assert config.summarize_after == 8
        assert config.summary_max_tokens == 300
        assert config.preserve_tool_calls is False
        assert config.token_budget == 4000

    def test_validation_min_values(self) -> None:
        """Test CompactionConfig validates minimum values."""
        with pytest.raises(ValueError):
            CompactionConfig(max_turns_full=0)

        with pytest.raises(ValueError):
            CompactionConfig(summarize_after=0)

        with pytest.raises(ValueError):
            CompactionConfig(summary_max_tokens=10)

        with pytest.raises(ValueError):
            CompactionConfig(token_budget=500)


class TestCompiledContext:
    """Tests for CompiledContext dataclass."""

    def test_compression_ratio_calculation(self) -> None:
        """Test compression_ratio property calculates correctly."""
        context = CompiledContext(
            prefix=[],
            messages=[{"role": "user", "content": "test"}],
            original_count=10,
            compiled_count=5,
            summary=None,
        )

        assert context.compression_ratio == 0.5

    def test_compression_ratio_no_compression(self) -> None:
        """Test compression_ratio when no compression occurred."""
        context = CompiledContext(
            prefix=[],
            messages=[{"role": "user", "content": "test"}],
            original_count=5,
            compiled_count=5,
            summary=None,
        )

        assert context.compression_ratio == 1.0

    def test_compression_ratio_zero_original(self) -> None:
        """Test compression_ratio handles zero original count."""
        context = CompiledContext(
            prefix=[],
            messages=[],
            original_count=0,
            compiled_count=0,
            summary=None,
        )

        assert context.compression_ratio == 1.0


class TestSessionCompactor:
    """Tests for SessionCompactor class."""

    def test_init_default_config(self) -> None:
        """Test SessionCompactor initializes with default config."""
        compactor = SessionCompactor()

        assert compactor.config is not None
        assert compactor.config.max_turns_full == 5

    def test_init_custom_config(self) -> None:
        """Test SessionCompactor accepts custom config."""
        config = CompactionConfig(max_turns_full=3)
        compactor = SessionCompactor(config=config)

        assert compactor.config.max_turns_full == 3

    @pytest.mark.asyncio
    async def test_compact_small_history_unchanged(self) -> None:
        """Test compact does not modify small history."""
        compactor = SessionCompactor()
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]

        result = await compactor.compact(history)

        assert result.prefix == []
        assert result.messages == history
        assert result.original_count == 3
        assert result.compiled_count == 3
        assert result.summary is None
        assert result.compression_ratio == 1.0

    @pytest.mark.asyncio
    async def test_compact_large_history_with_summarization(self) -> None:
        """Test compact summarizes large history."""
        config = CompactionConfig(max_turns_full=2, summarize_after=5)
        compactor = SessionCompactor(config=config)

        # Create history with 8 messages (exceeds threshold)
        history = [{"role": "user", "content": f"Message {i}"} for i in range(8)]

        # Mock the summarization
        with patch.object(compactor, "_summarize_turns", new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = "Summary of old messages"

            result = await compactor.compact(history)

            # Should have called summarize for first 6 messages
            mock_summarize.assert_called_once()
            summarized_turns = mock_summarize.call_args[0][0]
            assert len(summarized_turns) == 6

            # Result should have:
            # - prefix with summary
            # - last 2 messages
            assert len(result.prefix) == 1
            assert "Previous conversation summary" in result.prefix[0]["content"]
            assert len(result.messages) == 2
            assert result.messages == history[-2:]
            assert result.summary == "Summary of old messages"
            assert result.original_count == 8
            assert result.compiled_count == 3  # 1 prefix + 2 recent

    @pytest.mark.asyncio
    async def test_compact_preserves_tool_calls(self) -> None:
        """Test compact preserves tool calls from old messages."""
        config = CompactionConfig(max_turns_full=2, summarize_after=5, preserve_tool_calls=True)
        compactor = SessionCompactor(config=config)

        history = [
            {"role": "user", "content": "Message 1"},
            {
                "role": "assistant",
                "content": "Response 1",
                "tool_calls": [{"id": "1", "function": {"name": "test"}}],
            },
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"},
            {"role": "user", "content": "Message 4"},
            {"role": "assistant", "content": "Response 4"},
        ]

        with patch.object(compactor, "_summarize_turns", new_callable=AsyncMock) as mock_summarize:
            mock_summarize.return_value = "Summary"

            result = await compactor.compact(history)

            # Should preserve tool call in prefix
            tool_call_msgs = [msg for msg in result.prefix if compactor._is_tool_call(msg)]
            assert len(tool_call_msgs) == 1
            assert tool_call_msgs[0]["tool_calls"][0]["id"] == "1"

    @pytest.mark.asyncio
    async def test_summarize_turns_calls_llm(self) -> None:
        """Test _summarize_turns invokes LLM correctly."""
        compactor = SessionCompactor()
        turns = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
        ]

        # Mock the model
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Summary: Discussion about Python programming language."
        mock_model.ainvoke = AsyncMock(return_value=mock_response)

        with patch("app.services.context.compaction.get_chat_model", return_value=mock_model):
            result = await compactor._summarize_turns(turns)

            assert result == "Summary: Discussion about Python programming language."
            mock_model.ainvoke.assert_called_once()

    def test_is_tool_call_detects_tool_calls(self) -> None:
        """Test _is_tool_call correctly identifies tool calls."""
        compactor = SessionCompactor()

        # OpenAI format
        msg_with_tool_calls = {"role": "assistant", "tool_calls": [{"id": "1"}]}
        assert compactor._is_tool_call(msg_with_tool_calls) is True

        # Legacy function_call format
        msg_with_function_call = {"role": "assistant", "function_call": {"name": "test"}}
        assert compactor._is_tool_call(msg_with_function_call) is True

        # Regular message
        msg_no_tools = {"role": "assistant", "content": "Hello"}
        assert compactor._is_tool_call(msg_no_tools) is False

    def test_get_metrics_calculation(self) -> None:
        """Test get_metrics calculates correct statistics."""
        compactor = SessionCompactor()

        original = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

        compiled = CompiledContext(
            prefix=[
                {"role": "assistant", "tool_calls": [{"id": "1"}]},
                {"role": "system", "content": "Summary"},
            ],
            messages=[{"role": "user", "content": "Recent"}],
            original_count=10,
            compiled_count=3,
            summary="Summary text",
        )

        metrics = compactor.get_metrics(original, compiled)

        # Verify type
        assert isinstance(metrics, CompactionMetrics)

        # Verify values
        assert metrics.original_messages == 10
        assert metrics.compiled_messages == 3
        assert metrics.compression_ratio == 0.3
        assert metrics.summary_generated is True
        assert metrics.tool_calls_preserved == 1


class TestContextCompiler:
    """Tests for ContextCompiler class."""

    def test_init_with_identity(self) -> None:
        """Test ContextCompiler initialization with agent identity."""
        compiler = ContextCompiler(
            system_prompt="You are helpful",
            agent_identity="Friendly assistant",
        )

        assert compiler.system_prompt == "You are helpful"
        assert compiler.agent_identity == "Friendly assistant"
        assert compiler.compactor is not None

    def test_init_without_identity(self) -> None:
        """Test ContextCompiler initialization without agent identity."""
        compiler = ContextCompiler(system_prompt="You are helpful")

        assert compiler.system_prompt == "You are helpful"
        assert compiler.agent_identity is None

    @pytest.mark.asyncio
    async def test_compile_with_all_components(self) -> None:
        """Test compile_for_invocation with all components."""
        compiler = ContextCompiler(
            system_prompt="You are helpful",
            agent_identity="Test agent",
        )

        session_history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]
        current_input = "What's next?"
        injected_memory = ["User prefers detailed explanations", "User is beginner"]

        with patch.object(compiler.compactor, "compact", new_callable=AsyncMock) as mock_compact:
            mock_compact.return_value = CompiledContext(
                prefix=[],
                messages=session_history,
                original_count=2,
                compiled_count=2,
                summary=None,
            )

            result = await compiler.compile_for_invocation(
                session_history=session_history,
                current_input=current_input,
                injected_memory=injected_memory,
            )

            # Check structure
            assert len(result) >= 5  # system + memory + history + current

            # Check system prompt (should include identity)
            assert result[0]["role"] == "system"
            assert "You are helpful" in result[0]["content"]
            assert "Test agent" in result[0]["content"]

            # Check memory injection
            assert result[1]["role"] == "system"
            assert "User prefers detailed explanations" in result[1]["content"]

            # Check current input is last
            assert result[-1]["role"] == "user"
            assert result[-1]["content"] == "What's next?"

    @pytest.mark.asyncio
    async def test_compile_without_optional_components(self) -> None:
        """Test compile_for_invocation without optional components."""
        compiler = ContextCompiler(system_prompt="You are helpful")

        session_history = [{"role": "user", "content": "Hi"}]

        with patch.object(compiler.compactor, "compact", new_callable=AsyncMock) as mock_compact:
            mock_compact.return_value = CompiledContext(
                prefix=[],
                messages=session_history,
                original_count=1,
                compiled_count=1,
                summary=None,
            )

            result = await compiler.compile_for_invocation(
                session_history=session_history,
                current_input=None,
                injected_memory=None,
            )

            # Should have system prompt + history only
            assert len(result) == 2
            assert result[0]["role"] == "system"
            assert result[1] == session_history[0]

    @pytest.mark.asyncio
    async def test_compile_uses_compacted_prefix(self) -> None:
        """Test compile includes compacted prefix in result."""
        compiler = ContextCompiler(system_prompt="You are helpful")

        session_history = [{"role": "user", "content": f"Message {i}"} for i in range(10)]

        with patch.object(compiler.compactor, "compact", new_callable=AsyncMock) as mock_compact:
            mock_compact.return_value = CompiledContext(
                prefix=[{"role": "system", "content": "Previous conversation summary: Summary"}],
                messages=session_history[-2:],
                original_count=10,
                compiled_count=3,
                summary="Summary",
            )

            result = await compiler.compile_for_invocation(session_history=session_history)

            # Should have: system prompt + prefix + recent messages
            assert len(result) == 4  # 1 system + 1 prefix + 2 recent
            assert result[1]["content"] == "Previous conversation summary: Summary"


class TestWorkflowFactory:
    """Tests for workflow-specific compiler factory."""

    def test_create_tutor_compiler(self) -> None:
        """Test creating tutor workflow compiler."""
        compiler = create_workflow_compiler("tutor")

        assert isinstance(compiler, ContextCompiler)
        assert "Socratic tutor" in compiler.system_prompt
        assert compiler.agent_identity is not None
        assert "patient" in compiler.agent_identity.lower()

    def test_create_analysis_compiler(self) -> None:
        """Test creating analysis workflow compiler."""
        compiler = create_workflow_compiler("analysis")

        assert isinstance(compiler, ContextCompiler)
        assert "technical content analysis" in compiler.system_prompt
        assert compiler.agent_identity is not None
        assert "analyst" in compiler.agent_identity.lower()

    def test_create_unknown_workflow_raises_error(self) -> None:
        """Test creating compiler for unknown workflow raises ValueError."""
        with pytest.raises(ValueError, match="Unknown workflow type"):
            create_workflow_compiler("unknown")

    def test_create_with_custom_config(self) -> None:
        """Test creating compiler with custom compaction config."""
        config = CompactionConfig(max_turns_full=3)
        compiler = create_workflow_compiler("tutor", config=config)

        assert compiler.compactor.config.max_turns_full == 3
