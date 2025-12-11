"""Context compiler for building invocation-ready message lists.

Combines system prompts, agent identity, compacted history, and injected memory
into properly formatted message lists for LLM invocation.

Reference: Sprint 11 - Context Engineering (#247)
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.services.context.compaction import CompactionConfig, SessionCompactor

logger = get_logger(__name__)


class ContextCompiler:
    """Compiles context for LLM invocation.

    Handles:
    1. System prompt injection
    2. Agent identity/personality
    3. Session history compaction
    4. Memory injection
    5. Current input
    """

    def __init__(
        self,
        system_prompt: str,
        agent_identity: str | None = None,
        config: CompactionConfig | None = None,
    ) -> None:
        """Initialize context compiler.

        Args:
            system_prompt: Core system prompt for agent
            agent_identity: Optional agent personality/identity description
            config: Compaction configuration, uses defaults if None

        """
        self.system_prompt = system_prompt
        self.agent_identity = agent_identity
        self.compactor = SessionCompactor(config)

    async def compile_for_invocation(
        self,
        session_history: list[dict[str, Any]],
        current_input: str | None = None,
        injected_memory: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Compile complete context for LLM invocation.

        Builds message list with proper ordering:
        1. System prompt
        2. Agent identity (if provided)
        3. Injected memory (if provided)
        4. Compacted session history (prefix + recent messages)
        5. Current input (if provided)

        Args:
            session_history: Full conversation history
            current_input: Current user input to add
            injected_memory: Retrieved memory to inject

        Returns:
            Complete message list ready for LLM invocation

        """
        messages: list[dict[str, Any]] = []

        # 1. System prompt
        system_content = self.system_prompt
        if self.agent_identity:
            system_content = f"{system_content}\n\n{self.agent_identity}"

        messages.append({"role": "system", "content": system_content})

        # 2. Injected memory (if any)
        if injected_memory:
            memory_content = "Relevant context from memory:\n" + "\n".join(
                f"- {mem}" for mem in injected_memory
            )
            messages.append({"role": "system", "content": memory_content})

        # 3. Compact session history
        compiled = await self.compactor.compact(session_history)

        # Add prefix (static, cacheable messages like summaries and tool calls)
        messages.extend(compiled.prefix)

        # Add recent messages (dynamic)
        messages.extend(compiled.messages)

        # 4. Current input (if provided)
        if current_input:
            messages.append({"role": "user", "content": current_input})

        # Log compilation metrics
        logger.info(
            "context_compiled",
            total_messages=len(messages),
            system_messages=sum(1 for m in messages if m.get("role") == "system"),
            user_messages=sum(1 for m in messages if m.get("role") == "user"),
            assistant_messages=sum(1 for m in messages if m.get("role") == "assistant"),
            original_history=compiled.original_count,
            compiled_history=compiled.compiled_count,
            compression_ratio=compiled.compression_ratio,
            memory_injected=len(injected_memory) if injected_memory else 0,
        )

        return messages
