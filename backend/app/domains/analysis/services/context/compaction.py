"""Session compaction service for context engineering.

Implements session compaction and summarization to keep context within limits
while preserving recent conversation turns verbatim.

Reference: Sprint 11 - Context Engineering (#247)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.model_factory import get_chat_model
from app.core.timeout_config import create_runnable_config
from app.core.tracing import robust_traceable

logger = get_logger(__name__)


class CompactionConfig(BaseModel):
    """Configuration for session compaction.

    Controls how many recent turns to keep verbatim vs summarize,
    token budgets, and preservation of special message types.
    """

    max_turns_full: int = Field(
        default=5,
        ge=1,
        description="Keep last N conversation turns verbatim",
    )
    summarize_after: int = Field(
        default=10,
        ge=1,
        description="Trigger summarization after N total turns",
    )
    summary_max_tokens: int = Field(
        default=500,
        ge=50,
        description="Maximum tokens for summary text",
    )
    preserve_tool_calls: bool = Field(
        default=True,
        description="Preserve tool call messages even if old",
    )
    token_budget: int = Field(
        default=6000,
        ge=1000,
        description="Total token budget for compiled context",
    )


@dataclass
class CompiledContext:
    """Result of compaction with prefix (cacheable) and messages (dynamic).

    The prefix contains static/cacheable content (system prompt, summaries),
    while messages contain recent dynamic conversation turns.
    """

    prefix: list[dict[str, Any]]
    """Static, cacheable messages (system prompt, summary)"""

    messages: list[dict[str, Any]]
    """Dynamic, recent messages (recent conversation turns)"""

    original_count: int
    """Number of messages before compaction"""

    compiled_count: int
    """Number of messages after compaction"""

    summary: str | None
    """Summary of older messages (if generated)"""

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (compiled/original).

        Returns:
            Ratio between 0.0 and 1.0, where lower is more compressed

        """
        if self.original_count == 0:
            return 1.0
        return self.compiled_count / self.original_count


@dataclass
class CompactionMetrics:
    """Metrics for compaction operation logging."""

    original_messages: int
    compiled_messages: int
    compression_ratio: float
    summary_generated: bool
    tool_calls_preserved: int


class SessionCompactor:
    """Session compaction service.

    Compacts conversation history by:
    1. Keeping last N turns verbatim
    2. Summarizing older turns with LLM
    3. Preserving tool calls if configured
    """

    def __init__(self, config: CompactionConfig | None = None) -> None:
        """Initialize compactor with configuration.

        Args:
            config: Compaction configuration, uses defaults if None

        """
        self.config = config or CompactionConfig()

    @robust_traceable(
        name="session_compact",
        run_type="chain",
        tags=["compaction", "session", "context"],
        metadata={"service": "session_compactor"},
    )
    async def compact(self, full_history: list[dict[str, Any]]) -> CompiledContext:
        """Compact conversation history while keeping recent turns verbatim.

        Args:
            full_history: Full conversation history as list of message dicts

        Returns:
            CompiledContext with prefix (static) and messages (dynamic)

        """
        if len(full_history) <= self.config.summarize_after:
            # No compaction needed - history is short enough
            logger.debug(
                "compaction_skipped",
                message_count=len(full_history),
                threshold=self.config.summarize_after,
            )
            return CompiledContext(
                prefix=[],
                messages=full_history,
                original_count=len(full_history),
                compiled_count=len(full_history),
                summary=None,
            )

        # Split into old (to summarize) and recent (keep verbatim)
        recent_messages = full_history[-self.config.max_turns_full :]
        old_messages = full_history[: -self.config.max_turns_full]

        # Preserve tool calls if configured
        tool_calls = []
        if self.config.preserve_tool_calls:
            tool_calls = [msg for msg in old_messages if self._is_tool_call(msg)]
            # Remove tool calls from old messages (they'll go in prefix)
            old_messages = [msg for msg in old_messages if not self._is_tool_call(msg)]

        # Generate summary of old messages
        summary = None
        if old_messages:
            summary = await self._summarize_turns(old_messages)

        # Build prefix (static, cacheable)
        prefix = []
        if tool_calls:
            prefix.extend(tool_calls)
        if summary:
            prefix.append(
                {"role": "system", "content": f"Previous conversation summary: {summary}"}
            )

        compiled_count = len(prefix) + len(recent_messages)

        logger.info(
            "compaction_completed",
            original_count=len(full_history),
            compiled_count=compiled_count,
            summary_generated=summary is not None,
            tool_calls_preserved=len(tool_calls),
        )

        return CompiledContext(
            prefix=prefix,
            messages=recent_messages,
            original_count=len(full_history),
            compiled_count=compiled_count,
            summary=summary,
        )

    @robust_traceable(
        name="session_summarize_turns",
        run_type="llm",
        tags=["compaction", "summarization", "llm_call"],
        metadata={"service": "session_compactor"},
    )
    async def _summarize_turns(self, turns: list[dict[str, Any]]) -> str:
        """Summarize older conversation turns using LLM.

        Args:
            turns: List of message dicts to summarize

        Returns:
            Summary text

        """
        # Build conversation text
        conversation_text = "\n".join(
            [f"{msg.get('role', 'unknown')}: {msg.get('content', '')}" for msg in turns]
        )

        prompt = f"""Summarize this conversation, preserving:
1. Key topics discussed
2. User's understanding level and progress
3. Important context or decisions

Conversation:
{conversation_text}

Provide a concise summary (2-3 sentences) that captures essential context."""

        model = get_chat_model()
        messages = [
            SystemMessage(content="You are an expert at summarizing conversations concisely."),
            HumanMessage(content=prompt),
        ]

        config = create_runnable_config()
        response = await model.ainvoke(messages, config=config)
        summary_text: str
        if hasattr(response, "content"):
            content = response.content
            summary_text = content if isinstance(content, str) else str(content)
        else:
            summary_text = str(response)

        logger.debug(
            "conversation_summarized",
            original_turns=len(turns),
            summary_length=len(summary_text),
        )

        return summary_text

    def _is_tool_call(self, turn: dict[str, Any]) -> bool:
        """Check if message is a tool call.

        Args:
            turn: Message dict to check

        Returns:
            True if message contains tool calls

        """
        # Check for tool_calls field (OpenAI format) or function_call (legacy)
        return bool(turn.get("tool_calls") or turn.get("function_call"))

    def get_metrics(
        self,
        original: list[dict[str, Any]],
        compiled: CompiledContext,
    ) -> CompactionMetrics:
        """Calculate compaction metrics for logging.

        Args:
            original: Original message list
            compiled: Compiled context result

        Returns:
            CompactionMetrics with statistics

        """
        tool_calls_preserved = sum(1 for msg in compiled.prefix if self._is_tool_call(msg))

        return CompactionMetrics(
            original_messages=len(original),
            compiled_messages=compiled.compiled_count,
            compression_ratio=compiled.compression_ratio,
            summary_generated=compiled.summary is not None,
            tool_calls_preserved=tool_calls_preserved,
        )
